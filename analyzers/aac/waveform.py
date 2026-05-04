from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

import numpy as np
import random

from . import parse

LINE_COLOR = (128, 176, 224)
WAVEFORM_SIZE_SAMPLES = 50
MAX_BLOCK_STRIDE = 256
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
        self.drag_start = None
        self.drag_sample_start = 0

        self.block_values = [None] * track.numsamples()
        self.block_timer = QtCore.QTimer()
        self.block_timer.setSingleShot(True)
        self.block_timer.setInterval(0)
        self.block_timer.timeout.connect(self.populate_one_block)

        self.waveform_values = np.zeros([1024 * WAVEFORM_SIZE_SAMPLES, 2])
        self.waveform_start = 0
        self.waveform_valid = False
        self.waveform_update_range = None
        self.waveform_update_next = -1
        self.waveform_timer = QtCore.QTimer()
        self.waveform_timer.setSingleShot(True)
        self.waveform_timer.setInterval(0)
        self.waveform_timer.timeout.connect(self.populate_next_waveform_segment)

        for i in range(0, self.width(), 512):
            sample = int(self.sample_for_pixel(i))
            self.populate_block(sample)
        self.start_block_populate()

    def set_select_listener(self, listener):
        self.select_listener = listener

    def start_block_populate(self):
        self.block_stride = MAX_BLOCK_STRIDE
        self.block_index = 0
        self.block_timer.start()

    def populate_one_block(self):
        while True:
            offset = 0 if self.block_stride == MAX_BLOCK_STRIDE else self.block_stride // 2
            p = offset + self.block_stride * self.block_index
            if p >= self.width():
                if self.block_stride == 2:
                    return
                else:
                    self.block_stride //= 2
                    self.block_index = 0
            else:
                self.block_index += 1
                sample = int(self.sample_for_pixel(p))
                if self.block_values[sample] is None:
                    self.populate_block(sample)
                    self.update()
                    self.block_timer.start()
                    return

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
        self.start_block_populate()
        self.update_waveform()

    def enterEvent(self, event):
        self.update_hover(event.localPos().x())

    def leaveEvent(self, event):
        self.hover_sample = -1
        self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self.drag_start is None:
                self.drag_start = event.localPos()
                self.drag_sample_start = self.sample_start
            pixel_delta = event.localPos().x() - self.drag_start.x()
            delta = self.track.numsamples() * pixel_delta / (self.sample_zoom * self.width())
            max_start = self.track.numsamples() * (1 - 1/self.sample_zoom)
            if delta < 0:
                self.sample_start = min(self.drag_sample_start - delta, max_start)
            else:
                self.sample_start = max(self.drag_sample_start - delta, 0)
            self.update()
            self.update_waveform()
            self.start_block_populate()

        self.update_hover(event.localPos().x())

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            s = int(self.sample_for_pixel(event.localPos().x()))
            self.set_selected_sample(s)
        else:
            self.drag_start = None

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
        update_now = False
        if self.waveform_valid:
            shift = int(self.sample_start) - self.waveform_start
            if shift > 0 and shift < max_block:
                shift_left = shift
                shift_left_samples = shift_left * 1024
                self.waveform_values[0:-shift_left_samples] = self.waveform_values[shift_left_samples:]
                self.waveform_values[-shift_left_samples:] = np.zeros([shift_left_samples, 2])
                update_range = (max_block - shift_left - 1, max_block)
                update_now = True
            elif shift < 0 and shift > -max_block:
                shift_right = -shift
                shift_right_samples = shift_right * 1024
                self.waveform_values[shift_right_samples:] = self.waveform_values[0:-shift_right_samples]
                self.waveform_values[0:shift_right_samples] = np.zeros([shift_right_samples, 2])
                update_range = (-1, shift_right)
                update_now = True
            elif shift == 0:
                update_range = (0, 0)
        elif self.waveform_start != int(self.sample_start):
            self.waveform_values = np.zeros([1024 * WAVEFORM_SIZE_SAMPLES, 2])
        
        self.waveform_start = int(self.sample_start)

        if update_range != (0, 0):
            if update_now:
                for i in range(*update_range):
                    self.populate_waveform_segment(i)
            else:
                self.waveform_update_range = update_range
                self.waveform_update_next = update_range[0]    
                self.waveform_timer.start()

    def populate_next_waveform_segment(self):
        self.populate_waveform_segment(self.waveform_update_next)
        self.waveform_update_next += 1
        if self.waveform_update_next == self.waveform_update_range[1]:
            self.waveform_valid = True
            self.update()
        else:
            self.waveform_timer.start()

    def populate_waveform_segment(self, i):
        (bytes, location) = self.track.getsample(i + self.waveform_start)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())
        if i == self.waveform_update_range[0]:
            start = i * 1024 + 1024
            self.waveform_values[start:start+1024, 0] += aac.windowed_samples[0][1024:]
            self.waveform_values[start:start+1024, 1] += aac.windowed_samples[1][1024:]
        elif i == self.waveform_update_range[1] - 1:
            start = i * 1024
            self.waveform_values[start:start+1024, 0] += aac.windowed_samples[0][:1024]
            self.waveform_values[start:start+1024, 1] += aac.windowed_samples[1][:1024]
        else:
            start = i * 1024
            self.waveform_values[start:start+2048, 0] += aac.windowed_samples[0]
            self.waveform_values[start:start+2048, 1] += aac.windowed_samples[1]

    def pixel_for_sample(self, s):
        return int((s - self.sample_start) * self.sample_zoom * self.width() / self.track.numsamples())

    def sample_for_pixel(self, x):
        return x * self.track.numsamples() / (self.sample_zoom * self.width()) + self.sample_start
