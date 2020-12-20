from typing import *
import ctypes
import os
import platform

p = platform.system()

if p == 'Windows':
    g729a_lib_path = 'libg729a.dll'
elif p == 'Darwin':
    g729a_lib_path = 'macos_libg729a.so'
elif p == 'Linux':
    g729a_lib_path = 'libg729a.so'
else:
    raise RuntimeError("Unknown OS")

g729a_lib_path = os.path.join('..', g729a_lib_path)

class G729Acoder:
    SAMPLES_IN_FRAME = 80
    BYTES_IN_COMPRESSED_FRAME = 10
    def __init__(
        self, 
        f_stateSize: Callable[[], int], 
        f_init: Callable[[Any], int], 
        f_process: Callable[[Any, Any, Any], int],
        inputSize: int,
        outputSize: int
    ) -> None:
        self._state = (ctypes.c_byte * f_stateSize())()
        if f_init(self._state) != 0:
            raise RuntimeError("G729 init state function " + f_init.__name__ + " returned error")
        self._f_process = f_process
        self.inputSize = inputSize
        self.outputSize = outputSize

    def process(self, input: bytearray) -> bytearray:
        if len(input) != self.inputSize:
            raise RuntimeError("G729: incorrect input size in process(). Expected: " + str(self.inputSize) +". Got: " + str(len(input)))
        inData = (ctypes.c_byte * len(input))(*input)
        outData = (ctypes.c_byte * self.outputSize)()
        if self._f_process(self._state, inData, outData) != 0:
            raise RuntimeError("G729 process function " + self._f_process.__name__ + " returned error")
        return bytearray(outData)

class G729Aencoder(G729Acoder):
    def __init__(self) -> None:
        g729aLib = ctypes.CDLL(g729a_lib_path)
        super().__init__(
            g729aLib.G729A_Encoder_Get_Size,
            g729aLib.G729A_Encoder_Init,
            g729aLib.G729A_Encoder_Process,
            self.SAMPLES_IN_FRAME*2,
            self.BYTES_IN_COMPRESSED_FRAME
        )

class G729Adecoder(G729Acoder):
    def __init__(self) -> None:
        g729aLib = ctypes.CDLL(g729a_lib_path)
        super().__init__(
            g729aLib.G729A_Decoder_Get_Size,
            g729aLib.G729A_Decoder_Init,
            g729aLib.G729A_Decoder_Process,
            self.BYTES_IN_COMPRESSED_FRAME,
            self.SAMPLES_IN_FRAME*2
        )

if __name__ == "__main__":
    G729Aencoder()

"""
NOTE: THIS CODE HAS BEEN MODIFIED FROM SOURCE
ORIGINAL: https://github.com/AlexIII/g729a-python


LICENSE

Copyright (c) 2015, Russell
Copyright (c) 2019, github.com/AlexIII
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""