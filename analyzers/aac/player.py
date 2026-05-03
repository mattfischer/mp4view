from . import parse

import pyaudio
import numpy as np

BUFFER_SAMPLES = 100

class Player:
    def __init__(self, track):
        self.track = track
        self.stream = None

    def play(self, start_sample):
        buffer = np.zeros(BUFFER_SAMPLES * 1024 * 2, dtype=np.int16)
        
        sample = start_sample
        write_pointer = 0 
        for i in range(BUFFER_SAMPLES - 1):
            (bytes, location) = self.track.getsample(sample)
            aac = parse.RawDataBlock()
            aac.parse(bytes, location, self.track.es_descriptor())
            start = write_pointer * 2
            buffer[start:start + 4096:2] += aac.windowed_samples[0].astype(np.int16)
            buffer[start + 1:start + 1 + 4096:2] += aac.windowed_samples[1].astype(np.int16)
            write_pointer += 1024
            sample += 1

        p = pyaudio.PyAudio()
        self.stream = p.open(format=p.get_format_from_width(2), channels=2, rate=44100, output=True)
        self.stream.write(buffer[:(BUFFER_SAMPLES - 1) * 1024 * 2])
