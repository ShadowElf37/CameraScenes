import pygame
import pygame.freetype
from webcam import scale_to, crop
import numpy
import os
from enum import Enum
from math import ceil, floor

BLACK = (0,0,0)
WHITE = (255, 255, 255)

class scale(Enum):
    CROP = 'crop'
    WFLEX = 'wflex'
    HFLEX = 'hflex'
    SET = FORCE = 'set'
    NONE = 'none'


class Object:
    def __init__(self, x=0, y=0, w=0, h=0, corner=0):
        self.x = self.ox = self.cx = x
        self.y = self.oy = self.cy = y
        self.w = self.ow = self.cw = w
        self.h = self.oh = self.ch = h
        # ox and cx are provided for whatever you might need them for
        # generally ox should be kept the same, and cx can be used for caching a second temporary position if x is already changed
        self.corner = corner  # positioning - 0 1 2 3 4 by property order below; 0 is center

    @property
    def rect(self):
        try:
            topleft = (self.center, self.top_left, self.top_right, self.bottom_left, self.bottom_right)[self.corner]
            return *topleft, topleft[0] + self.w, topleft[1] + self.h
        except IndexError:
            raise ValueError('Object has invalid draw corner %s' % self.corner)

    # ALL OF THESE ARE RELATIVE - DO NOT USE AS ACTUAL COORDINATES OF CENTER ETC
    # CENTER IS ACTUALLY A SHIFTED TOP LEFT
    # USE x,y FOR ACTUAL POSITION
    # WHAT THAT MEANS PHYSICALLY DEPENDS ON THE CORNER CHOSEN IN DRAW FUNCTIONS
    @property
    def center(self):
        return (self.x - round(self.w / 2), self.y - round(self.h / 2))
    @property
    def top_left(self):
        return (self.x, self.y)
    @property
    def top_right(self):
        return (self.x + self.w, self.y)
    @property
    def bottom_left(self):
        return (self.x, self.y + self.h)
    @property
    def bottom_right(self):
        return (self.x + self.w, self.y + self.h)

    def draw(self, screen: pygame.Surface):
        pass
        #screen.blit()
    def reset(self):
        pass
        # if animated, revert to first frame etc.

    def selective_blit(self, screen, py_object, xoffset=0, yoffset=0):
        try:
            true_topleft = (self.center, self.top_left, self.top_right, self.bottom_left, self.bottom_right)[self.corner]
            screen.blit(py_object, (true_topleft[0] + xoffset, true_topleft[1] + yoffset))
        except IndexError:
            raise ValueError('Invalid draw corner %s' % self.corner)
        return true_topleft


class Rect(Object):
    def draw(self, screen, xoffset=0, yoffset=0):
        if self.corner == 0:
            pygame.draw.rect(screen, WHITE, (self.center[0] + xoffset, self.center[1] + yoffset, self.w, self.h))
        elif self.corner == 1:
            pygame.draw.rect(screen, WHITE, (self.top_left[0] + xoffset, self.top_left[1] + yoffset, self.w, self.h))
        elif self.corner == 2:
            pygame.draw.rect(screen, WHITE, (self.top_right[0] + xoffset, self.top_right[1] + yoffset, self.w, self.h))
        elif self.corner == 3:
            pygame.draw.rect(screen, WHITE, (self.bottom_left[0] + xoffset, self.bottom_left[1] + yoffset, self.w, self.h))
        elif self.corner == 4:
            pygame.draw.rect(screen, WHITE, (self.bottom_right[0] + xoffset, self.bottom_right[1] + yoffset, self.w, self.h))
        else:
            raise ValueError('Invalid draw corner %s' % self.corner)


class Sprite(Object):
    REAL_FPS = 30

    # set fps to 0 for stills
    def __init__(self, imgfolder, x, y, fps=REAL_FPS, w=0, h=0, delete_on_end_frames=False, delete_on_end_move=False, loop_move=True, end_pos=(), move_duration=0, rotation=0, corner=0):
        """
        :param imgfolder: folder with alphabetically sorted frames for the animation
        :param x: x pos
        :param y: y pos
        :param fps: frames of the animation to play per second - FPS/fps is how many times it loops in one second - set to 0 for stills
        :param w: mandated width (dont use)
        :param h: mandated height (dont use)
        :param delete_on_end_frames: delete after looping through all frames
        :param delete_on_end_move: delete after completing one movement loop
        :param loop_move: loop the movement frames indefinitely
        :param end_pos: final position for movement to take you
        :param move_duration: duration, in frames, of movement - set to 0 for static sprites
        :param rotation: degrees rotation of image
        :param corner: see Object for more info
        """
        super().__init__(x, y, w, h, corner)

        self.folder = os.path.join('sprites', imgfolder)
        self.img_paths = []

        for dirpath, dirnames, filenames in os.walk(self.folder):
            for file in filenames:
                self.img_paths.append(os.path.join(dirpath, file))

        print('Loaded sprite from', self.img_paths)
        self.rotation = rotation

        self.imgs = [pygame.transform.rotate(pygame.image.load(fp), -self.rotation) for fp in sorted(self.img_paths)]
        self.frame = 0

        self.cw = self.imgs[0].get_width()
        self.ch = self.imgs[0].get_height()

        if self.w and self.h and (self.cw != self.w or self.ch != self.h):
            new_imgs = []
            for img in self.imgs:
                new_imgs.append(pygame.transform.scale(img, (self.w, self.h)))
            self.imgs = new_imgs
        else:
            self.w, self.h = self.cw, self.ch

        self.delete_on_end_move = delete_on_end_move
        self.loop_move = loop_move
        self.end_pos = end_pos
        self.movement_duration = move_duration
        self.move_counter = 0
        self.move_on_frame = 0
        self.dx = self.end_pos[0] - self.x
        self.dy = self.end_pos[1] - self.y
        self.baked_move_frames = ((self.ox + self.dx / self.movement_duration * i, self.oy + self.dy / self.movement_duration * i) for i in range(self.movement_duration+1))
        if self.end_pos:
            self.move_on_frame = self.REAL_FPS / self.movement_duration

        self.delete_on_end_frames = delete_on_end_frames
        self.fps = fps
        self.advance_counter = 0
        self.advance_on_frame = 0
        if fps:
            self.advance_on_frame = round(self.REAL_FPS / self.fps)

    def reset(self):
        self.frame = 0
        self.move_counter = 0
        self.baked_move_frames = ((self.ox + self.dx / self.movement_duration * i, self.oy + self.dy / self.movement_duration * i) for i in range(self.movement_duration+1))

    def advance_frame(self):
        self.frame += 1
        if self.frame == len(self.imgs):
            if self.delete_on_end_frames:
                self.frame = -1
            else:
                self.frame = 0

    def draw(self, screen):
        if self.frame != -1:
            # draw image
            self.selective_blit(screen, self.imgs[self.frame])
            # count up the frame counter - only advance the frame when we reach show_on_frame
            if self.fps and self.advance_on_frame != self.advance_counter:
                self.advance_counter += 1
            else:
                self.advance_counter = 0
                self.advance_frame()

            if self.movement_duration and self.move_counter != -1 and self.move_on_frame != self.move_counter:
                self.move_counter += 1
            else:
                try:
                    self.x, self.y = next(self.baked_move_frames)
                except StopIteration:
                    if self.delete_on_end_move:
                        self.frame = -1
                    elif self.loop_move:
                        self.baked_move_frames = ((self.ox + self.dx / self.movement_duration * i, self.oy + self.dy / self.movement_duration * i) for i in range(self.movement_duration+1))
                        self.x, self.y = next(self.baked_move_frames)
                    else:
                        self.move_counter = -1



class Text(Object):
    def __init__(self, text, x, y, font='Calibri', fontsize=24, color=WHITE):
        self.reload(text, font, fontsize, color)
        super().__init__(x, y, self.w, self.h)

    def reload(self, text=None, font=None, fontsize=None, color=None,):
        if text is not None: self.text = text.split('\n')
        if font is not None: self.font = font
        if color is not None: self.color = color
        if fontsize is not None: self.fontsize = fontsize

        self.py_font = pygame.freetype.SysFont(self.font, self.fontsize)
        if len(self.text) == 1:
            self.py_text, self.py_textbox = self.py_font.render(self.text[0], self.color)
            self.w, self.h = self.py_textbox.width, self.py_textbox.height
        else:
            self.w = None
            self.h = None

    def draw(self, screen):
        # SINGLE LINE - PRERENDERED
        if len(self.text) == 1:
            self.selective_blit(screen, self.py_text)
        # MULTILINE
        else:
            self.y = self.oy - (len(self.text)-1) * self.fontsize / 2
            for i, line in enumerate(self.text):
                py_text, py_textbox = self.py_font.render(line, self.color)
                self.w = py_textbox.width
                self.h = py_textbox.height
                self.selective_blit(screen, py_text, yoffset=self.fontsize * i)

            self.x, self.y = self.ox, self.oy


class WebcamViewer(Object):
    def __init__(self, x=0, y=0, w=0, h=0, dim_enforcer=None):
        # NOTE: used to contain a cam/buffer input, this is now handled in mainloop for direct control of webcam data
        super().__init__(x, y, w, h)
        self.surf = pygame.Surface((self.w, self.h))
        self.old_frame: numpy.ndarray = None
        self.new_frame: numpy.ndarray = None

        self.dim_enforcer = dim_enforcer

    # this is necessary so that if we draw without a new frame (because of lag or something) the viewer won't be drawn as a black square
    def take_frame(self, frame):
        self.new_frame = frame

    def set_pos(self, x, y):
        self.x, self.y = x, y
    def set_dim(self, w, h):
        print('New dimensions set:', w, h)
        self.w, self.h = w, h

    def draw(self, screen, *modifiers):
        # see take_frame - otherwise it would flicker abhorrently
        if numpy.array_equal(self.old_frame, self.new_frame):
            self.selective_blit(screen, self.surf)
            return

        self.surf.fill(WHITE)
        if self.new_frame is None or not any(self.new_frame.shape[:2]):
            return

        # MODIFIERS SHOULD BE FUNCTIONS THAT CAN ACT ON THE FRAME ALONE
        # CAN BE USED FOR EASY CROP AND SCALE
        for func in modifiers:
            self.new_frame: numpy.ndarray = func(self.new_frame)

        # we will be compatible with all possible frame sizes
        # set just scales it in all dims to the box size
        #print(self.dim_enforcer)

        #print(self.x, self.y)

        if self.dim_enforcer == scale.SET:
            #print(self.new_frame.shape, self.w, self.h, self.surf.get_width(), self.surf.get_height())
            self.new_frame = scale_to(self.new_frame, self.w, self.h)
            #print(self.new_frame.shape, self.w, self.h, self.surf.get_width(), self.surf.get_height())

        # preserve box height and crop width if it's too big
        elif self.dim_enforcer == scale.CROP:
            #print("USING CROP")
            w, h, _ = self.new_frame.shape  # note that we throw out client h and preserve preset box h
            nw = round(w * self.h / h)
            #print(w, h, nw, self.w, self.h)
            self.new_frame = scale_to(self.new_frame, nw, self.h)  # first preserve the h and flex the w down to a proportional level


            diff = nw - self.w  # distance to box bounds
            #print(self.w, nw, w, self.surf.get_width(), diff)
            #print('1:', (self.w, self.h), (self.cw, self.ch), (w,h), (self.surf.get_width(), self.surf.get_height()), diff, nw)
            if diff > 0:  # if this is false, the frame is actually smaller than the box, and it's not like we can expand it
                self.new_frame = crop(self.new_frame, diff//2, 0, nw-diff//2, self.h)

            # if our surface is out of date, flex_dim won't change that - gotta fix it ourselves
            # scenes do update our self.w and self.h, but if we're flexing then the surface won't get that update, and it needs to
            # we use cw to cache surface width, and when it's out of date with our scene, we fix it

                if self.cw != (nw-diff):  # well now we need a new surface because the dims dont match
                    self.w = self.cw = nw-diff
                    self.surf = pygame.Surface((self.w, self.h))

                elif self.h != self.ch:
                    self.ch = self.h
                    self.surf = pygame.Surface((self.w, self.h))

            # if we need to resize the frame AND its smaller than the box
            elif self.w != nw or self.cw != nw:  # well now we need a new surface because the dims dont match
                self.w = self.cw = nw
                self.surf = pygame.Surface((self.w, self.h))

            elif self.h != self.ch:
                self.ch = self.h
                self.surf = pygame.Surface((self.w, self.h))

            #print('2:', (self.w, self.h), (self.cw, self.ch), (w,h), (self.surf.get_width(), self.surf.get_height()), diff, nw)

            #print('#', self.surf.get_width(), self.surf.get_height(), self.w, self.h, w, h, nw, diff, nw-diff)

        # preserve box width/height but keep the other proportional, even if it's outside or inside the box dims
        # if we wanna match the height and modify the width
        elif self.dim_enforcer == scale.WFLEX:

            w, h, _ = self.new_frame.shape  # note that we throw out client h and preserve preset box h
            nw = round(w * self.h / h)
            self.new_frame = scale_to(self.new_frame, nw, self.h)

            # if our surface is out of date, flex_dim won't change that - gotta fix it ourselves
            # scenes do update our self.w and self.h, but if we're flexing then the surface won't get that update, and it needs to
            # we use cw to cache surface width, and when it's out of date with our scene (it lags behind w), we fix it
            if self.w != nw or self.cw != nw:  # well now we need a new surface because the dims dont match
                self.w = self.cw = nw
                self.surf = pygame.Surface((self.w, self.h))

            elif self.h != self.ch:
                self.ch = self.h
                self.surf = pygame.Surface((self.w, self.h))

        elif self.dim_enforcer == scale.HFLEX:

            w, h, _ = self.new_frame.shape  # note that we throw out client w and preserve preset box w
            nh = round(h * self.w / w)
            self.new_frame = scale_to(self.new_frame, self.w, nh)

            # if our surface is out of date, flex_dim won't change that - gotta fix it ourselves
            # scenes do update our self.w and self.h, but if we're flexing then the surface won't get that update, and it needs to
            # we use ch to cache surface height, and when it's out of date with our scene (it lags behind h), we fix it
            if self.h != nh or self.ch != nh:  # well now we need a new surface because the dims dont match
                self.h = self.ch = nh
                self.surf = pygame.Surface((self.w, self.h))

            elif self.w != self.cw:
                self.cw = self.w
                self.surf = pygame.Surface((self.w, self.h))

        # if we're not doing any of this then we have to adjust our w/h to client's frame, regardless of how big it is
        elif self.dim_enforcer == scale.NONE:
            w, h, *_ = self.new_frame.shape

            # this surface is cached and reused as long as the size doesn't change
            if self.cw != w or self.ch != h:  # well now we need a new surface because the dims dont match
                self.w, self.h = self.cw, self.ch = w, h  # cached as well since scenes directly set w/h, cached will lag behind and we can use that
                self.surf = pygame.Surface((self.w, self.h))

        else:
            print("graphics.py line ~360, NO SCALER", self.dim_enforcer)

        self.cw, self.ch = self.w, self.h

        self.surf = pygame.Surface((self.w, self.h))
        try:
            pygame.surfarray.blit_array(self.surf, self.new_frame)
        except ValueError:
            raise ValueError(str(('CAM DIED', self.surf.get_width(), self.surf.get_height(), self.w, self.h, self.new_frame.shape, locals().get('nw'), locals().get('diff'))))

        self.old_frame = self.new_frame
        self.selective_blit(screen, self.surf)
