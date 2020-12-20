from sys import path
path.append('..')

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
from network_common import UDPSession

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
while True:
    screen.fill(BLACK)

    while not server.VIDEO_QUEUE.empty():
        uuid, frame = server.VIDEO_QUEUE.get()
        cam = cameras.get(uuid)

        # NEW GUY SPOTTED
        if cam is None: # ALL CLIENT INITIALIZATION GOES HERE
            print('NEW CLIENT', uuid)
            # tell everyone to give them audio
            client: UDPSession
            new_session: UDPSession = server.sessions[uuid]
            for client in server.sessions.values():
                if client != new_session:
                    client.send('ADD_CLIENT_TABLE', json.dumps(((new_session.ip, new_session.port, uuid),)).encode())
                else:
                    client.send('ADD_CLIENT_TABLE', json.dumps([(s.ip, s.port, s.uuid) for s in server.sessions.values() if s is not client]).encode())

            # add an audio processor for them
            aud.new_output(uuid)

            # make a cam viewer
            cameras[uuid] = cam = graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT, enforce_dim=True)

        cam.take_frame(pickle.loads(frame))
        #server.sessions[uuid].send('PRINT', b'hello fren')

    for cam in cameras.values():
        cam.draw(screen, webcam.jpeg_decode)

    text.draw(screen)

    # PLAY AUDIO FROM CLIENTS
    while not server.AUDIO_QUEUE.empty():
        aud.process(*server.AUDIO_QUEUE.get())

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            pygame.display.quit()
            exit()

    clock.tick(FPS)
