# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY
import pygame.freetype
import pygame.locals
import graphics
import webcam
import network
#import audio
import layout
import numpy
import pickle
from cv2 import COLOR_BGR2RGB

clock = pygame.time.Clock()

BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30

CAM_WIDTH = 400
CAM_HEIGHT = 300

pygame.init()
pygame.display.set_caption("Scene Manager - Server")
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.locals.RESIZABLE)

#cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75)
text = graphics.Text('PogU', WIDTH/2, 600)

#aud = audio.AudioInterface()
#aud.activate()

server = network.UDPManager(37001)
server.init()

cameras: {str: graphics.WebcamViewer} = {}
objects: [graphics.Object] = [text]

preview_tiler = layout.BasicTiler(WIDTH, HEIGHT, CAM_WIDTH, CAM_HEIGHT, True)

print('Application started!')
while True:
    #for chunk in aud.pending():
    #    for client in server.sessions.values():
    #        pass
            #client.send('AUDIO', chunk)
            #client.send('VIDEO', cam.read())

    #screen.fill(BLACK)

    while not server.VIDEO_QUEUE.empty():
        uuid, frame = server.VIDEO_QUEUE.get()
        cam = cameras.get(uuid)
        if cam is None: # make new viewer
            cameras[uuid] = cam = graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT)

        cam.take_frame(pickle.loads(frame))

    for cam in cameras.values():
        cam.draw(screen, webcam.jpeg_decode)

    text.draw(screen)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            exit()

    clock.tick(FPS)