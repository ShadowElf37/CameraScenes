from uuid import uuid4
from socket import *
from queue import Queue
import threading
from time import sleep

class UDPSession:
    def __init__(self, sock, ip, port):
        self.socket: socket = sock
        self.ip = ip
        self.port = port
        self.uuid = str(uuid4())
        self.packet_id = 0

    @property
    def addr(self):
        return self.ip, self.port

    @classmethod
    def decompile(self, data: bytes):
        return data.decode().split('\n')
    def compile(self, datatype, data):
        # datatype should be INFO, AUDIO, VIDEO, other
        # META is for manager to handle
        return '\n'.join((self.uuid, self.packet_id, datatype, data)).encode()

    def verify_decompiled(self, decomp_tuple):
        return decomp_tuple[0] == self.uuid and decomp_tuple[1] > self.packet_id

    def send(self, datatype, data):
        self.socket.sendto(self.compile(datatype, data), self.addr)
        self.packet_id += 1

class UDPClient:
    def __init__(self, host, port=37001):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()

        self.host = host
        self.port = port

        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.session = UDPSession(self.socket, self.host, self.port)

        self.running = False
        self.thread = threading.Thread(target=self._handle_data, daemon=True)

    def init(self):
        self.running = True
        self.thread.start()
    def close(self):
        self.running = False
        self.socket.close()

    def _handle_data(self):
        while self.running:
            data = UDPSession.decompile(self.socket.recv(1024))
            if not self.session.verify_decompiled(data):
                continue
            self.session.packet_id = data[1]

            if data[2] == 'INFO': # DATATYPE
                self.INFO_QUEUE.put(data)
            elif data[2] == 'AUDIO':
                self.AUDIO_QUEUE.put(data)
            elif data[2] == 'VIDEO':
                self.VIDEO_QUEUE.put(data)
            elif data[2] == 'KEEPALIVE':
                pass
            elif data[2] == 'PRINT':
                print('PRINT REQUEST:', data[3])
            else:
                ...  # can do stuff if necessary
