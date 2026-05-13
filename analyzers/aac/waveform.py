from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

import numpy as np

from . import parse

LINE_COLOR = (128, 176, 224)
WAVEFORM_SIZE_SAMPLES = 50
MAX_BLOCK_STRIDE = 256

class BlockLayer:
    def __init__(self, plot):
        self.plot = plot

        self.values = [None] * self.plot.track.numsamples()
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.populate_one_block)

        self.active = False

        for i in range(0, self.plot.width(), 512):
            sample = int(self.plot.sample_for_pixel(i))
            self.populate_block(sample)
        self.start_populate()

    def populate_block(self, index):
        (bytes, location) = self.plot.track.getsample(index)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.plot.track.es_descriptor())
        l_val = np.sum(np.abs(aac.windowed_samples[0])) / 1024
        r_val = np.sum(np.abs(aac.windowed_samples[1])) / 1024
        self.values[index] = (l_val, r_val)

    def start_populate(self):
        self.stride = MAX_BLOCK_STRIDE
        self.index = 0
        self.timer.start()

    def populate_one_block(self):
        if not self.active:
            return

        while True:
            offset = 0 if self.stride == MAX_BLOCK_STRIDE else self.stride // 2
            p = offset + self.stride * self.index
            if p >= self.plot.width():
                if self.stride == 2:
                    return
                else:
                    self.stride //= 2
                    self.index = 0
            else:
                self.index += 1
                sample = int(self.plot.sample_for_pixel(p))
                if self.values[sample] is None:
                    self.populate_block(sample)
                    self.plot.update()
                    self.timer.start()
                    return

    def draw(self, painter):
        brush = QtGui.QBrush(QtGui.QColor(*LINE_COLOR))
        for x in range(self.plot.width()):
            sample = int(self.plot.sample_for_pixel(x))
            while sample > 0 and self.values[sample] is None:
                sample -= 1

            if self.values[sample] is None:
                continue

            (l_val, r_val) = self.values[sample]

            h = self.plot.height() / 2 * l_val / 32767
            y = self.plot.height() / 4 - h / 2 
            painter.fillRect(x, y, 1, h, brush)

            h = self.plot.height() / 2 * r_val / 32767
            y = self.plot.height() * 3 / 4 - h / 2 
            painter.fillRect(x, y, 1, h, brush)

    def background_pause(self):
        self.active = False

    def background_resume(self):
        self.active = True
        self.start_populate()

class SamplesLayer:
    def __init__(self, plot):
        self.plot = plot

        self.values = np.zeros([1024 * WAVEFORM_SIZE_SAMPLES, 2])
        self.start = 0
        self.valid = False
        self.update_range = None
        self.update_next = -1
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.populate_next_segment)

    def can_draw(self):
       return self.valid and self.plot.track.numsamples() / self.plot.sample_zoom < len(self.values) // 1024
         
    def populate_next_segment(self):
        self.populate_segment(self.update_next)
        self.update_next += 1
        if self.update_next == self.update_range[1]:
            self.valid = True
            self.plot.update()
        else:
            self.timer.start()

    def populate_segment(self, i):
        (bytes, location) = self.plot.track.getsample(i + self.start)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.plot.track.es_descriptor())
        if i == self.update_range[0]:
            start = i * 1024 + 1024
            self.values[start:start+1024, 0] += aac.windowed_samples[0][1024:]
            self.values[start:start+1024, 1] += aac.windowed_samples[1][1024:]
        elif i == self.update_range[1] - 1:
            start = i * 1024
            self.values[start:start+1024, 0] += aac.windowed_samples[0][:1024]
            self.values[start:start+1024, 1] += aac.windowed_samples[1][:1024]
        else:
            start = i * 1024
            self.values[start:start+2048, 0] += aac.windowed_samples[0]
            self.values[start:start+2048, 1] += aac.windowed_samples[1]

    def update_waveform(self):
        max_block = len(self.values) // 1024

        if self.plot.track.numsamples() / self.plot.sample_zoom >= max_block:
            return

        update_range = (0, 0)
        update_now = False
        if self.valid:
            shift = int(self.plot.sample_start) - self.start
            if shift > 0 and shift < max_block:
                shift_left = shift
                shift_left_samples = shift_left * 1024
                self.values[0:-shift_left_samples] = self.values[shift_left_samples:]
                self.values[-shift_left_samples:] = np.zeros([shift_left_samples, 2])
                update_range = (max_block - shift_left - 1, max_block)
                update_now = True
            elif shift < 0 and shift > -max_block:
                shift_right = -shift
                shift_right_samples = shift_right * 1024
                self.values[shift_right_samples:] = self.values[0:-shift_right_samples]
                self.values[0:shift_right_samples] = np.zeros([shift_right_samples, 2])
                update_range = (-1, shift_right)
                update_now = True
            elif shift != 0:
                update_range = (-1, max_block)
                self.valid = False
                self.values = np.zeros([1024 * WAVEFORM_SIZE_SAMPLES, 2])
        elif self.start != int(self.plot.sample_start):
            update_range = (-1, max_block)
            self.values = np.zeros([1024 * WAVEFORM_SIZE_SAMPLES, 2])
        
        self.start = int(self.plot.sample_start)

        if update_range != (0, 0):
            self.update_range = update_range
            if update_now:
                for i in range(*update_range):
                    self.populate_segment(i)
            else:
                self.update_next = update_range[0]    
                self.timer.start()

    def draw(self, painter):
        pen = QtGui.QPen(QtGui.QColor(*LINE_COLOR))
        painter.setPen(pen)
        prev = (0, 0)
        for x in range(self.plot.width()):
            sample = self.plot.sample_for_pixel(x)
            i = int((sample - self.start) * 1024)
            (l_val, r_val) = self.values[i]

            h = self.plot.height() / 2 * l_val / 32767
            y_l = self.plot.height() / 4 - h / 2 
            
            h = self.plot.height() / 2 * r_val / 32767
            y_r = self.plot.height() * 3 / 4 - h / 2 
            if x > 0:
                (prev_l, prev_r) = prev
                painter.drawLine(x-1, prev_l, x, y_l)
                painter.drawLine(x-1, prev_r, x, y_r)
            prev = (y_l, y_r)

class SelectLayer:
    def __init__(self, plot):
        self.plot = plot
        self.windows = [np.zeros(2048)]

    def update_selected_sample(self):
        (bytes, location) = self.plot.track.getsample(self.plot.selected_sample)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.plot.track.es_descriptor())
        ics = aac.parsed_block.cpe.ics[0]
        params = ics.params
        ics_info = ics.ics_info
        self.windows = [None] * params.num_windows
        if params.num_windows == 1:
            self.windows[0] = np.zeros(2048)
            for i in range(2048):
                self.windows[0][i] = aac.window(ics_info.window_shape, ics_info.window_sequence, i)
        else:
            for w in range(params.num_windows):
                self.windows[w] = np.zeros(2048)
                for i in range(256):
                    start = 448 + w * 128
                    self.windows[w][start + i] = aac.window(ics_info.window_shape, ics_info.window_sequence, i)

        self.plot.update()

    def draw(self, painter):
        if self.plot.selected_sample != -1:
            sx = self.plot.pixel_for_sample(self.plot.selected_sample)
            ex = self.plot.pixel_for_sample(self.plot.selected_sample + 2)

            window_pen = QtGui.QPen(QtGui.QColor(128, 128, 128))
            painter.setPen(window_pen)
            for win in self.windows:
                prev_y = None
                for x in range(sx, ex):
                    if x < 0 or x >= self.plot.width():
                        continue
                    n = (x - sx) * 2048 // (ex - sx)
                    y = self.plot.height() * (1 - win[n])
                    if prev_y:
                        painter.drawLine(x - 1, prev_y, x, y)
                    prev_y = y

            ex = min(ex, self.plot.width())
            sx = max(sx, 0)
            if ex > 0 and sx < self.plot.width():
                w = ex - sx
                selected_pen = QtGui.QPen(QtGui.QColor(160, 160, 160), 5)
                painter.setPen(selected_pen)
                painter.drawRect(sx, 3, w, self.plot.height() - 6)

class HoverLayer:
    def __init__(self, plot):
        self.plot = plot
        self.hover_sample = -1

    def update_hover(self, x):
        s = int(self.plot.sample_for_pixel(x))
        if s != self.hover_sample:
            self.hover_sample = s
            self.plot.update()

    def leave_hover(self):
        self.hover_sample = -1
        self.plot.update()

    def draw(self, painter):
        if self.hover_sample != -1:
            sx = max(self.plot.pixel_for_sample(self.hover_sample), 0)
            ex = min(self.plot.pixel_for_sample(self.hover_sample + 2), self.plot.width())
            if ex > 0 and sx < self.plot.width():
                w = ex - sx
                hover_pen = QtGui.QPen(QtGui.QColor(255, 192, 160), 5)
                painter.setPen(hover_pen)
                painter.drawRect(sx, 3, w, self.plot.height() - 6)

class PlaybackLayer:
    def __init__(self, plot):
        self.plot = plot
        self.current_sample = -1
        self.start_sample = 0
        self.end_sample = 0

    def set_playback_status(self, start_sample, end_sample, current_sample):
        self.start_sample = start_sample
        self.end_sample = end_sample
        self.current_sample = current_sample
        self.plot.update()

    def draw_early(self, painter):
        if self.current_sample != -1:
            sx = self.plot.pixel_for_sample(self.start_sample)
            ex = self.plot.pixel_for_sample(self.end_sample)
            duration_brush = QtGui.QBrush(QtGui.QColor(220, 220, 220))
            painter.fillRect(sx, 0, ex - sx, self.plot.height(), duration_brush)

    def draw_late(self, painter):
        if self.current_sample != -1:
            p = self.plot.pixel_for_sample(self.current_sample)
            playback_pen = QtGui.QPen(QtGui.QColor(0, 0, 255), 3)
            painter.setPen(playback_pen)
            painter.drawLine(p, 0, p, self.plot.height())

class WaveformPlot(QtWidgets.QWidget):
    def __init__(self, track):
        super(WaveformPlot, self).__init__()
        self.track = track
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self.sample_start = 0.0
        self.sample_zoom = 1.0
        self.selected_sample = 0
        self.select_listener = None
        self.drag_start = None
        self.drag_sample_start = 0

        self.block_layer = BlockLayer(self)
        self.samples_layer = SamplesLayer(self)
        self.select_layer = SelectLayer(self)
        self.hover_layer = HoverLayer(self)
        self.playback_layer = PlaybackLayer(self)

    def set_select_listener(self, listener):
        self.select_listener = listener

    def set_playback_status(self, start_sample, end_sample, current_sample):
        self.playback_layer.set_playback_status(start_sample, end_sample, current_sample)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        self.playback_layer.draw_early(painter)

        if self.samples_layer.can_draw():
            self.samples_layer.draw(painter)
        else:
            self.block_layer.draw(painter)

        self.select_layer.draw(painter)
        self.hover_layer.draw(painter)

        self.playback_layer.draw_late(painter)

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

        self.hover_layer.update_hover(event.position().x())
        self.update()
        self.block_layer.start_populate()
        self.samples_layer.update_waveform()

    def enterEvent(self, event):
        self.hover_layer.update_hover(event.localPos().x())

    def leaveEvent(self, event):
        self.hover_layer.leave_hover()

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
            self.samples_layer.update_waveform()
            self.block_layer.start_populate()

        self.hover_layer.update_hover(event.localPos().x())

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            s = int(self.sample_for_pixel(event.localPos().x()))
            self.set_selected_sample(s)
        else:
            self.drag_start = None

    def resizeEvent(self, event):
        self.block_layer.start_populate()

    def showEvent(self, event):
        self.block_layer.background_resume()

    def hideEvent(self, event):
        self.block_layer.background_pause()

    def set_selected_sample(self, value):
        if self.selected_sample != value:
            self.selected_sample = value
            if self.select_listener:
                self.select_listener(value)
            self.select_layer.update_selected_sample()

    def pixel_for_sample(self, s):
        return int((s - self.sample_start) * self.sample_zoom * self.width() / self.track.numsamples())

    def sample_for_pixel(self, x):
        return x * self.track.numsamples() / (self.sample_zoom * self.width()) + self.sample_start
