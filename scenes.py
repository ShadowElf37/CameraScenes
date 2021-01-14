import pygame
from typing import Optional, Callable, Tuple, Set
import graphics
import webcam
from pipe import Pipe
from network_server import UDPManager
import time
import threading

class SceneManager:
    UNDEFINED_COMMAND = object()
    RESOLUTION_SETTER = 'CROP'  # SET, W_FLEX, H_FLEX, CROP

    def __init__(self, server: UDPManager, screen: pygame.Surface, use_pipe=True, block_pipe=False, debug=False, pipe_ip='localhost'):
        self.server: UDPManager = server
        self.cameras: {str: graphics.WebcamViewer} = {}
        self.persistent_objects: [graphics.Object] = []
        self.scenes: [Scene] = []
        self.current_i = -1
        self.current_scene: Optional[Scene] = None

        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.debug = debug

        self.transition_from = None
        self.prior_scene: Optional[Scene] = None
        self.wipe_side = ''
        self.transition_type = None
        self.transition_duration = 0  # IN FRAMES
        self.transition_counter = 0

        self.cues = Pipe(at=38051, ip=pipe_ip)

        if use_pipe:
            if block_pipe:
                print('SceneManager Pipe has been created with blocking. Please establish the other end now.')
            else:
                print('SceneManager Pipe has been created without blocking. The other end may connect at any time.')

            self.cues.open(blocking=block_pipe, cb=lambda: print('Pipe established.'))

    @property
    def dim(self):
        return self.screen_width, self.screen_height

    def register_camera(self, uuid, viewer):
        uuid = str(uuid)
        self.cameras[uuid] = viewer
        for scene in self.scenes:
            scene.notify_new(uuid)
    def unregister_camera(self, uuid):
        uuid = str(uuid)
        self.cameras[uuid] = None
        for scene in self.scenes:
            scene.notify_death(uuid)

    def add_scenes(self, *scenes):
        for scene in scenes:
            self.scenes.append(scene)

    def set_scene_notrans(self, i):
        if i > len(self.scenes)-1 or i < 0: return
        self.current_i = i
        self.current_scene = self.scenes[i]
        self.current_scene.activate()
        print(f'Switched to scene {i}. UUIDs available: ' + ', '.join(info[0] for info in self.current_scene.cameras))

    def set_scene(self, i):
        if i > len(self.scenes) - 1 or i < 0: return
        self.prior_scene = self.current_scene
        self.current_i = i
        self.current_scene: Scene = self.scenes[i]

        # set transition variables
        if self.current_scene.transition is not None:
            # print('TRANS', self.current_scene.transition, self.current_scene.transition_duration, )
            self.transition_type = self.current_scene.transition
            self.transition_from = self.screen.copy()
            self.transition_duration = self.current_scene.transition_duration
            self.wipe_side = self.current_scene.wipe_side
            self.transition_counter = 0
        # there's no transition on this scene, clear ALL THE OTHER TRANSITIONS NOW
        else:
            self.transition_from = None
            self.transition_type = None
            self.transition_counter = 0

        self.current_scene.activate()
        print(f'Switched to scene {i}' + (f' ({self.current_scene.transition})' if self.current_scene.transition else '') + '. UUIDs available: ' + ', '.join(info[0] for info in self.current_scene.cameras))

    def next(self):
        self.set_scene(self.current_i + 1)
    def back(self):
        self.set_scene(self.current_i - 1)
    def last(self):
        self.set_scene(len(self.scenes)-1)
    def first(self):
        self.set_scene(0)

    def draw(self):
        for full_command in iter(self.cues):
            full_command = full_command.decode()
            for command in full_command.split(';'):
                command = command.strip()
                if {
                    'next': self.next,
                    'back': self.back,
                    'last': self.last,
                    'first': self.first,
                    'test': lambda: print('pipe test!')
                }.get(command, lambda: self.UNDEFINED_COMMAND)() is self.UNDEFINED_COMMAND:
                    try:
                        if command[:3] == 'py:':
                            try:
                                eval(command[3:].strip())
                            except SyntaxError:
                                exec(command[3:].strip())
                        else:
                            cmd, *args = command.split(' ')

                            if cmd == 'set_scene':
                                self.set_scene(int(args[0]))
                            elif cmd == 'set_scene_nowipe':
                                self.set_scene_notrans(int(args[0]))
                            elif cmd in ('mute_audio', 'mutea', 'mute'):
                                self.server.sessions[args[0]].send('MUTE_AUDIO')
                                self.server.muted(args[0])
                                self.server.META_QUEUE.put((args[0], -7, 'MUTE', (0,0), b''))
                            elif cmd in ('unmute_audio', 'unmutea', 'unmute'):
                                self.server.sessions[args[0]].send('UNMUTE_AUDIO')
                                self.server.unmuted(args[0])
                                self.server.META_QUEUE.put((args[0], -7, 'UNMUTE', (0,0), b''))
                            elif cmd in ('mute_video', 'mutev'):
                                self.server.sessions[args[0]].send('MUTE_VIDEO')
                                self.server.muted(args[0])
                            elif cmd in ('unmute_video', 'unmutev'):
                                self.server.sessions[args[0]].send('UNMUTE_VIDEO')
                                self.server.unmuted(args[0])
                            elif cmd in ('update_text', 'text'):
                                self.server.sessions[args[0]].send('UPDATE_TEXT', b' '.join(map(str.encode, args[1:])))
                            elif cmd in ('update_text_color', 'color'):
                                self.server.sessions[args[0]].send('UPDATE_TEXT_COLOR', b' '.join(map(str.encode, args[1:])))
                            elif cmd == 'kill':
                                self.server.META_QUEUE.put((args[0], 0, 'CLOSE', (0,0), b''))
                            elif cmd == 'exit':
                                raise SystemExit('Exit by pipe command')
                            elif cmd == 'print':
                                print('From pipe:', *args)
                            else:
                                print('Bad pipe command', '"'+command+'"')
                    except Exception as e:
                        print(f'Pipe command "{command}" failed:', str(e))

        # ===============
        # DRAWING
        # ===============

        # EXECUTE ANY WIPES OR FADES NECESSARY
        if self.transition_type == 'wipe' and self.transition_duration:
            #print('WIPE')
            self.current_scene.draw(self.screen)
            #for obj in self.persistent_objects:  # we should do this before wipes because otherwise they're on top of each other and it looks bad
            #    obj.draw(self.screen)

            if self.wipe_side == 'right':
                x = round(self.transition_counter / self.transition_duration * self.screen_width)
                self.screen.blit(self.transition_from, (x, 0), pygame.Rect(x, 0, self.screen_width-x, self.screen_height))
            elif self.wipe_side == 'left':
                x = round(self.transition_counter / self.transition_duration * self.screen_width)
                self.screen.blit(self.transition_from, (0, 0), pygame.Rect(0, 0, self.screen_width - x, self.screen_height))
            elif self.wipe_side == 'top':
                y = round(self.transition_counter / self.transition_duration * self.screen_height)
                self.screen.blit(self.transition_from, (0, 0), pygame.Rect(0, 0, self.screen_width, self.screen_height - y))
            elif self.wipe_side == 'bottom':
                y = round(self.transition_counter / self.transition_duration * self.screen_height)
                self.screen.blit(self.transition_from, (0, y), pygame.Rect(0, y, self.screen_width, self.screen_height - y))
            else:
                raise ValueError('Bad wipe option %s' % self.wipe_side)

            self.transition_counter += 1
            if self.transition_counter == self.transition_duration:  # CLEAR TRANSITION VARIABLES, WE FINISHED
                self.transition_from = None
                self.transition_type = None
                self.transition_counter = 0

        elif self.transition_type == 'fade' and self.transition_duration:
            self.current_scene.draw(self.screen)

            self.transition_from.set_alpha(round(255-(self.transition_counter / self.transition_duration)**2 * 255))
            self.screen.blit(self.transition_from, (0, 0))

            self.transition_counter += 1
            if self.transition_counter == self.transition_duration:   # CLEAR TRANSITION VARIABLES, WE FINISHED
                self.transition_from = None
                self.transition_type = None
                self.transition_counter = 0

        else: # no transitions, simple draw
            self.current_scene.draw(self.screen)

        # persistent objects should just be on top of everything
        for obj in self.persistent_objects:
            obj.draw(self.screen)

class Scene:
    def __init__(self, manager, layout=None, background=None, transition_duration=0, transition=None, wipe_side='left'):
        self.manager: SceneManager = manager
        self.layout: Layout = layout or Layout()
        self.cameras: [Tuple[str, Set[Callable]]] = []
        self.debug_rects: {str: graphics.Rect} = {}  # uuid: rect
        self.debug_texts: {str: graphics.Text} = {}  # uuid: text with uuid, pos, etc
        self.objects: [graphics.Object] = []
        self.background: Optional[pygame.Surface, tuple] = self.bg_to_surface(background) if type(background) is str else background if type(background) in (tuple, list, set) else None
        self.manager.add_scenes(self)

        self.transition_duration = transition_duration
        self.transition = transition
        self.wipe_side = wipe_side

    def bg_to_surface(self, fp):
        surf = pygame.image.load(fp)
        surf = pygame.transform.scale(surf, (self.manager.screen_width, self.manager.screen_height))
        return surf

    def update_cameras(self, offload=True):
        # updates all CLIENTS that are CURRENTLY REGISTERED (i.e. logged in) with the manager
        for uuid, _ in self.cameras:
            if cam := self.manager.cameras.get(uuid):
                cam.set_pos(*self.layout.get_pos(uuid))
                cam.set_dim(*(dim:=self.layout.get_dim(uuid)))
                if self.manager.debug:
                    text = self.debug_texts[uuid]
                    rect = self.debug_rects[uuid]  # just need to update these coords real quick for mouse drag purposes
                    text.x, text.y = rect.x, rect.y = cam.x, cam.y
                    text.reload(text=f'{uuid}@{text.x},{text.y}')

                print('Set dim %sx%s for %s' % (*dim, uuid))
                if offload:
                    self.manager.server.sessions[uuid].send(self.manager.RESOLUTION_SETTER+'_RESOLUTION', f'{dim[0]} {dim[1]}'.encode())

    def activate(self, client_offload=True):
        self.update_cameras(client_offload)
        for obj in self.objects:
            obj.reset()

    # THIS SHOULD BE DONE BEFORE ACTUAL CAMERA FEEDS ARE PASSED TO MANAGER - USED TO CREATE THE SCENE DATA
    def add(self, uuid, x, y, w, h, *frame_modifying_funcs):
        for cam in self.cameras:
            # ALREADY REGISTERED
            if cam[0] == uuid:
                return

        uuid = str(uuid)
        self.cameras.append((uuid, set(frame_modifying_funcs+(webcam.jpeg_decode,))))
        self.layout.register(uuid, x, y, w, h)
        if self.manager.debug:
            self.debug_rects[uuid] = graphics.Rect(x, y, w, h)
            self.debug_texts[uuid] = graphics.Text(f'{uuid}@({x},{y})', x, y, color=(255, 0, 0))

    def add_object(self, obj):
        self.objects.append(obj)

    def notify_new(self, uuid):
        if self.manager.current_scene is self:
            dim = self.layout.get_dim(uuid)
            #print('NEW GUY IN TOWN HAS DIMS', dim)
            self.manager.server.sessions[uuid].send(self.manager.RESOLUTION_SETTER+'_RESOLUTION', f'{dim[0]} {dim[1]}'.encode())

        self.layout.notify_new(uuid)
        if self.layout.DYNAMIC: self.update_cameras()  # for basictiler and similar

    def notify_death(self, uuid):
        self.layout.notify_death(uuid)
        if self.layout.DYNAMIC: self.update_cameras()  # for basictiler and similar

    def draw(self, screen: pygame.Surface):
        if type(self.background) in (tuple, list, set):  # bg is color
            screen.fill(self.background)
        elif self.background:  # bg is surface (i.e. image)
            screen.blit(self.background, (0,0))
        else:  # no bg, fill black
            screen.fill((0, 0, 0))

        for uuid, funcs in self.cameras:
            # if we have a feed for this uuid
            if cam := self.manager.cameras.get(uuid):
                text = None
                cam.set_pos(*self.layout.get_pos(uuid))

                # there's debug AND we have a feed - just text
                if self.manager.debug:
                    text = self.debug_texts[uuid]
                    rect = self.debug_rects[uuid]  # just need to update these coords real quick for mouse drag purposes
                    text.x, text.y = rect.x, rect.y = cam.x, cam.y
                    text.reload(text=f'{uuid}@{text.x},{text.y}')
                    rect.draw(screen)

                cam.draw(screen, *funcs)
                if text: text.draw(screen)

            # debug and the feed is MISSING - white rect and text
            elif self.manager.debug:
                rect = self.debug_rects[uuid]
                text = self.debug_texts[uuid]

                text.x, text.y = rect.x, rect.y = self.layout.get_pos(uuid)
                text.reload(text=f'{uuid}@{text.x},{text.y}')

                rect.draw(screen)
                text.draw(screen)

        # draw misc
        for obj in self.objects:
            obj.draw(screen)


class Layout:
    DYNAMIC = False
    def __init__(self):
        self.positions = {}
        self.dims = {}

    def register(self, uuid, x, y, w, h):
        uuid = str(uuid)
        self.positions[uuid] = x,y
        self.dims[uuid] = w,h

    def unregister(self, uuid):
        uuid = str(uuid)
        del self.positions[uuid], self.dims[uuid]

    def notify_new(self, uuid):
        return
    def notify_death(self, uuid):
        return

    def set_pos(self, uuid, x, y):
        self.positions[uuid] = x, y
    def set_dim(self, uuid, w, h):
        self.dims[uuid] = w, h

    def get_pos(self, uuid):
        return self.positions.get(str(uuid), (0,0))
    def get_dim(self, uuid):
        return self.dims.get(str(uuid), (0,0))


class BasicTiler(Layout):
    DYNAMIC = True
    def __init__(self, w, h, tilew, tileh, pad_edges=False):
        super().__init__()
        self.count = -1
        self.w = w
        self.h = h
        self.tw = tilew
        self.th = tileh
        self.x = 0
        self.y = 0

        self.pad_edges = pad_edges

        self.countx = self.w // self.tw
        self.county = self.h // self.th
        self.maximum = self.countx * self.county
        #      (fraction that can fit - actual that can fit) * size / (number +- 1 for padding)
        # i cant explain exactly why padding is count+1 instead of +2, but it is the case
        if pad_edges:
            self.padx = ((self.w / self.tw - self.countx) * self.tw / (self.countx + 1)) if self.countx > 1 else 0
            self.pady = ((self.h / self.th - self.county) * self.th / (self.county + 1)) if self.county > 1 else 0
        else:
            self.padx = ((self.w / self.tw - self.countx) * self.tw / (self.countx - 1)) if self.countx > 1 else 0
            self.pady = ((self.h / self.th - self.county) * self.th / (self.county - 1)) if self.county > 1 else 0

    def register(self, uuid, *_):
        print('NEW REGISTER')
        super().register(uuid, *self.new(), self.tw, self.th)

    def notify_new(self, new_uuid):
        return
    def notify_death(self, dead_uuid):
        self.count = -1
        for uuid in self.positions.keys():
            if uuid != dead_uuid:
                print('NEW DEATH')
                self.positions[uuid] = self.new()

    def new(self):
        if self.count == self.maximum-1:
            raise ValueError('Layout can\'t handle any more tiles!')

        self.count += 1
        x = y = 0

        # preliminary check so we can center a single input cam
        if self.countx < 2:
            x = self.w / 2
        if self.county < 2:
            y = self.h / 2

        #        (proper place on axis + centering) * wh + padding * (number on axis because it accumulates + 1 if the 0th place wants more than 0 padding)
        if not x:
            x = (self.count % self.countx + 0.5) * self.tw + self.padx * (self.count % self.countx + (1 if self.pad_edges else 0))
        if not y:
            y = (self.count // self.countx + 0.5) * self.th + self.pady * (self.count // self.countx + (1 if self.pad_edges else 0))

        print('NEW', x, y)
        return x, y


if __name__ == "__main__":
    tiler = BasicTiler(550, 550, 100, 100, False)
    while True:
        print(tiler.new())
