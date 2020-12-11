# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY

import pygame.locals
import graphics

clock = pygame.time.Clock()

WIDTH = 1000
HEIGHT = 700
FPS = 60

pygame.init()
pygame.display.set_caption("WEBCAM WOOOOOOOOOOO")
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.locals.RESIZABLE)

objects: [graphics.Object] = []

while True:
    for object in objects:
        object.draw()

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            exit()

    clock.tick(FPS)