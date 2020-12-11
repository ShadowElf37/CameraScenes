from pygame.locals import KEYDOWN, K_ESCAPE, K_q
import pygame
import pygame.freetype
import webcam
from sys import exit
import graphics
from time import sleep
from cv2 import COLOR_BGR2RGB

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30


pygame.init()
pygame.display.set_caption("Scene Manager")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75)

cam_viewer = graphics.WebcamViewer(cam, WIDTH/2, HEIGHT/2, 400, 200)

text = graphics.Text('POGGERS', WIDTH/2, 600)

i = 0
print(cam_viewer.w, cam_viewer.h)
while True:
    screen.fill(BLACK)

    i += 1
    if i > 30:
        cam_viewer.draw(screen, webcam.jpeg_decode, lambda frame: webcam.crop(frame, 640 // 2 - 200, 480 // 2 - 100, 640 // 2 + 200, 480 // 2 + 100))
    else:
        cam_viewer.draw(screen, webcam.jpeg_decode)
    if i == 60:
        i = 0


    text.draw(screen)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            exit()
        #elif event.type == VIDEORESIZE:
        #    screen.blit(pygame.transform.scale(pic, event.dict['size']), (0, 0))
        #    pygame.display.update()
        #elif event.type == VIDEOEXPOSE:  # handles window minimising/maximising
        #    screen.fill((0, 0, 0))
        #    screen.blit(pygame.transform.scale(pic, screen.get_size()), (0, 0))
        #    pygame.display.update()

    clock.tick(FPS)
