import pygame.freetype
import webcam
from sys import exit
import graphics
import network
#import audio
import pickle
from cv2 import COLOR_BGR2RGB

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30


pygame.init()
pygame.display.set_caption("Scene Manager - Client")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75) #device=r'C:\Users\Key Cohen Office\Desktop\My Movie.mp4'
text = graphics.Text('Client POGGERS', WIDTH/2, 600)

#aud = audio.AudioInterface()
#aud.activate()

client = network.UDPClient('73.166.38.74', 37001, override_uuid='tester77')
client.init()

cam_viewer = graphics.WebcamViewer(WIDTH/2, HEIGHT/2, 640, 480, enforce_dim=True)

print(cam_viewer.w, cam_viewer.h)
while True:
    #for chunk in aud.pending():
    #    client.session.send('AUDIO', chunk)
    frame = cam.read()
    client.session.send('VIDEO', pickle.dumps(frame))

    screen.fill(BLACK)

    cam_viewer.take_frame(frame)
    cam_viewer.draw(screen, webcam.jpeg_decode)
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
