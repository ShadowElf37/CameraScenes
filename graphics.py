import pygame
import pygame.freetype
from webcam import scale_to
import numpy

BLACK = (0,0,0)
WHITE = (255, 255, 255)

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
        return (self.x - self.w // 2, self.y - self.h // 2)
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
    def __init__(self, imgfps: tuple, x, y, fps=REAL_FPS, w=0, h=0, delete_on_end=False, corner=0):
        super().__init__(x, y, w, h, corner)
        self.imgs = [pygame.image.load(fp) for fp in imgfps]
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

        self.delete_on_end = delete_on_end
        self.fps = fps
        self.advance_counter = 0
        self.advance_on_frame = 0
        if fps:
            self.advance_on_frame = round(self.REAL_FPS / self.fps)

    def reset(self):
        self.frame = 0

    def advance_frame(self):
        self.frame += 1
        if self.frame == len(self.imgs):
            if self.delete_on_end:
                self.frame = -1
            else:
                self.reset()

    def draw(self, screen):
        if self.frame != -1:
            # draw image
            self.selective_blit(screen, self.imgs[self.frame])
            # count up the frame counter - only advance the frame when we reach show_on_frame
            if self.fps and self.advance_on_frame != self.advance_counter:
                self.advance_counter += 1
                return
            self.advance_counter = 0
            self.advance_frame()


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
            self.y = self.oy - len(self.text) * self.fontsize / 2
            for i, line in enumerate(self.text):
                py_text, py_textbox = self.py_font.render(line, self.color)
                self.w = py_textbox.width
                self.h = py_textbox.height
                self.selective_blit(screen, py_text, yoffset=self.fontsize * i)

            self.x, self.y = self.ox, self.oy


class WebcamViewer(Object):
    def __init__(self, x=0, y=0, w=0, h=0, enforce_dim=False):
        # NOTE: used to contain a cam/buffer input, this is now handled in mainloop for direct control of webcam data
        super().__init__(x, y, w, h)
        self.surf = pygame.Surface((self.w, self.h))
        self.old_frame: numpy.ndarray = None
        self.new_frame: numpy.ndarray = None

        self.enforce_dim = enforce_dim


    # this is necessary so that if we draw without a new frame (because of lag or something) the viewer won't be drawn as a black square
    def take_frame(self, frame):
        self.new_frame = frame

    def set_pos(self, x, y):
        self.x, self.y = x, y
    def set_dim(self, w, h):
        self.w, self.h = w, h

    def draw(self, screen, *modifiers):
        # see take_frame - otherwise it would flicker abhorrently
        if numpy.array_equal(self.old_frame, self.new_frame):
            self.selective_blit(screen, self.surf)
            return

        self.surf.fill(WHITE)
        if self.new_frame is None:
            return

        # MODIFIERS SHOULD BE FUNCTIONS THAT CAN ACT ON THE FRAME ALONE
        # CAN BE USED FOR EASY CROP AND SCALE
        for func in modifiers:
            self.new_frame: numpy.ndarray = func(self.new_frame)

        # we will be compatible with all possible frame sizes
        # no clue what we're receiving sadly
        # if we want specific dimensions, use modifiers to crop or scale on client or server side, or use enforce_dim, which will scale automatically to ow/oh
        if self.enforce_dim:
            self.new_frame = scale_to(self.new_frame, self.w, self.h)
        else:
            w, h, *_ = self.new_frame.shape
            if self.w != w or self.h != h and self.new_frame:
                self.w, self.h = w, h
                self.surf = pygame.Surface((w, h))

        pygame.surfarray.blit_array(self.surf, self.new_frame)

        self.old_frame = self.new_frame
        self.selective_blit(screen, self.surf)
