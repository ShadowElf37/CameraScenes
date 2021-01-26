from socket import *
import threading
from network_common import *
from collections import defaultdict
from time import time, sleep

class UDPManager:
    BUFFER = 9000
    SESSION_TIMEOUT = 15
    DEBUG_ALL = False
    REPORT_INTERVAL = 15

    def __init__(self, port=37001, frag=False):
        self.AUDIO_QUEUE = Queue()
        self.VIDEO_QUEUE = Queue()
        self.INFO_QUEUE = Queue()
        self.META_QUEUE = Queue()

        self.recv_queue = Queue()
        self.recv_thread = threading.Thread(target=self._recv_all, daemon=True)

        self.port = port
        self.sessions: {str: Session} = {}

        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))

        self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', port+1))
        self.tcp_connections: {tuple: socket} = {}
        self.tcp_keepalive_time = time()
        self.tcp_connector_thread = Thread(target=self._handle_tcp_connections, daemon=True)

        self.running = False
        self.handle_thread = threading.Thread(target=self._handle_data, daemon=True)

        self.frag = frag
        self.fragments = defaultdict(lambda: defaultdict(list))
        self.fragment_age = defaultdict(lambda: defaultdict(int))
        self.incomplete_packets = defaultdict(list)

        self.times: {str: float} = defaultdict(time)  # uuid: time() of last message
        self.mutes = []  # uuids that are muted, we send them pings so they can pong and we record their time
        self.pingpong_thread = threading.Thread(target=self._pingpong, daemon=True)

        self.reports = defaultdict(int)
        self.reporter_thread = threading.Thread(target=self._print_reports, daemon=True)

    def init(self):
        self.running = True
        self.handle_thread.start()
        self.pingpong_thread.start()
        self.reporter_thread.start()
        self.recv_thread.start()
        self.tcp_connector_thread.start()
    def close(self):
        self.running = False
        self.socket.close()

    def session_by_addr(self, addr) -> Session:
        for s in self.sessions.values():
            if s.addr == addr:
                return s

    def muted(self, uuid):
        if uuid not in self.mutes:
            self.mutes.append(uuid)
    def unmuted(self, uuid):
        if uuid in self.mutes:
            self.mutes.remove(uuid)

    def _print_reports(self):
        sleep(1)
        while self.running:
            print('=======REPORT=======')
            print('Reassembled %s packets.' % self.reports['frag'])
            del self.reports['frag']
            print('%s out of order packets were dropped.' % self.reports['out of order'])
            del self.reports['out of order']
            print('%s fragmented packets were terminated.' % self.reports['frag term'])
            del self.reports['frag term']
            open_sessions = [uuid for uuid, s in self.sessions.items() if s.is_open]
            print('Clients:', ', '.join(open_sessions), '(%s/%s)' % (len(open_sessions), len(self.sessions)))
            if self.reports:
                print('Packet report:\n\t' + '\n\t'.join(f'{key} - {i}' for key,i in self.reports.items()))
            else:
                print('No other packets received.')
            self.reports.clear()
            print('============')
            sleep(self.REPORT_INTERVAL)


    def _pingpong(self):
        while self.running:
            t = time()
            # send muted some pings
            #for uuid in self.mutes.copy():  # need copy for threadsafe
            #    if t - self.times[uuid] > 3:
            #        self.sessions[uuid].send_tcp('PING')

            #kill expired sessions
            #for uuid in self.sessions.keys():
                #if 15.1 >= t - self.times[uuid] >= 15:
                    #self.META_QUEUE.put((uuid, -7, 'CLOSE', (0,0), b''))

            if t - self.tcp_keepalive_time > 2:
                self.tcp_keepalive_time = t
                for session in self.sessions.values():
                    if session.is_open:
                        try:
                            session._send_tcp('KEEPALIVE')
                        except:
                            self.META_QUEUE.put((session.uuid, -8, 'CLOSE', (0, 0), b''))

                    #print('KEEPALIVE', session.uuid)

            sleep(0.1)

    def _recv_all(self):
        while self.running:
            try:
                self.recv_queue.put(self.socket.recvfrom(self.BUFFER))
            except Exception as e:
                print('UDP socket crashed:', str(e))
                continue

    def _handle_tcp_connections(self):
        self.tcp_socket.listen(32)
        while self.running:
            c, a = self.tcp_socket.accept()
            print('CONNECTION', a, c)
            self.tcp_connections[a] = c
            def _handle_open_msg():
                print('HANDLING')
                data = c.recv(self.BUFFER)
                open_msg = Session.decompile(data[2:2+struct.unpack('!H', data[:2])[0]])
                print('GOT', open_msg)
                uuid = open_msg[0]
                reason = open_msg[2]
                print(uuid, reason)
                if reason == 'OPEN':
                    self.sessions[uuid] = session = Session(self, *a, tcp_socket=c, uuid=uuid, fragment=self.frag)
                    session.start_threads()
                    self.META_QUEUE.put(open_msg)
                else:
                    c.send(b'DIE')  # can't send() because no send thread, must _send
            Thread(target=_handle_open_msg, daemon=True).start()

    def _handle_data(self):
        # 0 - uuid
        # 1 - pid
        # 2 - reason
        # 3 - frag
        # 4 - data
        try:
            while self.running:
                raw, addr = self.recv_queue.get()

                decomp = Session.decompile(raw)
                uuid = decomp[0]
                pid = decomp[1]
                frag_opts = decomp[3]

                incomplete = False
                if self.frag and frag_opts[0] != 0:
                    self.fragments[uuid][pid].append((frag_opts[0], decomp[4]))
                    self.fragment_age[uuid][pid] = time()

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

                        self.reports['frag'] += 1
                        if self.DEBUG_ALL: print('Packet %s-%s was reassembled successfully.' % (decomp[2].lower(), pid), 'The fragments arrived out of order.' if found_incomplete else '')
                        data = *decomp[:3], (0, 0), b''.join(frag[1] for frag in sorted(fragments, key=lambda f: f[0]))
                        del self.fragments[uuid][pid]
                        if found_incomplete: self.incomplete_packets[uuid].remove(pid)
                    else:
                        continue
                else:
                    data = decomp

                uuid = data[0]
                pid = data[1]
                reason = data[2]

                for pid_frag, age in self.fragment_age[uuid].copy().items():
                    if time() - age > 20:
                        self.reports['frag term'] += 1
                        del self.fragments[uuid][pid_frag], self.fragment_age[uuid][pid_frag]

                if self.DEBUG_ALL: print(*data[:3], addr[0]+':'+str(addr[1]))
                self.reports[reason] += 1

                if self.sessions.get(uuid) is None:
                    # If they're sending us something but we have no records, i.e. zombie that we have to get rid of
                    Session(self, *addr, tcp_socket=None, uuid=uuid, fragment=self.frag)._send_tcp('DIE') # can't send() because no send thread, must _send
                    continue


                # they already exist, no init needed
                session: Session = self.sessions[uuid]
                # print('SESSION:', session.uuid, session.packet_id_recv, session.packet_id_send)
                # print(data[0] == session.uuid, data[1] > session.packet_id_recv, data[1] == -1)
                if not session.verify_pid(pid, reason) and reason != 'OPEN':
                    self.reports['out of order'] += 1
                    if self.DEBUG_ALL: print('Out of order packet rejected!')
                    continue

                elif reason == 'OPEN':
                    session.packet_id_recv.clear()
                        #if session.tcp_socket is None:
                        #    print('Resetting session TCP...')
                        #    session.tcp_socket = self.tcp_socket.accept()[0]
                        #    session.reset_tcp()
                        #    session.start_threads(tcp_only=True)
                        #    print('Reset!')
                        # we'll need to do more up top

                session.packet_id_recv[reason] = pid
                self.times[uuid] = time()

                # DATATYPE
                if data[2] == 'INFO':
                    self.INFO_QUEUE.put((session.uuid, data[4]))
                elif data[2] == 'AUDIO':
                    self.AUDIO_QUEUE.put((session.uuid, data[4]))
                elif data[2] == 'VIDEO':
                    self.VIDEO_QUEUE.put((session.uuid, data[4]))
                elif data[2] == 'HELLO':
                    print('%s says hello :)' % uuid)
                elif data[2] == 'PRINT':
                    print('PRINT REQUEST:', data[4])
                elif data[2] in ('OPEN', 'CLOSE'):
                    self.META_QUEUE.put(data)
                elif data[2] in ('KEEPALIVE', 'PONG'):
                    pass
                else:
                    print('Odd request:', data)
                    # can do stuff if necessary
                    # possible keep-alive, auth, etc.

        except OSError as e:
            print('Server thread died.', str(e))