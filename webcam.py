import cv2 as cv
import numpy
from sys import getsizeof

import platform
PLATFORM = platform.system()

def crop(frame, x1, y1, x2, y2):
    return frame[x1:x2, y1:y2]

def scale_by(frame, factor):
    if factor < 1:
        return cv.resize(frame, factor, interpolation=cv.INTER_AREA)
    elif factor > 1:
        return cv.resize(frame, factor, interpolation=cv.INTER_LINEAR)
    return frame

def scale_to(frame: numpy.ndarray, x=0, y=0):
    # no scaling passed
    print(x, y)
    if x == y == 0:
        return frame
    ox, oy, _ = frame.shape  # third is colors
    # scaling passed that's not just old vals
    if (ox, oy) != (x, y):
        return cv.resize(frame, (y, x), interpolation=cv.INTER_AREA)
    # it was the old vals
    return frame

def jpeg_encode(frame, quality):
    _, frame = cv.imencode('.jpg', frame, (int(cv.IMWRITE_JPEG_QUALITY), quality))
    #print(getsizeof(frame))
    return frame

def jpeg_decode(frame):
    return cv.imdecode(frame, 1)

class Webcam:
    def __init__(self, *cv_conversion_flags, mirror=False, swap_axes=False, compress_quality=100, resolution=(), device=0):
        # open webcam
        if PLATFORM == 'Windows' and type(device) is int:
            self.cap = cv.VideoCapture(device, cv.CAP_DSHOW)
        else:
            self.cap = cv.VideoCapture(device)
        if not self.cap.isOpened():
            raise IOError('Failed to open webcam. Make sure it\'s connected and not in use.')
        elif self.cap.read()[1] is None:
            raise IOError('Failed to open webcam. Maybe it\'s already in use?\nOn newer Macs, this might be fixed simply by restarting the program a few times.')
        print('Webcam initialized.')
        # DONE INIT WOO

        if resolution:
            self.cap.set(cv.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.width = self.cap.get(cv.CAP_PROP_FRAME_WIDTH)  # float
        self.height = self.cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        if resolution and (self.width, self.height) != resolution:
            raise ValueError(f'Webcam can\'t manually handle resolution {resolution[0]}x{resolution[1]}')

        self.cap.set(cv.CAP_PROP_FPS, 30)

        self.compress_quality = compress_quality
        self.conversion_flags = cv_conversion_flags # these flags should be any cvtColor() flags (e.g. COLOR_BGR2RGB, etc)
        self.flip = mirror
        self.swap_axes = swap_axes # switches x and y axes, necessary for pygame for unknown reasons

        self.muted = False
        self.enforced_resolution = None

    def read(self, with_jpeg_encode=False):
        if self.muted:
            return

        frame: numpy.ndarray = self.cap.read()[1]
        if frame is None:
            print('webcam.read() didn\'t return any data - if you restart enough times it tends to work')
            return

        if self.swap_axes:
            frame = frame.swapaxes(0, 1)
        for flag in self.conversion_flags:
            frame = cv.cvtColor(frame, flag)
        if self.flip:
            frame = cv.flip(frame, 0)
        if self.enforced_resolution:
            frame = scale_to(frame, *self.enforced_resolution)
        if with_jpeg_encode and self.compress_quality < 100:
            frame = jpeg_encode(frame, self.compress_quality)

        return frame

    def mute(self):
        self.muted = True
    def unmute(self):
        self.muted = False

    def enforce_output_resolution(self, x, y):
        self.enforced_resolution = x,y

    def close(self):
        self.cap.release()

    def preview(self, w_name='Webcam Preview'):
        while True:
            print(1)
            frame = self.read()
            print(2)
            cv.imshow(w_name, frame)
            print(3)

            c = cv.waitKey(1)
            if c == ord('q'):
                break
            elif c == ord('d'):
                self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 300)
                self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 400)

        self.close()
        cv.destroyAllWindows()


if __name__ == '__main__':
    webcam = Webcam(mirror=False, swap_axes=False, resolution=(640, 480))
    webcam.preview()