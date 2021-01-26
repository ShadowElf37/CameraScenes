import pyaudio
from threading import Thread
from time import sleep
from queue import Queue


def iterq(queue: Queue):
    """Creates an iterator over a Queue object"""
    while not queue.empty():
        yield queue.get()

# SERVER NEEDS MANY AUDIO STREAMS, CONSIDER CHANNELLER

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1000  # actually doubled because 16 bit samples - needs to be small for encoding, doesn't matter too much for raw
AUDIO = pyaudio.PyAudio()

class Throughput:
    def __init__(self):
        self.buffer = []
        self.open = False
        self.stream: pyaudio.Stream = None
        self.running = False

    def pause(self):
        self.open = False
        #self.stream.stop_stream()

    def unpause(self):
        #self.stream.start_stream()
        self.open = True

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
        print('Audio input has latency', self.stream.get_input_latency())
        self.buffer = Queue(100)
        self.running = True

    def activate(self):
        self.open = True  # this is for pause/unpause, it's not a mistake
        while self.running:  # running is for dead/alive
            if self.open:
                if self.buffer.full():
                    self.stream.read(CHUNK, exception_on_overflow=False)
                    continue
                try:
                    self.buffer.put(self.stream.read(CHUNK, exception_on_overflow=False))
                except OSError as e:
                    print('MIC IMPLODED LUL', str(e))
                    sleep(0.01)
            else:
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
            else:
                sleep(0.01)

    def write(self, data):
        self.buffer.put(data)


class MultipleAudioOutput:
    DUMMY = type('', (object,), {'write': lambda x: None})
    def __init__(self):
        self.outputs: {str: AudioOutput} = {}  # USE UUIDS
        self.threads = {}
        self.muted = []

    def new_output(self, uuid):
        self.outputs[uuid] = out = AudioOutput()
        self.threads[uuid] = thread = Thread(target=out.activate, daemon=True)
        thread.start()

    def close_output(self, uuid):
        if uuid in self.outputs:
            self.outputs[uuid].close()
            del self.outputs[uuid]

    def mute(self, uuid):
        if uuid not in self.muted:
            self.muted.append(uuid)
    def unmute(self, uuid):
        if uuid in self.muted:
            self.muted.remove(uuid)

    def process(self, uuid, chunk):
        if uuid not in self.muted:
            self.outputs.get(uuid, self.DUMMY).write(chunk)  # dummy is for thread safety


class AudioInterface:
    def __init__(self, output=True, input=True):
        self.inp = AudioInput()
        self.ithread = Thread(target=self.inp.activate, daemon=True)
        self.out = AudioOutput()
        self.othread = Thread(target=self.out.activate, daemon=True)

        self.use_output = output
        self.use_input = input

    def read(self):
        return self.inp.read()
    def pending(self):
        while not self.inp.buffer.empty():
            yield self.inp.read()

    def write(self, data):
        self.out.write(data)

    def activate(self):
        if self.use_input: self.ithread.start()
        if self.use_output: self.othread.start()

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


"""
from g729a import g729a

class G729ABufferedAudioInterface(AudioInterface):
    ENCODED_FRAME_SIZE = 640  # size of encoded frame to send (should be multiple of 10) (>150)
    RAW_FRAME_SIZE = 800  # size of raw frame to send (send to server only) (>160)

    def __init__(self, use_raw=True):
        self.out = MultipleAudioOutput()
        self.inp = AudioInput()
        self.ithread = Thread(target=self.inp.activate, daemon=True)
        self.encoder = g729a.G729Aencoder()
        self.decoder = g729a.G729Adecoder()

        self.temp_encoding_buffer = []  # this will take 50 160-bit frames before returning a bigger one - we have no need to be sending 10-byte udp packets, that's probably a bottleneck
        self.encoded = Queue(100)
        self.to_decode = Queue(100)

        self.use_raw = use_raw
        self.temp_raw_buffer = []
        self.raw_stream = Queue(100)

        self.encoder_thread = Thread(target=self._encode_all, daemon=True)
        self.decoder_thread = Thread(target=self._decode_all, daemon=True)

    def activate(self):
        self.ithread.start()
        self.encoder_thread.start()
        self.decoder_thread.start()

    def write_raw(self, uuid, data):
        self.out.process(uuid, data)
    def read_raw(self):
        return self.raw_stream.get()
    def pending_raw(self):
        return iterq(self.raw_stream)

    def write(self, uuid, data):
        self.to_decode.put((uuid, data))
    def read(self):
        return self.encoded.get()
    def pending(self):
        while not self.encoded.empty():
            yield self.read()

    def _encode_all(self):  # encode everything from mic and put it in input buffer
        while self.inp.running:
            raw = self.inp.read()

            self.temp_encoding_buffer.append(self.encoder.process(raw))

            if self.use_raw:
                self.temp_raw_buffer.append(raw)
                if len(self.temp_raw_buffer) == self.RAW_FRAME_SIZE//160:
                    self.raw_stream.put(b''.join(self.temp_raw_buffer))
                    self.temp_raw_buffer = []

            if len(self.temp_encoding_buffer) == self.ENCODED_FRAME_SIZE//10:
                self.encoded.put(b''.join(self.temp_encoding_buffer))
                self.temp_encoding_buffer = []

    def _decode_all(self):  # decode everything we received and put it in the output
        while self.inp.running:
            uuid, encoded = self.to_decode.get()
            frames = [encoded[i:i+10] for i in range(0, len(encoded), 10)]
            for frame in frames:
                #print(frame)
                self.out.process(uuid, bytes(self.decoder.process(frame)))
"""

if __name__ == '__main__':

    aud = AudioInterface()
    aud.activate()

    def onoff():
        while True:
            sleep(1)
            aud.mute()
            sleep(1)
            aud.unmute()
    import threading
    threading.Thread(target=onoff, daemon=True).start()

    while True:
        aud.write(aud.read())