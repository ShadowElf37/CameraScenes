# SERVER REQUIREMENTS
# receive video
# receive audio
# pump out audio stream to everyone
# send cues
# channeller should get streaming channels; perhaps they are off when no data is given, or perhaps they are off when I command them to be off

from uuid import uuid4 as uuid
from socket import *
import threading
import queue

class AuthenticationServer:
    def __init__(self, port=37001):
        self.auth_table = {}  # (ip,port):uuid

        self.socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))
        self.socket.listen(1)

        self.running = False
        self.main_thread = threading.Thread(target=self._start, daemon=True)

    def close(self):
        self.running = False
        self.socket.close()

    def verify(self, addr, uid=None):
        if uid is None:
            return bool(self.auth_table.get(addr[0]))
        return self.auth_table.get(addr[0]) == uid

    def start(self):
        self.running = True
        self.main_thread.start()
        print('Authentication server active.')

    def _start(self):
        while self.running:
            c, a = self.socket.accept()
            req = c.recv(1024)
            u = str(uuid())
            if req == b'AUTHENTICATE':
                c.send(b'GRANTED ' + u.encode() + b' 0')
                print('AUTHENTICATION GRANTED TO', a)

            self.auth_table[a[0]] = u

            c.close()


class UDPServer:
    def __init__(self, port=37002):
        self.auth = AuthenticationServer()
        self.auth.start()

        self.client_packet_ids = {}
        self.buffer = queue.SimpleQueue()

        self.socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))

        self.running = False
        self.listening_thread = threading.Thread(target=self._listen, daemon=True)
        self.processing_thread = threading.Thread(target=self._process, daemon=True)

    def get_port(self, ip):
        for addr in self.client_packet_ids.keys():
            if addr[0] == ip:
                return addr[1]

    def join(self):
        self.processing_thread.join()

    def start(self):
        self.running = True
        self.listening_thread.start()
        self.processing_thread.start()
        print('UDP server listening.')

    def _process(self):
        while True:
            addr, data = self.buffer.get()
            datatype, data = data
            print('PROCESSED:', addr, datatype, data)
            self.socket.sendto(b'pogchamp', addr)

    def _listen(self):
        while self.running:
            msg, addr = self.socket.recvfrom(1024)
            uid, pid, datatype, data = msg.decode().split('\n')
            pid = int(pid)
            # --MESSAGE STRUCTURE--
            # UUID\n
            # PACKET ID\n
            # TYPE\n
            # DATA
            if self.auth.verify(addr, uid):
                old_pid = self.client_packet_ids.get(addr)
                if old_pid is not None and pid <= old_pid:
                    continue
                self.client_packet_ids[addr] = pid + 1
                print('VERIFIED DATA:', datatype, data)
                self.buffer.put((addr, (datatype, data)))
                return
            print('DATA REJECTED FROM', addr)

    def read(self):
        self.buffer.get(True)

    def send(self, ip, *data):
        self.socket.sendto(b' '.join(data), (ip, self.get_port(ip)))

    def close(self):
        self.running = False
        self.socket.close()
        self.auth.close()

if __name__ == "__main__":
    server = UDPServer(37002)
    server.start()
    server.join()