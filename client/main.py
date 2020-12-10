from pygame.locals import KEYDOWN, K_ESCAPE, K_q
import pygame
import pygame.freetype
import webcam
from sys import exit
from time import sleep
from cv2 import COLOR_BGR2RGB

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 60


pygame.init()
pygame.display.set_caption("WEBCAM WOOOOOOOOOOO")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

cam = webcam.Webcam(COLOR_BGR2RGB, flip=True, swap_axes=True, resolution=(640, 480))
webcam_viewer = pygame.Surface((cam.width, cam.height))

cool_font = pygame.freetype.SysFont('Calibri', 24)
cool_text, cool_text_box = cool_font.render('pogchamp', WHITE)

while True:
    screen.fill(BLACK)
    webcam_viewer.fill(BLACK)
    frame = cam.read()

    pygame.surfarray.blit_array(webcam_viewer, frame)

    screen.blit(webcam_viewer, ((WIDTH-cam.width)/2, 0))
    screen.blit(cool_text, ((WIDTH-cool_text_box.width)/2, 500))

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            exit()

    clock.tick(FPS)
