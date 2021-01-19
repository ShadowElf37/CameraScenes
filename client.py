from sys import path
path.append('')

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame.freetype
from sys import exit
import sys
import webcam
import graphics
import network_client as network
import audio
import pickle
from cv2 import COLOR_BGR2RGB
from network_common import iterq
from queue import Empty
from time import sleep
import traceback
import logging


BLACK = (0,0,0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

WIDTH = 1000
HEIGHT = 700
FPS = 30
RUNNING = False
FIXED_VIEWER = False


# GET UUID
import tkinter as tk

done = False
def quit_tk(*_):
    global done
    done = True
    root.destroy()

root = tk.Tk()
root.title('ID Entry')
root.focus()
uid = tk.StringVar(value='')

uid_text = tk.Label(root, text='Enter ID')
uid_entry = tk.Entry(root, textvar=uid)
submit = tk.Button(root, text='Submit', command=lambda *_: root.destroy() if uid_entry.get() != '' else 0)
root.bind('<Return>', lambda *_: submit.invoke())

uid_text.pack()
uid_entry.pack(padx=20)
submit.pack(pady=10)

root.protocol("WM_DELETE_WINDOW", quit_tk)

try:
    root.mainloop()
except tk.TclError:
    uid_text.destroy()
    uid_entry.destroy()
    submit.destroy()
    root.quit()

# END GET UUID
uuid = uid.get().strip()
if done or not uuid:
    exit()
del uid, tk, submit, uid_entry, uid_text
# ACCESS WITH uuid


pygame.init()
pygame.display.set_caption("Proscenium Client")

import sys
if getattr(sys, 'frozen', False):
    pygame.display.set_icon(pygame.image.load(os.path.join(sys._MEIPASS, 'images/favicon.png')))
else:
    pygame.display.set_icon(pygame.image.load('images/favicon.png'))


screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
clock = pygame.time.Clock()

loading_text = graphics.Text('', WIDTH/2, HEIGHT/2)

# THIS WILL LET US GIVE THE USER LOADING MESSAGES
def change_loading_text(text, color=WHITE):
    screen.fill(BLACK)
    loading_text.reload(text=text, color=color)
    loading_text.draw(screen)
    pygame.display.flip()
def throw_error_to_user(text, close=True):
    global clock, client
    change_loading_text(text+'\nYou may exit the application.', color=RED)
    try:
        if close: client.session._send('CLOSE')
    except OSError:
        pass
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('User quit.')
                exit()
        pygame.display.update()
        clock.tick(FPS)


change_loading_text('Starting client...')
print('Initializing client...')
client = network.UDPClient('73.166.38.74', 37001, override_uuid=uuid, frag=True)
client.init()

change_loading_text('Waiting for server...')
print('Waiting for permission to continue...')
client.session.send('OPEN')

# FIRST PING PONG

try:
    sleep(0.2)
    if not client.running:  # it crashed when it tried to send OPEN
        raise Empty
    response = client.META_QUEUE.get(timeout=5)
except Empty:
    response = None

if response == 'CONTINUE':
    print('Permission received.')
    pass
elif response == 'DUPLICATE':
    print('The server already has this ID registered AND marked as open. Fuck.')
    throw_error_to_user('This ID is already in use. Please ask your manager for help.', close=False)
else:
    print('Couldn\'t connect to server.')
    throw_error_to_user('Failed to connect to the server. It may be closed, or your internet may be down.\nPlease ask your manager for help if you cannot resolve the issue.')


# ACTUAL INIT TIME

print('Opening webcam...')
change_loading_text('Opening webcam...')
try:
    cam = webcam.Webcam(COLOR_BGR2RGB, mirror=True, swap_axes=True, compress_quality=75) #device=r'C:\Users\Key Cohen Office\Desktop\My Movie.mp4'
except (ValueError, IOError) as e:
    throw_error_to_user(str(e))
except Exception as e:
    throw_error_to_user('Wow, your webcam absolutely imploded. Show your manager the error message below.\n\n'+type(e).__qualname__+': '+str(e)+'\n')
cam  # pycharm is dumb

text = graphics.Text('Welcome!', WIDTH / 2, HEIGHT * 7 / 8, fontsize=56)
cam_viewer = graphics.WebcamViewer(WIDTH / 2, HEIGHT * 4 / 9, 640, 480, dim_enforcer=graphics.scale.NONE if FIXED_VIEWER else graphics.scale.WFLEX)

print('Opening microphone...')
change_loading_text('Opening microphone...')
try:
    aud = audio.AudioInterface(output=False)
    aud.activate()
except:
    throw_error_to_user('Failed to open your microphone. Maybe it\'s not plugged in?')
aud  # pycharm is dumb

# ==========
#  MAINLOOP
# ==========
ENFORCED_OUTPUT_RESOLUTION = cam.width, cam.height
CROP_X1_X2 = 0, 0

RUNNING = True

print('Client starting at', str(cam_viewer.w)+'x'+str(cam_viewer.h))
try:
    while client.running and RUNNING:
        for chunk in aud.pending():
            client.session.send('AUDIO', chunk)

        #for chunk in iterq(client.AUDIO_QUEUE):
        #    aud.write(*chunk)

        for data in iterq(client.META_QUEUE):
            if data == 'DIE':
                print('Server forced a quit.')
                RUNNING = False
                client.close()
                break

            elif data == 'MUTE_AUDIO':
                aud.mute()
            elif data == 'UNMUTE_AUDIO':
                aud.unmute()
            elif data == 'MUTE_VIDEO':
                cam.mute()
            elif data == 'UNMUTE_VIDEO':
                cam.unmute()

            elif data[0] == 'SET_RESOLUTION':  # 'x y'
                w, h = map(int, data[1].decode().split())
                if w != 0 and h != 0:
                    ENFORCED_OUTPUT_RESOLUTION = w, h
                else:
                    print('Ignored 0x0 resolution set request.')
                #print('Set resolution to', w, h)
            elif data[0] == 'W_FLEX_RESOLUTION': # 'x y'
                w, h = map(int, data[1].decode().split())
                if w != 0 and h != 0:
                    fw = ENFORCED_OUTPUT_RESOLUTION[0]
                    fh = ENFORCED_OUTPUT_RESOLUTION[1]
                    ENFORCED_OUTPUT_RESOLUTION = round(fw * h / fh), h
                    print('H-Flexed output to', 'x'.join(map(str, ENFORCED_OUTPUT_RESOLUTION)))
                else:
                    print('Ignored 0x0 wflex request.')
            elif data[0] == 'H_FLEX_RESOLUTION':
                w, h = map(int, data[1].decode().split())
                if w != 0 and h != 0:
                    fw = ENFORCED_OUTPUT_RESOLUTION[0]
                    fh = ENFORCED_OUTPUT_RESOLUTION[1]
                    ENFORCED_OUTPUT_RESOLUTION = w, round(fh * w / fw)
                    print('W-Flexed output to', 'x'.join(map(str, ENFORCED_OUTPUT_RESOLUTION)))
                else:
                    print('Ignored 0x0 hflex request.')
            elif data[0] == 'CROP_RESOLUTION':
                w, h = map(int, data[1].decode().split())
                if w != 0 and h != 0:
                    fw = ENFORCED_OUTPUT_RESOLUTION[0]
                    fh = ENFORCED_OUTPUT_RESOLUTION[1]
                    nw = round(fw * h / fh)
                    ENFORCED_OUTPUT_RESOLUTION = nw, h

                    diff = nw - w  # distance to box bounds
                    if diff > 0:  # if this is false, the frame is actually smaller than the box, and it's not like we can expand it
                        CROP_X1_X2 = diff // 2, nw - diff // 2
                    else:
                        CROP_X1_X2 = 0,0

                    print('Cropped output to', 'x'.join(map(str, ENFORCED_OUTPUT_RESOLUTION)))
                else:
                    print('Ignored 0x0 crop request.')

            elif data[0] == 'UPDATE_TEXT':  # hello world
                text.reload(text=data[1].decode())
            elif data[0] == 'UPDATE_TEXT_COLOR':  # 0,0,0
                text.reload(color=tuple(map(int, data[1].decode().split(','))))

        if not cam.muted:
            frame = cam.read(with_jpeg_encode=False)
            enc_frame = webcam.scale_to(frame, *ENFORCED_OUTPUT_RESOLUTION)
            if any(CROP_X1_X2):
                # print(CROP_X1_X2[0], 0, CROP_X1_X2[1], ENFORCED_OUTPUT_RESOLUTION[1])
                enc_frame = webcam.crop(enc_frame, CROP_X1_X2[0], 0, CROP_X1_X2[1], ENFORCED_OUTPUT_RESOLUTION[1])
            client.session.send('VIDEO', pickle.dumps(webcam.jpeg_encode(enc_frame, cam.compress_quality)))
            cam_viewer.take_frame(frame if FIXED_VIEWER else enc_frame)

        screen.fill(BLACK)

        cam_viewer.draw(screen)
        text.draw(screen)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('User quit.')
                client.session._send('CLOSE')
                RUNNING = False
                client.close()
                break
            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = pygame.display.get_window_size()
                cam_viewer.set_pos(WIDTH/2, HEIGHT * 4 / 9)
                text.x = WIDTH/2
                text.y = HEIGHT * 7 / 8
            #elif event.type == VIDEOEXPOSE:  # handles window minimising/maximising
            #    screen.fill((0, 0, 0))
            #    screen.blit(pygame.transform.scale(pic, screen.get_size()), (0, 0))
            #    pygame.display.update()

        clock.tick(FPS)

except Exception as e:
    traceback.print_exc()
    print(type(e).__qualname__, str(e))
    client.session._send('CLOSE')
    RUNNING = False
    client.close()
    raise e

finally:
    client.close()
    pygame.quit()
    print('Closed safely.')
    exit()

exit(0)
