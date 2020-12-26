from sys import path
path.append('..')

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame.freetype
from sys import exit
import webcam
import graphics
import network
import audio
import pickle
from cv2 import COLOR_BGR2RGB
from network_common import iterq


BLACK = (0,0,0)
WHITE = (255, 255, 255)

WIDTH = 1000
HEIGHT = 700
FPS = 30


# GET UUID
import tkinter as tk

root = tk.Tk()
root.title('ID Entry')
uid = tk.StringVar(value='')

uid_text = tk.Label(root, text='Enter ID')
uid_entry = tk.Entry(root, textvar=uid)
submit = tk.Button(root, text='Submit', command=lambda *_: root.destroy() if uid_entry.get() != '' else 0)
root.bind('<Return>', submit.invoke)

uid_text.pack()
uid_entry.pack(padx=20)
submit.pack(pady=10)

try:
    root.mainloop()
except tk.TclError:
    pass
# END GET UUID
uuid = uid.get()
del uid, root, tk, submit, uid_entry, uid_text
# ACCESS WITH uuid


pygame.init()
pygame.display.set_caption("Scene Manager - Client")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

loading_text = graphics.Text('Loading...', WIDTH/2, HEIGHT/2)
loading_text.draw(screen)
pygame.display.flip()

print('Opening webcam...')
cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, resolution=(640, 480), compress_quality=75) #device=r'C:\Users\Key Cohen Office\Desktop\My Movie.mp4'
text = graphics.Text('Client POGGERS', WIDTH/2, 600)

aud = audio.AudioInterface()

client = network.UDPClient('73.166.38.74', 37001, override_uuid=uuid)
client.init()

cam_viewer = graphics.WebcamViewer(WIDTH / 2, HEIGHT / 2, 640, 480, enforce_dim=True)

print('Client starting at', str(cam_viewer.w)+'x'+str(cam_viewer.h))
client.session.send('OPEN')
if client.META_QUEUE.get(timeout=6) != 'CONTINUE':
    raise ConnectionRefusedError('Server manually refused the connection request :(')

aud.activate()
while client.running:
    for chunk in aud.pending():
        client.session.send('AUDIO', chunk)

    for chunk in iterq(client.AUDIO_QUEUE):
        aud.write(*chunk)

    for data in iterq(client.META_QUEUE):
        if data == 'DIE':
            break

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
            break
        #elif event.type == VIDEORESIZE:
        #    screen.blit(pygame.transform.scale(pic, event.dict['size']), (0, 0))
        #    pygame.display.update()
        #elif event.type == VIDEOEXPOSE:  # handles window minimising/maximising
        #    screen.fill((0, 0, 0))
        #    screen.blit(pygame.transform.scale(pic, screen.get_size()), (0, 0))
        #    pygame.display.update()

    clock.tick(FPS)


client.session._send('CLOSE')
client.close()
pygame.quit()
print('Died safely.')
exit(0)