from socket import *
import threading
from network_common import *
import json

class UDPClient:
    def __init__(self, host, port=37001, override_uuid=None):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()
        self.META_QUEUE = Queue()

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
    def close(self):
        self.running = False
        self.socket.close()


    def _handle_data(self):
        try:
            while self.running:
                data = UDPSession.decompile(self.socket.recvfrom(56000)[0])

                if not self.session.verify_pid(data[1]) and data[2] not in ('DIE', 'RESET'):
                    print('Out of order packet rejected', data[:3])
                    continue
                self.session.packet_id_recv = data[1]

                print(*data[:3])

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
                elif data[2] == 'CONTINUE':
                    self.META_QUEUE.put('CONTINUE')
                elif data[2] == 'DIE':
                    self.META_QUEUE.put('DIE')
                else:
                    ...  # can do stuff if necessary

        except (ConnectionAbortedError, ConnectionError, OSError):
            self.close()
        finally:
            print('FATAL CONNECTION ERROR')
