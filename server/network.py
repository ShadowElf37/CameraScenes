from socket import *
import threading
from network_common import *
from collections import defaultdict
from time import time, sleep

class UDPManager:
    SESSION_TIMEOUT = 15

    def __init__(self, port=37001, frag=False):
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

        self.frag = frag
        self.fragments = defaultdict(lambda: defaultdict(list))
        self.incomplete_packets = defaultdict(list)

        self.times: {str: float} = defaultdict(time)  # uuid: time() of last message
        self.mutes = []  # uuids that are muted, we send them pings so they can pong and we record their time
        self.pingpong_thread = threading.Thread(target=self._pingpong, daemon=True)

    def init(self):
        self.running = True
        self.thread.start()
        self.pingpong_thread.start()
    def close(self):
        self.running = False
        self.socket.close()

    def session_by_addr(self, addr) -> UDPSession:
        for s in self.sessions.values():
            if s.addr == addr:
                return s

    def muted(self, uuid):
        self.mutes.append(uuid)
    def unmuted(self, uuid):
        self.mutes.remove(uuid)

    def _pingpong(self):
        while self.running:
            t = time()
            # send muted some pings
            for uuid in self.mutes.copy():  # need copy for threadsafe
                if 3.2 > t - self.times[uuid] > 3 or 8.2 > t - self.times[uuid] > 8 or 12.2 > t - self.times[uuid] > 12:
                    self.sessions[uuid].send('PING')

            # kill expired sessions
            for uuid in self.sessions.keys():
                if 15.1 >= t - self.times[uuid] >= 15:
                    self.META_QUEUE.put((uuid, -7, 'CLOSE', (0,0), b''))

            sleep(0.1)

    def _handle_data(self):
        # 0 - uuid
        # 1 - pid
        # 2 - reason
        # 3 - frag
        # 4 - data
        while self.running:
            raw, addr = self.socket.recvfrom(96000)
            decomp = UDPSession.decompile(raw)
            uuid = decomp[0]
            pid = decomp[1]
            frag_opts = decomp[3]

            incomplete = False
            if self.frag and frag_opts[0] != 0:
                self.fragments[uuid][pid].append((frag_opts[0], decomp[4]))

                if (found_incomplete := (pid in self.incomplete_packets)) or frag_opts[1] == 1:
                    fragments = self.fragments[uuid][pid]

                    # discovers newly incomplete packets, and proceeds if a previously incomplete packet is now complete
                    for i, frag in enumerate(sorted(fragments, key=lambda f: f[0])):
                        if frag[0] != i + 1:
                            self.incomplete_packets[uuid].append(pid)
                            incomplete = True
                            break

                    if incomplete:
                        continue

                    print('Packet %s was reassembled successfully.' % pid, 'It arrived out of order.' if found_incomplete else '')
                    data = *decomp[:3], (0, 0), b''.join(frag[1] for frag in sorted(fragments, key=lambda f: f[0]))
                    del self.fragments[uuid][pid]
                    if found_incomplete: self.incomplete_packets[uuid].remove(pid)
                else:
                    continue
            else:
                data = decomp

            uuid = data[0]
            reason = data[2]

            print(*data[:3], addr[0]+':'+str(addr[1]))

            if self.sessions.get(uuid) is None:
                self.sessions[uuid] = session = UDPSession(self, *addr, uuid=uuid, fragment=self.frag)

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
            self.times[uuid] = time()

            # DATATYPE
            if data[2] == 'INFO':
                self.INFO_QUEUE.put((session.uuid, data[4]))
            elif data[2] == 'AUDIO':
                self.AUDIO_QUEUE.put((session.uuid, data[4]))
            elif data[2] == 'VIDEO':
                self.VIDEO_QUEUE.put((session.uuid, data[4]))
            elif data[2] == 'KEEPALIVE':
                pass
            elif data[2] == 'PRINT':
                print('PRINT REQUEST:', data[4])
            elif data[2] in ('OPEN', 'CLOSE'):
                self.META_QUEUE.put(data)
            elif data[2] == 'PONG':
                ...
            else:
                ... # can do stuff if necessary
                # possible keep-alive, auth, etc.

