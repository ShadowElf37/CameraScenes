from uuid import getnode
from queue import Queue
from threading import Thread

class UDPSession:
    def __init__(self, manager, ip, port, uuid=None):
        self.manager = manager  # UDPClient or UDPManager will both work
        self.ip = ip
        self.port = port
        self.uuid = uuid or str(getnode())

        # these are different because we don't care about client and server syncing perfectly when it's just streaming data
        # all we want to ensure is that we and they are not *receiving* packets out of order, and are discarding such packets
        self.packet_id_recv = -1  # packet id of packets we receive - other end's send id
        self.packet_id_send = -1  # packet id of packets we send - other end's receive id

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

        return uuid, int(pid), type_, data

    def compile(self, datatype: str, data: bytes, override_uuid=None):
        # datatype should be INFO, AUDIO, VIDEO, other
        # META is for manager to handle
        return '\n'.join((override_uuid or self.uuid, str(self.packet_id_send), datatype)).encode() + b'\n' + data

    def verify_pid(self, pid):
        return pid > self.packet_id_recv

    def _send(self, datatype: str, data: bytes=b'', send_as=None):
        self.packet_id_send += 1
        self.manager.socket.sendto(self.compile(datatype, data, override_uuid=send_as), self.addr)

    # BUFFERED STUFF
    def send(self, datatype: str, data: bytes=b'', send_as=None):
        self.send_buffer.put((datatype, data, send_as))

    def start_send_thread(self):
        self.sending = True
        self.send_thread.start()
    def close(self):
        self.sending = False

    def _sendloop(self):
        while self.sending:
            self._send(*self.send_buffer.get())


def iterq(queue: Queue):
    """Creates an iterator over a Queue object"""
    while not queue.empty():
        yield queue.get()
