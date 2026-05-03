from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

import numpy as np
import random

from . import parse

LINE_COLOR = (128, 176, 224)

class WaveformPlot(QtWidgets.QWidget):
    def __init__(self, track):
        super(WaveformPlot, self).__init__()
        self.track = track
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self.sample_start = 0.0
        self.sample_zoom = 1.0
        self.hover_sample = -1
        self.selected_sample = 0
        self.selected_sample_windows = [np.zeros(2048)]
        self.select_listener = None

        self.block_values = [None] * track.numsamples()
        self.waveform_values = np.zeros([1024 * 50, 2])
        self.waveform_start = 0
        self.waveform_valid = False
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.populate_one_block)
        self.timer.start()

        for i in range(20):
            self.populate_block(i * track.numsamples() // 20)

    def set_select_listener(self, listener):
        self.select_listener = listener

    def populate_one_block(self):
        center = random.randint(0, self.width())

        sample = 0
        for i in range(self.width()):
            if center + i < self.width():
                s = int(self.sample_for_pixel(center + i))
                if self.block_values[s] is None:
                    sample = s
                    break
            elif center - i >= 0:
                s = int(self.sample_for_pixel(center - i))
                if self.block_values[s] is None:
                    sample = s
                    break
            else:
                break

        if self.block_values[sample] is None:
            self.populate_block(sample)
            self.update()
            self.timer.start()

    def populate_block(self, index):
        (bytes, location) = self.track.getsample(index)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())
        l_val = np.sum(np.abs(aac.windowed_samples[0])) / 1024
        r_val = np.sum(np.abs(aac.windowed_samples[1])) / 1024
        self.block_values[index] = (l_val, r_val)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if not self.waveform_valid or self.track.numsamples() / self.sample_zoom >= len(self.waveform_values) // 1024:
            brush = QtGui.QBrush(QtGui.QColor(*LINE_COLOR))
            for x in range(self.width()):
                sample = int(self.sample_for_pixel(x))
                while sample > 0 and self.block_values[sample] is None:
                    sample -= 1

                if self.block_values[sample] is None:
                    continue

                (l_val, r_val) = self.block_values[sample]

                h = self.height() / 2 * l_val / 32767
                y = self.height() / 4 - h / 2 
                painter.fillRect(x, y, 1, h, brush)

                h = self.height() / 2 * r_val / 32767
                y = self.height() * 3 / 4 - h / 2 
                painter.fillRect(x, y, 1, h, brush)
        else:
            pen = QtGui.QPen(QtGui.QColor(*LINE_COLOR))
            painter.setPen(pen)
            prev = (0, 0)
            for x in range(self.width()):
                sample = self.sample_for_pixel(x)
                i = int((sample - self.waveform_start) * 1024)
                (l_val, r_val) = self.waveform_values[i]

                h = self.height() / 2 * l_val / 32767
                y_l = self.height() / 4 - h / 2 
                
                h = self.height() / 2 * r_val / 32767
                y_r = self.height() * 3 / 4 - h / 2 
                if x > 0:
                    (prev_l, prev_r) = prev
                    painter.drawLine(x-1, prev_l, x, y_l)
                    painter.drawLine(x-1, prev_r, x, y_r)
                prev = (y_l, y_r)

        if self.selected_sample != -1:
            sx = self.pixel_for_sample(self.selected_sample)
            ex = self.pixel_for_sample(self.selected_sample + 2)

            window_pen = QtGui.QPen(QtGui.QColor(128, 128, 128))
            painter.setPen(window_pen)
            for win in self.selected_sample_windows:
                prev_y = None
                for x in range(sx, ex):
                    if x < 0 or x >= self.width():
                        continue
                    n = (x - sx) * 2048 // (ex - sx)
                    y = self.height() * (1 - win[n])
                    if prev_y:
                        painter.drawLine(x - 1, prev_y, x, y)
                    prev_y = y

            ex = min(ex, self.width())
            sx = max(sx, 0)
            if ex > 0 and sx < self.width():
                w = ex - sx
                selected_pen = QtGui.QPen(QtGui.QColor(160, 160, 160), 5)
                painter.setPen(selected_pen)
                painter.drawRect(sx, 3, w, self.height() - 6)

        if self.hover_sample != -1:
            sx = max(self.pixel_for_sample(self.hover_sample), 0)
            ex = min(self.pixel_for_sample(self.hover_sample + 2), self.width())
            if ex > 0 and sx < self.width():
                w = ex - sx
                hover_pen = QtGui.QPen(QtGui.QColor(255, 192, 160), 5)
                painter.setPen(hover_pen)
                painter.drawRect(sx, 3, w, self.height() - 6)

        edge_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
        painter.setPen(edge_pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        painter.end()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ShiftModifier:
            delta = self.track.numsamples() / (10 * self.sample_zoom)
            max_start = self.track.numsamples() * (1 - 1/self.sample_zoom)
            if event.angleDelta().y() > 0:
                self.sample_start = min(self.sample_start + delta, max_start)
            else:
                self.sample_start = max(self.sample_start - delta, 0)
        else:
            cursor_sample = self.sample_for_pixel(event.position().x())
            if event.angleDelta().y() > 0:
                self.sample_zoom *= 1.25
            else:
                self.sample_zoom = max(self.sample_zoom / 1.25, 1.0)
            self.sample_start = cursor_sample - event.position().x() * self.track.numsamples() / (self.sample_zoom * self.width())
            max_start = self.track.numsamples() * (1 - 1/self.sample_zoom)
            self.sample_start = max(min(self.sample_start, max_start), 0)

        self.update_hover(event.position().x())
        self.update()
        self.timer.start()
        self.update_waveform()

    def enterEvent(self, event):
        self.update_hover(event.localPos().x())

    def leaveEvent(self, event):
        self.hover_sample = -1
        self.update()

    def mouseMoveEvent(self, event):
        self.update_hover(event.localPos().x())

    def mousePressEvent(self, event):
        s = int(self.sample_for_pixel(event.localPos().x()))
        self.set_selected_sample(s)

    def set_selected_sample(self, value):
        if self.selected_sample != value:
            self.selected_sample = value
            if self.select_listener:
                self.select_listener(value)
            (bytes, location) = self.track.getsample(value)
            aac = parse.RawDataBlock()
            aac.parse(bytes, location, self.track.es_descriptor())
            ics = aac.parsed_block.cpe.ics[0]
            params = ics.params
            ics_info = ics.ics_info
            self.selected_sample_windows = [None] * params.num_windows
            if params.num_windows == 1:
                self.selected_sample_windows[0] = np.zeros(2048)
                for i in range(2048):
                    self.selected_sample_windows[0][i] = aac.window(ics_info.window_shape, ics_info.window_sequence, i)
            else:
                for w in range(params.num_windows):
                    self.selected_sample_windows[w] = np.zeros(2048)
                    for i in range(256):
                        start = 448 + w * 128
                        self.selected_sample_windows[w][start + i] = aac.window(ics_info.window_shape, ics_info.window_sequence, i)

            self.update()

    def update_hover(self, x):
        s = int(self.sample_for_pixel(x))
        if s != self.hover_sample:
            self.hover_sample = s
            self.update()

    def update_waveform(self):
        max_block = len(self.waveform_values) // 1024

        if self.track.numsamples() / self.sample_zoom >= max_block:
            return

        update_range = (-1, max_block)
        if self.waveform_valid:
            shift = int(self.sample_start) - self.waveform_start
            if shift > 0 and shift < max_block:
                shift_left = shift
                shift_left_samples = shift_left * 1024
                self.waveform_values[0:-shift_left_samples] = self.waveform_values[shift_left_samples:]
                self.waveform_values[-shift_left_samples:] = np.zeros([shift_left_samples, 2])
                update_range = (max_block - shift_left - 1, max_block)
            elif shift < 0 and shift > -max_block:
                shift_right = -shift
                shift_right_samples = shift_right * 1024
                self.waveform_values[shift_right_samples:] = self.waveform_values[0:-shift_right_samples]
                self.waveform_values[0:shift_right_samples] = np.zeros([shift_right_samples, 2])
                update_range = (-1, shift_right)
            elif shift == 0:
                update_range = (0, 0)
        self.waveform_start = int(self.sample_start)

        for i in range(*update_range):
            (bytes, location) = self.track.getsample(i + self.waveform_start)
            aac = parse.RawDataBlock()
            aac.parse(bytes, location, self.track.es_descriptor())
            if i == update_range[0]:
                start = i * 1024 + 1024
                self.waveform_values[start:start+1024, 0] += aac.windowed_samples[0][1024:]
                self.waveform_values[start:start+1024, 1] += aac.windowed_samples[1][1024:]
            elif i == update_range[1] - 1:
                start = i * 1024
                self.waveform_values[start:start+1024, 0] += aac.windowed_samples[0][:1024]
                self.waveform_values[start:start+1024, 1] += aac.windowed_samples[1][:1024]
            else:
                start = i * 1024
                self.waveform_values[start:start+2048, 0] += aac.windowed_samples[0]
                self.waveform_values[start:start+2048, 1] += aac.windowed_samples[1]
        self.waveform_valid = True

    def pixel_for_sample(self, s):
        return int((s - self.sample_start) * self.sample_zoom * self.width() / self.track.numsamples())

    def sample_for_pixel(self, x):
        return x * self.track.numsamples() / (self.sample_zoom * self.width()) + self.sample_start
