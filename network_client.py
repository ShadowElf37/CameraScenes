from socket import *
import threading
from network_common import *
import json
from collections import defaultdict
import autolog

class UDPClient:
    BUFFER = 8192

    def __init__(self, host, port=37001, override_uuid=None, frag=False):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()
        self.META_QUEUE = Queue()

        self.recv_queue = Queue()
        self.recv_thread = threading.Thread(target=self._recv_all, daemon=True)

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

        self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.session = Session(self, self.host, self.port, tcp_socket=None, fragment=frag)
        if override_uuid:
            self.session.uuid = override_uuid
        self.session.start_threads()

        self.running = False
        self.thread = threading.Thread(target=self._handle_data, daemon=True)

        self.frag = frag
        self.fragments = defaultdict(list)
        self.incomplete_packets = []

    def init_tcp(self):
        """This must be called AFTER sending an OPEN request over UDP"""
        self.session.tcp_socket = self.tcp_socket
        self.tcp_socket.connect((self.host, self.port + 1))
        self.session.start_threads(tcp_only=True)

    def init(self):
        self.running = True
        self.thread.start()
        self.recv_thread.start()
    def close(self):
        self.running = False
        self.session.close()
        try:
            self.socket.close()
        except OSError:
            pass

    def _recv_all(self):
        while self.running:
            try:
                self.recv_queue.put(self.socket.recvfrom(56000))
            except Exception as e:
                print('UDP socket crashed:', str(e))
                continue

    def _handle_data(self):
        try:
            # 0 - uuid
            # 1 - pid
            # 2 - reason
            # 3 - frag
            # 4 - data
            while self.running:
                decomp = Session.decompile(self.recv_queue.get()[0])

                pid = decomp[1]
                frag_opts = decomp[3]

                incomplete = False
                if self.frag and frag_opts[0] != 0:
                    self.fragments[pid].append((frag_opts[0], decomp[4]))

                    if (found_incomplete:=(pid in self.incomplete_packets)) or frag_opts[1] == 1:
                        fragments = self.fragments[pid]

                        # discovers newly incomplete packets, and proceeds if a previously incomplete packet is now complete
                        for i, frag in enumerate(sorted(fragments, key=lambda f: f[0])):
                            if frag[0] != i+1:
                                self.incomplete_packets.append(pid)
                                incomplete = True
                                break

                        if incomplete: continue

                        print('Packet %s-%s was reassembled successfully.' % (decomp[2].lower(), pid),
                              'It arrived out of order.' if pid in self.incomplete_packets else '')
                        data = *decomp[:3], (0,0), b''.join(frag[1] for frag in sorted(fragments, key=lambda f: f[0]))
                        del self.fragments[pid]
                        if found_incomplete: self.incomplete_packets.remove(pid)
                    else:
                        continue
                else:
                    data = decomp

                reason = data[2]

                if not self.session.verify_pid(pid, reason) and reason not in ('DIE', 'RESET'):
                    print('Out of order packet rejected', data[:4])
                    continue
                elif reason == 'RESET':
                    self.session.packet_id_recv.clear()
                self.session.packet_id_recv[reason] = pid

                print(*data[:4])

                if reason == 'INFO': # DATATYPE
                    self.INFO_QUEUE.put((data[0], data[4]))
                elif reason == 'AUDIO':
                    self.AUDIO_QUEUE.put((data[0], data[4]))
                elif reason == 'VIDEO':
                    self.VIDEO_QUEUE.put((data[0], data[4]))
                elif reason == 'KEEPALIVE':
                    pass
                elif reason == 'PRINT':
                    print('PRINT REQUEST:', data[4])
                elif reason in ('CONTINUE', 'DIE', 'DUPLICATE', 'MUTE_AUDIO', 'MUTE_VIDEO', 'UNMUTE_AUDIO', 'UNMUTE_VIDEO'):
                    self.META_QUEUE.put(data[2]) # these go straight up to main
                elif reason in ('SET_RESOLUTION', 'CROP_RESOLUTION', 'H_FLEX_RESOLUTION', 'W_FLEX_RESOLUTION', 'UPDATE_TEXT', 'UPDATE_TEXT_COLOR', 'QUALITY'):
                    self.META_QUEUE.put((data[2], data[4]))
                elif reason == 'PING':
                    self.session.send_tcp('PONG')
                else:
                    ...  # can do stuff if necessary

        except (ConnectionAbortedError, ConnectionError, OSError):
            if self.running:
                print('Connection imploded!')
                self.close()
