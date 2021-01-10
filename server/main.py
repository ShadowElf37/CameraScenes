from sys import path
path.append('..')

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY
import pygame.locals
import network
import audio
import webcam
import graphics
import scenes
import pickle
import json
from sys import exit
from network_common import UDPSession, iterq
import traceback

path.append('..')

clock = pygame.time.Clock()

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30
RUNNING = True

CAM_WIDTH = 400
CAM_HEIGHT = 300

pygame.init()
pygame.display.set_caption("Scene Manager - Server")
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.locals.RESIZABLE)

#cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75)
text = graphics.Text('Server POGGERS', WIDTH / 2, 600)

aud = audio.MultipleAudioOutput()

print('Audio ready. Initializing server...')
server = network.UDPManager(37001, frag=True)
server.init()

scene_manager = scenes.SceneManager(server, use_pipe=True)

preview_tiler = scenes.BasicTiler(WIDTH, HEIGHT, CAM_WIDTH, CAM_HEIGHT, True)
scene1 = scenes.Scene(scene_manager, layout=preview_tiler, background=BLACK)

scene2 = scenes.Scene(scene_manager)

scene2.add(7, WIDTH/4, HEIGHT/2, CAM_WIDTH, CAM_HEIGHT)
scene2.add(1, WIDTH*3/4, HEIGHT/2, CAM_WIDTH, CAM_HEIGHT)

scene_manager.add_scenes(scene1, scene2)
scene_manager.first()

scene_manager.persistent_objects.append(text)

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
                scene_manager.register_camera(uuid, graphics.WebcamViewer(w=CAM_WIDTH, h=CAM_HEIGHT, enforce_dim=True))
                scene1.add(uuid, *[None]*4)
            elif data[2] == 'CLOSE':
                session.is_open = False
                scene_manager.unregister_camera(uuid)
                aud.close_output(uuid)

        for uuid, frame in iterq(server.VIDEO_QUEUE):
            if (cam := scene_manager.cameras.get(uuid)) is None:
                continue
            cam.take_frame(pickle.loads(frame))
            #server.sessions[uuid].send('PRINT', b'hello fren')

        scene_manager.draw(screen)

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

        clock.tick(FPS)

except Exception as e:
    traceback.print_exc()
    print(type(e).__qualname__, str(e))
    for session in server.sessions.values():
        session._send('DIE')
    RUNNING = False
    server.close()
    raise e

finally:
    server.close()
    pygame.quit()
    print('Closed safely.')
    exit(0)

