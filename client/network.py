from socket import *
import threading
from network_common import *
import json
from collections import defaultdict

class UDPClient:
    def __init__(self, host, port=37001, override_uuid=None, frag=False):
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

        self.session = UDPSession(self, self.host, self.port, fragment=frag)
        if override_uuid:
            self.session.uuid = override_uuid
        self.session.start_send_thread()

        self.running = False
        self.thread = threading.Thread(target=self._handle_data, daemon=True)

        self.frag = frag
        self.fragments = defaultdict(list)
        self.incomplete_packets = []

    def init(self):
        self.running = True
        self.thread.start()
    def close(self):
        self.running = False
        self.session.close()
        try:
            self.socket.close()
        except OSError:
            pass

    def _handle_data(self):
        try:
            # 0 - uuid
            # 1 - pid
            # 2 - reason
            # 3 - frag
            # 4 - data
            while self.running:
                decomp = UDPSession.decompile(self.socket.recvfrom(56000)[0])
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

                        print('Packet %s was reassembled successfully.' % pid,
                              'It arrived out of order.' if pid in self.incomplete_packets else '')
                        data = *decomp[:3], (0,0), b''.join(frag[1] for frag in sorted(fragments, key=lambda f: f[0]))
                        del self.fragments[pid]
                        if found_incomplete: self.incomplete_packets.remove(pid)
                    else:
                        continue
                else:
                    data = decomp


                if not self.session.verify_pid(pid) and data[2] not in ('DIE', 'RESET'):
                    print('Out of order packet rejected', data[:4])
                    continue
                self.session.packet_id_recv = pid

                print(*data[:4])

                if data[2] == 'INFO': # DATATYPE
                    self.INFO_QUEUE.put((data[0], data[4]))
                elif data[2] == 'AUDIO':
                    self.AUDIO_QUEUE.put((data[0], data[4]))
                elif data[2] == 'VIDEO':
                    self.VIDEO_QUEUE.put((data[0], data[4]))
                elif data[2] == 'KEEPALIVE':
                    pass
                elif data[2] == 'PRINT':
                    print('PRINT REQUEST:', data[4])
                elif data[2] in ('CONTINUE', 'DIE', 'DUPLICATE'):
                    self.META_QUEUE.put(data[2])
                else:
                    ...  # can do stuff if necessary

        except (ConnectionAbortedError, ConnectionError, OSError):
            if self.running:
                print('Connection imploded!')
                self.close()
