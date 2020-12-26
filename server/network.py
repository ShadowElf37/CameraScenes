from socket import *
import threading
from network_common import *

class UDPManager:
    def __init__(self, port=37001):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()
        self.META_QUEUE = Queue()

        self.port = port
        self.sessions: {str: UDPSession} = {}

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

    def session_by_addr(self, addr) -> UDPSession:
        for s in self.sessions.values():
            if s.ip == addr[0] and s.port == addr[1]:
                return s
        return None

    def _handle_data(self):
        while self.running:
            data, addr = self.socket.recvfrom(100000)
            data = UDPSession.decompile(data)
            uuid = data[0]
            reason = data[2]

            print(*data[:3], addr[0]+':'+str(addr[1]))

            if self.sessions.get(uuid) is None:
                self.sessions[uuid] = session = UDPSession(self, *addr, uuid=uuid)

                # If they're sending us something but we have no records, i.e. zombie that we have to get rid of
                if reason != 'OPEN':
                    session._send('DIE')  # can't send() because no send thread, must _send
                    del self.sessions[uuid]
                    continue

                session.start_send_thread()
            else:
                session: UDPSession = self.sessions[uuid]
                # print('SESSION:', session.uuid, session.packet_id_recv, session.packet_id_send)
                # print(data[0] == session.uuid, data[1] > session.packet_id_recv, data[1] == -1)
                if not session.verify_pid(data[1]) and data[2] != 'OPEN':
                    print('Out of order packet rejected')
                    continue

            session.packet_id_recv = data[1]

            # DATATYPE
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
            elif data[2] == 'OPEN' or data[2] == 'CLOSE':
                self.META_QUEUE.put(data)
            else:
                ... # can do stuff if necessary
                # possible keep-alive, auth, etc.

