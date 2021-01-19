from sys import path
path.append('')

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame.locals
import network_server as network
import audio
import webcam
import graphics
import scenes
import pickle
import pyjson5 as json
from sys import exit
from network_common import UDPSession, iterq
import traceback

import os
import tkinter as tk
from tkinter import filedialog as fd
import ntpath


# ===================
#    LOAD SHOW CFG
# ===================


with open('config.json') as config_file:
    config = json.decode_io(config_file)

last_show_file = show_file = config['last_show_file']

def load_cfg(sv=None):
    global show_file
    path = fd.askopenfilename(initialdir='shows', filetypes=(
                                        ("Config/JSON files", "*.json;*.cfg;*.json5"),
                                        ("All files", "*.*")
                                            ))
    if sv:
        sv.set(ntpath.basename(path) or last_show_file or 'Select...')
    show_file = path

done = False
def quit_tk(*_):
    global done
    done = True
    root.destroy()

root = tk.Tk()
root.geometry('200x100')
root.title('Load Files')

show_label = tk.Label(root, text='Show file:', anchor='e')
show_sv = tk.StringVar(value=ntpath.basename(last_show_file) or 'Select...')
show_selector = tk.Button(root, textvar=show_sv, command=lambda: load_cfg(show_sv), anchor='w')

space = tk.Label(root)

show_label.pack()
show_selector.pack()
space.pack()

submit = tk.Button(root, text='Continue', command=lambda *_: root.destroy() if show_file != '' else 0, width=13)
submit.pack()
root.bind('<Return>', lambda *_: submit.invoke())

root.protocol("WM_DELETE_WINDOW", quit_tk)

try:
    root.mainloop()
except tk.TclError:
    show_label.destroy()
    show_selector.destroy()
    submit.destroy()
    root.quit()


config['last_show_file'] = show_file
with open('config.json', 'wb') as config_file:
    json.encode_io(config, config_file)

if not show_file or done:
    exit()

show_data = json.decode_io(open(show_file))

# ===================
#        START
# ===================

print('Booting up...')

clock = pygame.time.Clock()

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1920
HEIGHT = 1080
os.environ['SDL_VIDEO_WINDOW_POS'] = '%i,%i' % (8,30)
FPS = graphics.Sprite.REAL_FPS = 30
DEBUG = True
RUNNING = True
SCALE_METHOD = graphics.scale.CROP

def frac_to_coord(x=None, y=None):
    """doesn't convert if they're not floats between 0 and 1"""
    if x is y is None:
        return tuple()

    if type(x) is float and 0 <= x <= 1:
        x *= WIDTH
    if type(y) is float and 0 <= y <= 1:
        y *= HEIGHT
    return x, y

pygame.init()
pygame.display.set_caption("Proscenium Server")
pygame.display.set_icon(pygame.image.load('images/favicon.png'))
screen = pygame.display.set_mode((WIDTH, HEIGHT))

aud = audio.MultipleAudioOutput()

print('Audio ready. Initializing server...')
server = network.UDPManager(37001, frag=True)
server.init()

scene_manager = scenes.SceneManager(server, screen, use_pipe=True, debug=DEBUG)

# ============
# PARSE SCENES
# ============

for scene in show_data:
    bg = scene.get('background', '')
    s = scenes.Scene(scene_manager,
                     background=os.path.join('images', bg) if bg else None,
                     transition_duration=scene.get('transition_duration', 0),
                     transition=scene.get('transition', None),
                     wipe_side=scene.get('wipe_to', 'left'))

    for camera in scene.get('cameras', []):  # uuid, x, y, w, h
        uuid, x, y, w, h, *extra = camera

        # floats become fractions of window
        x, y = frac_to_coord(x, y)
        w, h = frac_to_coord(w, h)

        s.add(str(uuid), x, y, w, h, *extra)

    # ENSURE CORRECT ARGS CAN BE EASILY PASSED - THIS IS ROUGH SKETCH - NO FRACTIONAL
    for text in scene.get('text', []):  # text, x, y     opt: font, fsize, color
        t, x, y, *args = text
        x, y = frac_to_coord(x, y)
        s.objects.append(graphics.Text(t, x, y, *args))

    # fps should be 0 for stills
    # you may need to calculate the correct fps if you don't have one image for every frame in the second
    for sprite in scene.get('sprites', []):  # [paths], x, y, fps     opt: w=0, h=0, delete_on_end=False, corner=0

        s.objects.append(graphics.Sprite(
            sprite.get('folder'),
            *frac_to_coord(*sprite.get('start_pos')),
            sprite.get('fps', graphics.Sprite.REAL_FPS),
            delete_on_end_frames=sprite.get('delete_on_end_frames', False),
            delete_on_end_move=sprite.get('delete_on_end_move', False),
            loop_move=sprite.get('loop_move', True),
            end_pos=frac_to_coord(*sprite.get('end_pos', (None, None))),
            move_duration=sprite.get('move_duration', 0),
            rotation=sprite.get('rotation', 0),
            corner=sprite.get('corner', 0),
            w=sprite.get('w', 0),
            h=sprite.get('h', 0)
        ))


#preview_tiler = scenes.BasicTiler(WIDTH, HEIGHT, CAM_WIDTH, CAM_HEIGHT, True)
FPS_COUNTER = graphics.Text('FPS', 50, 20)
if DEBUG:
    scene_manager.persistent_objects.append(FPS_COUNTER)
scene_manager.first()

# ======
#  LOOP
# ======

DEBUG_DRAGGING_SELECTED = None  # uuid of box dragging
DEBUG_DRAGGING_CACHED_POSITION = None  # original box position, used for mouse offset so dragging feels more natural
DEBUG_DRAGGING_CACHED_MOUSE = None  # original mouse position, used for mouse offset so dragging feels more natural

print('Server started!')
try:
    while server.running and RUNNING:
        for data in iterq(server.META_QUEUE):
            print('META', data)
            uuid = data[0]
            session = server.sessions[uuid]
            if data[2] == 'OPEN':
                if not session.is_open:
                    session.is_open = True
                    session.send('CONTINUE')
                else:  # the session is already open!
                    session.send('DUPLICATE')
                    continue
                # add an audio processor for them
                aud.new_output(uuid)
                # make a cam viewer

                w, h = scene_manager.current_scene.layout.get_dim(uuid)
                scene_manager.register_camera(uuid, graphics.WebcamViewer(w=w, h=h, dim_enforcer=SCALE_METHOD))

            elif data[2] == 'CLOSE':
                session.is_open = False
                scene_manager.unregister_camera(uuid)
                aud.close_output(uuid)

            elif data[2] == 'MUTE':
                aud.mute(uuid)
                server.muted(uuid)
            elif data[2] == 'UNMUTE':
                aud.unmute(uuid)
                server.unmuted(uuid)

        for uuid, frame in iterq(server.VIDEO_QUEUE):
            if (cam := scene_manager.cameras.get(uuid)) is None:
                continue
            cam.take_frame(pickle.loads(frame))
            #server.sessions[uuid].send('PRINT', b'hello fren')

        scene_manager.draw()

        # PLAY AUDIO FROM CLIENTS
        for chunk in iterq(server.AUDIO_QUEUE):
            aud.process(*chunk)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('User quit.')
                for session in server.sessions.values():
                    session._send('DIE')
                RUNNING = False
                break

            elif DEBUG and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    scene_manager.next()
                elif event.key == pygame.K_LEFT:
                    scene_manager.back()

            elif DEBUG and event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                # check every camera
                for uuid, *_ in reversed(scene_manager.current_scene.cameras):
                    # get the debug rect, we're in debug guaranteed
                    cam_box = scene_manager.current_scene.debug_rects.get(uuid)
                    # something dumb happened
                    if cam_box is None:
                        continue

                    rect = cam_box.rect
                    # clicked on rect
                    if rect[0] < pos[0] < rect[2] and rect[1] < pos[1] < rect[3]:
                        # we're dragging this box
                        DEBUG_DRAGGING_SELECTED = uuid
                        DEBUG_DRAGGING_CACHED_MOUSE = pos
                        DEBUG_DRAGGING_CACHED_POSITION = cam_box.x, cam_box.y
                        break

            # release the drag
            elif DEBUG and event.type == pygame.MOUSEBUTTONUP:
                DEBUG_DRAGGING_SELECTED = None
                DEBUG_DRAGGING_CACHED_MOUSE = None
                DEBUG_DRAGGING_CACHED_POSITION = None


            # while dragging, set position
            if DEBUG_DRAGGING_SELECTED is not None:
                ox, oy = DEBUG_DRAGGING_CACHED_POSITION
                omx, omy = DEBUG_DRAGGING_CACHED_MOUSE
                x, y = pygame.mouse.get_pos()
                scene_manager.current_scene.layout.set_pos(DEBUG_DRAGGING_SELECTED, ox + x - omx, oy + y - omy)


        clock.tick(FPS)
        if DEBUG:
            FPS_COUNTER.reload(text=str(round(clock.get_fps(), 1)))

except Exception as e:
    traceback.print_exc()
    print(type(e).__qualname__, str(e))
    for session in server.sessions.values():
        session._send('DIE')
    RUNNING = False
    server.close()
    raise e

except SystemExit:
    for session in server.sessions.values():
        session._send('DIE')
    RUNNING = False

finally:
    server.close()
    pygame.quit()
    print('Closed safely.')
    exit()

exit(0)
