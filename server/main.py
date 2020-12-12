# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY
import pygame.freetype
import pygame.locals
import graphics
import webcam
import network
import audio
from cv2 import COLOR_BGR2RGB

clock = pygame.time.Clock()

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30

pygame.init()
pygame.display.set_caption("WEBCAM WOOOOOOOOOOO")
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.locals.RESIZABLE)

cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75)
text = graphics.Text('SERVER', WIDTH/2, 600)

aud = audio.AudioInterface()
aud.activate()

server = network.UDPManager(37001)
server.init()

cam_viewer = graphics.WebcamViewer(None, WIDTH/2, HEIGHT/2, 400, 200)

cameras: [graphics.WebcamViewer] = [cam_viewer]
objects: [graphics.Object] = [text]

while True:
    for chunk in aud.pending():
        for client in server.sessions.values():
            client.send('AUDIO', chunk)
            client.send('VIDEO', cam.read())

    screen.fill(BLACK)

    while not server.VIDEO_QUEUE.empty():
        # TODO: match viewers to camera streams in the video queue, loop through cameras[]
        cam_viewer.draw(screen, webcam.jpeg_decode, frame=server.VIDEO_QUEUE.get())
    for object in objects:
        object.draw(screen)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            exit()

    clock.tick(FPS)