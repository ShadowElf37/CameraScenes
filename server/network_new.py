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


class UDPManager:
    def __init__(self, port=37001):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()

        self.port = port
        self.sessions = {}

        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))

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
            data, addr = self.socket.recvfrom(1024)
            if self.sessions.get(addr) is None:
                self.sessions[addr] = UDPSession(self, *addr)
            session = self.sessions[addr]

            data = UDPSession.decompile(data)
            if not session.verify_decompiled(data):
                continue
            session.packet_id = data[1]

            if data[2] == 'INFO': # DATATYPE
                self.INFO_QUEUE.put((session.uuid, data))
            elif data[2] == 'AUDIO':
                self.AUDIO_QUEUE.put((session.uuid, data))
            elif data[2] == 'VIDEO':
                self.VIDEO_QUEUE.put((session.uuid, data))
            else:
                ... # can do stuff if necessary
                # possible keep-alive, auth, etc.

