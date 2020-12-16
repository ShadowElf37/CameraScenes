# GUI NEEDS CUSTOM BACKGROUND
# SPRITE ANIMATIONS
# USEABLE GRAPHICS LIBRARY
import pygame.locals
import network
#import audio
import webcam
import graphics
import layout
import pickle

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

#aud = audio.AudioInterface()
#aud.activate()

server = network.UDPManager(37001)
server.init()

preview_tiler = layout.BasicTiler(WIDTH, HEIGHT, CAM_WIDTH, CAM_HEIGHT, True)

cameras: {str: graphics.WebcamViewer} = {}  # BLANK {'1': graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT)}
objects: [graphics.Object] = [text]

print('Server started.')
while True:
    #for chunk in aud.pending():
    #    for client in server.sessions.values():
    #        pass
            #client.send('AUDIO', chunk)
            #client.send('VIDEO', cam.read())

    screen.fill(BLACK)

    while not server.VIDEO_QUEUE.empty():
        uuid, frame = server.VIDEO_QUEUE.get()
        cam = cameras.get(uuid)
        if cam is None: # make new viewer
            cameras[uuid] = cam = graphics.WebcamViewer(*preview_tiler.new(), CAM_WIDTH, CAM_HEIGHT, enforce_dim=True)

        cam.take_frame(pickle.loads(frame))
        server.sessions[uuid].send('PRINT', b'hello fren')

    for cam in cameras.values():
        cam.draw(screen, webcam.jpeg_decode)

    text.draw(screen)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print('User quit.')
            pygame.display.quit()
            exit()

    clock.tick(FPS)
