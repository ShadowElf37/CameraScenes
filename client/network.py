from socket import *
import threading
from network_common import *
import json

class UDPClient:
    def __init__(self, host, port=37001, override_uuid=None):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()

        self.audio_client_table: {tuple: UDPSession} = {}  # addr: UDPSession
        self.audio_broadcast_buffer = Queue()
        self.audio_client_thread = Thread(target=self._broadcast_audio, daemon=True)

        self.host = host
        self.port = port

        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # I NEED A REALLY RANDOM PORT SO I CAN RECEIVE - ROUTER HAS NAT, WE'RE RECEIVING FROM WAN, NUM DOESNT MATTER
        p = 38000
        while True:
            try:
                self.socket.bind(('', p))
            except OSError:
                continue
            else:
                break

        self.session = UDPSession(self, self.host, self.port)
        if override_uuid:
            self.session.uuid = override_uuid
        self.session.start_send_thread()

        self.running = False
        self.thread = threading.Thread(target=self._handle_data, daemon=True)

    def init(self):
        self.running = True
        self.thread.start()
        self.audio_client_thread.start()
    def close(self):
        self.running = False
        self.socket.close()

    def _broadcast_audio(self):
        while self.running:
            audio = self.audio_broadcast_buffer.get()
            for client in self.audio_client_table.values():
                print('SENDING TO CLIENT', client.ip, client.port)
                client.send('AUDIO', audio, send_as=self.session.uuid)


    def _handle_data(self):
        while self.running:
            data = UDPSession.decompile(self.socket.recvfrom(56000)[0])

            session = self.audio_client_table.get(data[0], self.session)
            if not session.verify_pid(data[1]):
                print('Out of order packet rejected')
                continue
            session.packet_id_recv = data[1]

            if data[2] == 'INFO': # DATATYPE
                self.INFO_QUEUE.put((data[0], data[3]))
            elif data[2] == 'AUDIO':
                self.AUDIO_QUEUE.put((data[0], data[3]))
            elif data[2] == 'VIDEO':
                self.VIDEO_QUEUE.put((data[0], data[3]))
            elif data[2] == 'KEEPALIVE':
                pass
            elif data[2] == 'PRINT':
                print('PRINT REQUEST:', data[3])
            elif data[2] == 'ADD_CLIENT_TABLE':  # HOST PORT UUID
                print(data[3], json.loads(data[3].decode()))
                for host, port, uuid in json.loads(data[3].decode()):
                    self.audio_client_table[uuid] = session = UDPSession(self, host, port, uuid=uuid)
                    session.start_send_thread()
            elif data[2] == 'REMOVE_CLIENT_TABLE': # [UUID]
                for uuid in json.loads(data[3].decode()):
                    self.audio_client_table[uuid].close()
                    del self.audio_client_table[uuid]
            else:
                ...  # can do stuff if necessary
