import pygame
from typing import Optional
import graphics

class SceneManager:
    def __init__(self, server):
        self.server = server
        self.cameras: {str: graphics.WebcamViewer} = {}
        self.persistent_objects: [graphics.Object] = []
        self.scenes: [Scene] = []
        self.current_i = -1
        self.current_scene: Optional[Scene] = None

    def register_camera(self, uuid, viewer):
        self.cameras[uuid] = viewer

    def add_scene(self, scene):
        self.scenes.append(scene)

    def set_scene(self, i):
        self.current_i = i
        self.current_scene = self.scenes[i]
        self.current_scene.activate()

    def next_scene(self):
        self.set_scene(self.current_i + 1)

    def draw(self, screen):
        self.current_scene.draw(screen)
        for obj in self.persistent_objects:
            obj.draw(screen)

class Scene:
    def __init__(self, manager, layout=None):
        self.manager: SceneManager = manager
        self.layout: Layout = layout or Layout()
        self.cameras: [graphics.WebcamViewer] = []
        self.background: Optional[pygame.Surface] = None

    def activate(self):
        for uuid in self.cameras:
            cam = self.manager.cameras[uuid]
            cam.set_pos(*self.layout.get_pos(uuid))
            cam.set_dim(*self.layout.get_dim(uuid))

    def use_camera(self, uuid, *frame_modifying_funcs):
        self.cameras.append((uuid, frame_modifying_funcs))

    def draw(self, screen):
        screen.blit(self.background)
        for uuid, funcs in self.cameras:
            self.manager.cameras[uuid].draw(screen, *funcs)


class Layout:
    def __init__(self):
        self.positions = {}
        self.dims = {}

    def register(self, uuid, x, y, w, h):
        self.positions[uuid] = x,y
        self.dims[uuid] = w,h

    def get_pos(self, uuid):
        return self.positions[uuid]

    def get_dim(self, uuid):
        return self.dims[uuid]





class BasicTiler:
    def __init__(self, w, h, tilew, tileh, pad_edges=False):
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

    def go_back_one(self):
        self.count -= 1

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

        return x, y


if __name__ == "__main__":
    tiler = BasicTiler(550, 550, 100, 100, False)
    while True:
        print(tiler.new())
