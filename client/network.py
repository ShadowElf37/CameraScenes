# REQUIREMENTS
# send video to server
# send audio to server
# receive audio from server, at minimum - we actually don't need video, the kids can listen to the lines
# client will see their own webcam, it'll be fine
# receive cues (we can send notifications of upcoming events to display, etc)

import queue
from socket import *
from audio import *

class Authenticator:
    UUID = None
    PACKET_ID = None

    @staticmethod
    def authenticate(host, port):
        s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.connect((host, port))
        s.send(b'AUTHENTICATE')
        credentials = s.recv(1024).decode().split(' ')  # "GRANTED xxxxx 0"
        if credentials[0] == 'GRANTED':
            Authenticator.UUID = credentials[1]
            Authenticator.PACKET_ID = int(credentials[2])
            print('Authenticated!')
        s.close()

    @staticmethod
    def reset():
        Authenticator.UUID = None
        Authenticator.PACKET_ID = None


class UDPClient:
    def __init__(self, host, port):
        self.buffer = queue.SimpleQueue()
        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.addr = host, port

    def init(self):
        self.send(Authenticator.UUID.encode(), str(Authenticator.PACKET_ID).encode(), b'hello world')
        print('Receiving...')
        #print('RECEIVED', self.socket.recvfrom(1024))
        self.recv()
        print(self.read())

    def close(self):
        self.socket.close()

    def read(self):
        return self.buffer.get()

    def send(self, *data):
        self.socket.sendto(b'\n'.join(data), self.addr)

    def recv(self):
        self.buffer.put(self.socket.recvfrom(1024))

if __name__ == '__main__':
    client = UDPClient('73.166.38.74', 37002)
    Authenticator.authenticate('73.166.38.74', 37001)
    client.init()