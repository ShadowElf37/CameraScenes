import socket
from threading import Thread
from queue import Queue, Empty

class Nothing:
    def __repr__(self):
        return '<Nothingness>'

class Pipe:
    NOTHING = Nothing()

    def __init__(self, at=38050):
        self.port = at
        self.socket = socket.socket()
        try:
            self.socket.bind(('localhost', at))
            self.socket.listen(1)
            self.connection = None
            self.server = True
        except OSError:
            self.server = False

        self.is_open = False
        self.reader_thread = Thread(target=self._read_all, daemon=True)
        self._messages = Queue()

    def __iter__(self):
        while not self._messages.empty():
            yield self._messages.get()

    def write(self, msg: str):
        self.connection.send(msg.encode())
    def read(self):
        """Gets a message, or nothing"""
        if self._messages.empty():
            return self.NOTHING
        return self._messages.get()
    def wait_read(self):
        """Waits for a message before returning"""
        return self._messages.get()

    def close(self):
        self.is_open = False
        self.socket.close()
    def open(self):
        self.is_open = True
        if self.server:
            self.connection, _ = self.socket.accept()
        else:
            self.socket.connect(('localhost', self.port))
            self.connection = self.socket
        self.reader_thread.start()

    def _read_all(self):
        try:
            while self.is_open:
                self._messages.put(self.connection.recv(1024))
        except ConnectionError:
            self.is_open = False
            print('Pipe broke.')


if __name__ == "__main__":
    p = Pipe(at=38051)
    p.open()
    while True:
        p.write(input('>> '))
