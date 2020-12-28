import pygame
from typing import Optional, Callable, Tuple, Set
import graphics
import webcam
from pipe import Pipe

class SceneManager:
    def __init__(self, server, use_pipe=True):
        self.server = server
        self.cameras: {str: graphics.WebcamViewer} = {}
        self.persistent_objects: [graphics.Object] = []
        self.scenes: [Scene] = []
        self.current_i = -1
        self.current_scene: Optional[Scene] = None

        self.cues = Pipe(at=38051)

        if use_pipe:
            print('The SceneManager Pipe has been created. Please establish the other end now.')
            self.cues.open()
            print('Pipe established!')

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

    def set_scene(self, i):
        if i > len(self.scenes) or i < 0: return
        self.current_i = i
        self.current_scene = self.scenes[i]
        self.current_scene.activate()

    def next(self):
        self.set_scene(self.current_i + 1)
    def back(self):
        self.set_scene(self.current_i - 1)
    def last(self):
        self.set_scene(len(self.scenes))
    def first(self):
        self.set_scene(0)

    def draw(self, screen):
        for command in iter(self.cues):
            exec(command)

        self.current_scene.draw(screen)
        for obj in self.persistent_objects:
            obj.draw(screen)

class Scene:
    def __init__(self, manager, layout=None, background=None):
        self.manager: SceneManager = manager
        self.layout: Layout = layout or Layout()
        self.cameras: [Tuple[str, Set[Callable]]] = []
        self.objects: [graphics.Object] = []
        self.background: Optional[pygame.Surface, tuple] = background
        self.manager.add_scenes(self)

    def update_cameras(self):
        for uuid, _ in self.cameras:
            if cam := self.manager.cameras.get(uuid):
                cam.set_pos(*self.layout.get_pos(uuid))
                cam.set_dim(*self.layout.get_dim(uuid))

    def activate(self):
        self.update_cameras()
        for obj in self.objects:
            obj.reset()

    def add(self, uuid, x, y, w, h, *frame_modifying_funcs):
        for cam in self.cameras:
            # ALREADY REGISTERED
            if cam[0] == uuid:
                return

        uuid = str(uuid)
        self.cameras.append((uuid, set(frame_modifying_funcs+(webcam.jpeg_decode,))))
        self.layout.register(uuid, x, y, w, h)
        if cam := self.manager.cameras.get(uuid):
            cam.set_pos(*self.layout.get_pos(uuid))
            cam.set_dim(*self.layout.get_dim(uuid))

    def add_object(self, obj):
        self.objects.append(obj)

    def notify_new(self, uuid):
        self.layout.notify_new(uuid)
        self.update_cameras()

    def notify_death(self, uuid):
        self.layout.notify_death(uuid)
        self.update_cameras()

    def draw(self, screen: pygame.Surface):
        if type(self.background) is tuple:
            screen.fill(self.background)
        elif self.background:
            screen.blit(self.background, (0,0))
        else:
            screen.fill((0,0,0))

        for uuid, funcs in self.cameras:
            if cam := self.manager.cameras.get(uuid):
                cam.draw(screen, *funcs)

        for obj in self.objects:
            obj.draw(screen)


class Layout:
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

    def get_pos(self, uuid):
        uuid = str(uuid)
        return self.positions[uuid]
    def get_dim(self, uuid):
        uuid = str(uuid)
        return self.dims[uuid]


class BasicTiler(Layout):
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
