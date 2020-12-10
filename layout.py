from typing import Union

class Screen:
    def __init__(self, w, h):
        self.real_w = w
        self.real_h = h

    @property
    def center(self):
        return self.real_w // 2, self.real_h // 2

class Grid:
    def __init__(self, parent: Union[Screen, __class__], w=1, h=1, padr=0, padl=0, padt=0, padb=0):
        self.parent = parent
        self.w = w
        self.h = h
        self.real_w = parent.real_w
        self.real_h = parent.real_h
        self.pad_right = padr
        self.pad_left = padl
        self.pad_top = padt
        self.pad_bottom = padb

        self.tiles = [[Tile(self, 1/self.w, 1/self.h, x*self.real_w/self.w-, y) for x in range(self.w)] for y in range(self.h)]

    @property
    def center(self):
        return (self.real_w - self.pad_left - self.pad_right)//2, self.real_h//2

class Tile:
    def __init__(self, parent: Grid, wfrac, hfrac, realx, realy):
        self.parent = parent
        self.wfrac = wfrac
        self.hfrac = hfrac
        self.x = realx
        self.y = realy
        self.w = parent.real_w * wfrac - parent.pad_left - parent.pad_right
        self.h = parent.real_h * hfrac - parent.pad_top - parent.pad_bottom

    @property
    def center(self):
        return self.w // 2, self.h // 2