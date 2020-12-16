from uuid import getnode
from queue import Queue
from threading import Thread

class UDPSession:
    def __init__(self, manager, ip, port):
        self.manager = manager  # UDPClient or UDPManager will both work
        self.ip = ip
        self.port = port
        self.uuid = str(getnode())
        self.packet_id_recv = -1
        self.packet_id_send = -1

        self.send_buffer = Queue()
        self.sending = False
        self.send_thread = Thread(target=self._sendloop, daemon=True)

    @property
    def addr(self):
        return self.ip, self.port

    @classmethod
    def decompile(self, data: bytes):
        # this is probably faster than split - just breaks into 4 pieces by first 3 \n
        ncount = 0
        indices = []
        index = -1
        for char in data:
            index += 1
            if char != ord(b'\n'):
                continue
            ncount += 1
            indices.append(index)
            if ncount == 3:
                break

        uuid = data[:indices[0]].decode()
        pid = data[indices[0]+1:indices[1]].decode()
        type_ = data[indices[1]+1:indices[2]].decode()
        data = data[indices[2]+1:]

        # PRINTING FROM HERE
        print(uuid, pid, type_)
        return uuid, int(pid), type_, data

    def compile(self, datatype: str, data: bytes):
        # datatype should be INFO, AUDIO, VIDEO, other
        # META is for manager to handle
        return '\n'.join((self.uuid, str(self.packet_id_send), datatype)).encode() + b'\n' + data

    def verify_pid(self, pid, accept_reset_connection=True):
        return pid > self.packet_id_recv or (pid == -1 and accept_reset_connection)

    def _send(self, datatype: str, data: bytes, affect_pid=True):
        self.manager.socket.sendto(self.compile(datatype, data), self.addr)
        if affect_pid:
            self.packet_id_send += 1


    # BUFFERED STUFF
    def send(self, datatype: str, data: bytes):
        self.send_buffer.put((datatype, data))

    def start_send_thread(self):
        self.sending = True
        self.send_thread.start()
    def close_send_thread(self):
        self.sending = False

    def _sendloop(self):
        while self.sending:
            self._send(*self.send_buffer.get())