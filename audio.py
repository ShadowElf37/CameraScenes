import pyaudio
import threading
from time import sleep
from queue import Queue

# SERVER NEEDS MANY AUDIO STREAMS, CONSIDER CHANNELLER

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 80  # actually doubled because 16 bit samples - needs to be small for encoding
AUDIO = pyaudio.PyAudio()

class Throughput:
    def __init__(self):
        self.buffer = []
        self.open = False
        self.stream = None
        self.running = False

    def pause(self):
        self.open = False
        self.stream.stop_stream()

    def unpause(self):
        self.open = True
        self.stream.start_stream()

    def close(self):
        self.running = False
        self.open = False
        self.stream.stop_stream()
        self.stream.close()

class AudioInput(Throughput):
    def __init__(self):
        super().__init__()
        self.stream = AUDIO.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)
        self.buffer = Queue(100)
        self.running = True

    def activate(self):
        self.open = True  # this is for pause/unpause, it's not a mistake
        while self.running:  # running is for dead/alive
            if self.open:
                if self.buffer.full():
                    continue
                self.buffer.put(self.stream.read(CHUNK))
                continue
            sleep(0.01)

    def read(self):
        return self.buffer.get()



class AudioOutput(Throughput):
    def __init__(self):
        super().__init__()
        self.stream = AUDIO.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, output=True,
                    frames_per_buffer=CHUNK)
        self.buffer = Queue(100)
        self.running = True

    def activate(self):
        self.open = True  # this is for pause/unpause, it's not a mistake
        while self.running:  # running is for dead/alive
            if self.open:
                self.stream.write(self.buffer.get())
                continue
            sleep(0.01)

    def write(self, data):
        self.buffer.put(data)


class AudioInterface:
    def __init__(self):
        self.inp = AudioInput()
        self.out = AudioOutput()
        self.ithread = threading.Thread(target=self.inp.activate, daemon=True)
        self.othread = threading.Thread(target=self.out.activate, daemon=True)

    def read(self):
        return self.inp.read()
    def pending(self):
        while not self.inp.buffer.empty():
            yield self.inp.read()

    def write(self, data):
        self.out.write(data)

    def activate(self):
        self.ithread.start()
        self.othread.start()

    def mute(self):
        self.inp.pause()
    def unmute(self):
        self.inp.unpause()

    def deafen(self):
        self.out.pause()
    def undeafen(self):
        self.out.unpause()

    def close(self):
        self.out.close()
        self.inp.close()
        self.ithread = None
        self.othread = None



import g729a
encoder = g729a.G729Aencoder()
decoder = g729a.G729Adecoder()

if __name__ == '__main__':
    aud = AudioInterface()
    aud.activate()

    while True:
        frame = aud.read()
        encode = encoder.process(frame)
        print(len(encode), encode)
        decode = bytes(decoder.process(encode))
        #print(decode)
        aud.write(decode)
