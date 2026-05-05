from . import parse

import pyaudio
import numpy as np

from PySide2 import QtCore

BUFFER_SAMPLES = 44100 * 10 // 1024

class Player:
    def __init__(self, track):
        self.track = track
        self.stream = None
        self.start_sample = -1
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.on_timeout)

    def set_start_sample(self, start_sample):
        if start_sample != self.start_sample:
            self.start_sample = start_sample
            self.next_buffer_sample = 0
            self.buffer = np.zeros(BUFFER_SAMPLES * 1024 * 2, dtype=np.int16)
            self.timer.start()

    def play(self):    
        p = pyaudio.PyAudio()
        self.read_pointer = 0
        self.stream = p.open(format=p.get_format_from_width(2), channels=2, rate=44100, output=True, stream_callback=self.stream_callback)

    def stop(self):
        self.stream.stop_stream()

    def stream_callback(self, in_data, frame_count, time_info, status_flags):
        buffer_end = (self.next_buffer_sample - 1) * 2 * 1024
        end = min(buffer_end, self.read_pointer + frame_count * 2)
        data = self.buffer[self.read_pointer:end]
        self.read_pointer = end
        return (data, pyaudio.paContinue)

    def is_playing(self):
        return self.stream and self.stream.is_active()

    def playback_sample(self):
        if self.stream.is_active():
            return self.start_sample + self.read_pointer / (1024 * 2)
        else:
            return -1

    def playback_duration(self):
        return (self.start_sample, self.start_sample + self.next_buffer_sample)

    def on_timeout(self):
        sample = self.start_sample + self.next_buffer_sample
        (bytes, location) = self.track.getsample(sample)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())
        start = (self.next_buffer_sample - 1 ) * 2 * 1024
        if start < 0:
            self.buffer[:2048:2] += aac.windowed_samples[0][1024:].astype(np.int16)
            self.buffer[1:2048 + 1:2] += aac.windowed_samples[1][1024:].astype(np.int16)
        else:
            self.buffer[start:start + 4096:2] += aac.windowed_samples[0].astype(np.int16)
            self.buffer[start + 1:start + 1 + 4096:2] += aac.windowed_samples[1].astype(np.int16)
        self.next_buffer_sample += 1
        if self.next_buffer_sample < BUFFER_SAMPLES:
            self.timer.start()
