from uuid import uuid4
from socket import *
from queue import Queue
import threading
from time import sleep
from network_common import *

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

    def session_by_uuid(self, uuid) -> UDPSession:
        for s in self.sessions.values():
            if s.uuid == uuid:
                return s
        return None

    def _handle_data(self):
        while self.running:
            data, addr = self.socket.recvfrom(100000)
            data = UDPSession.decompile(data)

            if self.sessions.get(addr) is None:
                self.sessions[addr] = session = UDPSession(self, *addr)
                session.uuid = data[0]
                session.start_send_thread()
            else:
                session: UDPSession = self.sessions[addr]
                # print('SESSION:', session.uuid, session.packet_id)
                if not session.verify_decompiled(data):
                    print('PACKET REJECTED')
                    continue

            session.packet_id = data[1]

            # DATATYPE
            #print(data)
            if data[2] == 'INFO':
                self.INFO_QUEUE.put((session.uuid, data[3]))
            elif data[2] == 'AUDIO':
                self.AUDIO_QUEUE.put((session.uuid, data[3]))
            elif data[2] == 'VIDEO':
                self.VIDEO_QUEUE.put((session.uuid, data[3]))
            elif data[2] == 'KEEPALIVE':
                pass
            elif data[2] == 'PRINT':
                print('PRINT REQUEST:', data[3])
            else:
                ... # can do stuff if necessary
                # possible keep-alive, auth, etc.

