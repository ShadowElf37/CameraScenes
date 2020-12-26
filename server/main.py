from sys import path
path.append('..')

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY
import pygame.locals
import network
import audio
import webcam
import graphics
import layout
import pickle
import json
from sys import exit
from network_common import UDPSession, iterq

path.append('..')

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
text = graphics.Text('Server POGGERS', WIDTH / 2, 600)

aud = audio.MultipleAudioOutput()

server = network.UDPManager(37001)
server.init()

preview_tiler = layout.BasicTiler(WIDTH, HEIGHT, CAM_WIDTH, CAM_HEIGHT, True)

cameras: {str: graphics.WebcamViewer} = {}  # BLANK {'1': graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT)}
objects: [graphics.Object] = [text]

import g729a
audio_decoder = g729a.G729Adecoder()

print('Server started.')
while server.running:
    screen.fill(BLACK)

    for data in iterq(server.META_QUEUE):
        uuid = data[0]
        if data[2] == 'OPEN':
            print('NEW CLIENT', uuid)
            server.sessions[uuid].send('CONTINUE')
            # add an audio processor for them
            aud.new_output(uuid)
            # make a cam viewer
            cameras[uuid] = cam = graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT, enforce_dim=True)
        elif data[2] == 'CLOSE':
            del cameras[uuid]
            aud.close_output(uuid)
            preview_tiler.go_back_one()

    for uuid, frame in iterq(server.VIDEO_QUEUE):
        cam = cameras.get(uuid)
        if cam is None:
            continue
        cam.take_frame(pickle.loads(frame))
        #server.sessions[uuid].send('PRINT', b'hello fren')

    for cam in cameras.values():
        cam.draw(screen, webcam.jpeg_decode)

    text.draw(screen)

    # PLAY AUDIO FROM CLIENTS
    for chunk in iterq(server.AUDIO_QUEUE):
        aud.process(*chunk)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            break

    clock.tick(FPS)

for session in server.sessions.values():
    session._send('DIE')
server.close()
pygame.display.quit()
print('Died safely.')
exit(0)
