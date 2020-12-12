import pygame
import cv2 as cv
import numpy
from typing import Union

BLACK = (0,0,0)
WHITE = (255, 255, 255)

class Object:
    def __init__(self, x, y, w, h, corner=0):
        self.x = x
        self.y = y
        self.w = self.ow = self.cw = w
        self.h = self.oh = self.ch = h
        # ow/oh don't need to be used but are nice for original w/h
        # cw/ch should be used for caching positions so rescaling doesn't need to be done every frame
        self.corner = corner  # positioning - 0 1 2 3 4 by property order below; 0 is center

    @property
    def center(self):
        return (self.x - self.w / 2, self.y - self.h / 2)
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

    def selective_blit(self, screen, py_object):
        if self.corner == 0:
            screen.blit(py_object, self.center)
        elif self.corner == 1:
            screen.blit(py_object, self.top_left)
        elif self.corner == 2:
            screen.blit(py_object, self.top_right)
        elif self.corner == 3:
            screen.blit(py_object, self.bottom_left)
        elif self.corner == 4:
            screen.blit(py_object, self.bottom_right)
        else:
            raise ValueError('Invalid draw corner %s' % self.corner)


class Text(Object):
    def __init__(self, text, x, y, font='Calibri', fontsize=24, color=WHITE):
        self.text = text
        self.font = font
        self.fontsize = fontsize
        self.color = color
        self.py_font = pygame.freetype.SysFont(self.font, self.fontsize)
        self.py_text, self.py_textbox = self.py_font.render(self.text, self.color)
        super().__init__(x, y, self.py_textbox.width, self.py_textbox.height)

    def reload(self):
        self.py_font = pygame.freetype.SysFont(self.font, self.fontsize)
        self.py_text, self.py_textbox = self.py_font.render(self.text, self.color)

    def draw(self, screen):
        self.selective_blit(screen, self.py_text)


class WebcamViewer(Object):
    def __init__(self, cam: Union[cv.VideoCapture, None], x, y, w=0, h=0):
        super().__init__(x, y, w, h)
        self.cam = cam  # this can be any buffer with read() returning opencv frames, can be used in both client and server
        self.surf = pygame.Surface((self.w, self.h))

    def draw(self, screen, *modifiers, frame=None):
        if self.cam is not None:
            frame = self.cam.read()
        elif frame is None:
            return

        self.surf.fill(BLACK)

        # MODIFIERS SHOULD BE FUNCTIONS THAT CAN ACT ON THE FRAME ALONE
        # CAN BE USED FOR EASY CROP AND SCALE
        for func in modifiers:
            frame: numpy.ndarray = func(frame)

        # we will be compatible with all possible frame sizes
        # no clue what we're receiving sadly
        # if we want specific dimensions, use modifiers to crop or scale on client or server side
        w, h, *_ = frame.shape
        if self.w != w or self.h != h and frame:
            self.w, self.h = w, h
            self.surf = pygame.Surface((w, h))
        pygame.surfarray.blit_array(self.surf, frame)

        self.selective_blit(screen, self.surf)