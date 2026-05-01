from . import block, plot
import syntax

from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

import numpy as np
import random

SCALEFACTOR_COLOR = (192, 184, 192)
INTENSITY_COLOR = (224, 192, 64)

LINE_COLOR = (128, 176, 224)
MS_COLOR = (160, 212, 184)

TNS_COLOR = (248, 220, 220)

WINDOW_COLOR = (128, 128, 128)

class SpectrumScalefactorPlot(plot.PlotView):
    def __init__(self, channel):
        super(SpectrumScalefactorPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis_scalefactor = plot.AxisLinearUnsigned(128)
        v_axis_spectrum = plot.AxisLinearSigned(32) 
        win_idx = 0
        scalefactor_colors = [SCALEFACTOR_COLOR, INTENSITY_COLOR]
        spectrum_colors = [LINE_COLOR, MS_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                scalefactor_bars = []
                spectrum_points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]
                    val = ics.scale_factor_data.sf[g][sfb] - 100
                    is_intensity = ics.section_data.sfb_cb[g][sfb] in (block.INTENSITY_HCB, block.INTENSITY_HCB2)
                    color = 1 if is_intensity else 0
                    scalefactor_bars.append((color, end - start, val))

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 0
                    for bin in range(start, end):
                        value = ics.spectral_data.spec[g][win][sfb][bin - start]
                        spectrum_points.append((color, bin, value))

                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_scalefactor, scalefactor_colors, scalefactor_bars))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class RescaledSpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(RescaledSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis = plot.AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [LINE_COLOR, MS_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 0
                    for bin in range(start, end):
                        value = aac.x_rescal[self.channel][g][win][sfb][bin - start]
                        points.append((color, bin, value))

                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class SpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(SpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis = plot.AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [LINE_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for i in range(ics.params.window_length):
                    value = aac.spec[self.channel][g][win][i]
                    points.append((0, i, value))

                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class TNSSpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(TNSSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis_spectrum = plot.AxisLogarithmicSigned(7)
        v_axis_tns = plot.AxisLinearUnsigned(1) 
        win_idx = 0
        tns_colors = [TNS_COLOR]
        spectrum_colors = [LINE_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                bottom = ics.ics_info.max_sfb
                tns_bars = []
                if hasattr(ics, 'tns_data'):
                    spectrum = aac.tns_spec
                    for f in range(ics.tns_data.n_filt[win_idx]):
                        top = bottom
                        bottom = max(top - ics.tns_data.length[win_idx][f], 0)
                        tns_order = ics.tns_data.order[win_idx][f]
                        sfb_start = ics.params.swb_offset[bottom]
                        sfb_end = ics.params.swb_offset[top]
                        value = 1 if tns_order > 0 else 0
                        tns_bars.insert(0, (0, sfb_end - sfb_start, value))

                    if bottom > 0:
                        tns_bars.insert(0, (0, bottom, 0))
                else:
                    spectrum = aac.spec

                spectrum_points = []
                for i in range(ics.params.window_length):
                    value = spectrum[self.channel][g][win][i]
                    spectrum_points.append((0, i, value))

                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_tns, tns_colors, tns_bars))
                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis_spectrum, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class RawSamplesPlot(plot.PlotView):
    def __init__(self, channel):
        super(RawSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length * 2)
        v_axis_samples = plot.AxisLinearSigned(32767)
        v_axis_window = plot.AxisLinearUnsigned(1)
        win_idx = 0
        sample_colors = [LINE_COLOR]
        window_colors = [WINDOW_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                sample_points = []
                window_points = []
                for i in range(ics.params.window_length * 2):
                    value = aac.samples[self.channel][g][win][i]
                    sample_points.append((0, i, value))
                    value = aac.window(ics.ics_info.window_shape, ics.ics_info.window_sequence, i)
                    window_points.append((0, i, value))

                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_window, 1, window_colors, window_points))
                self.add_plot(win_idx, plot.PlotAxes((h_axis, 0, 0), (v_axis_samples, 0, 0)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_samples, 2, sample_colors, sample_points))
                win_idx += 1

class FinalSamplesPlot(plot.PlotView):
    def __init__(self, channel):
        super(FinalSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        self.reset()

        samples = aac.windowed_samples[self.channel]
        if prev_aac:
            prev_samples = prev_aac.windowed_samples[self.channel]
        else:
            prev_samples = [0] * 2048

        h_axis = plot.AxisLinearUnsigned(1024)
        v_axis = plot.AxisLinearSigned(32767)
        win_idx = 0
        colors = [LINE_COLOR]
        points = []
        for i in range(1024):
            value = samples[i] + prev_samples[1024 + i]
            points.append((0, i, value))

        self.add_plot(win_idx, plot.PlotAxes((h_axis, 0, 0), (v_axis, 0, 0)))
        self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))

class PerChannelView(QtWidgets.QScrollArea):
    def __init__(self, cls, title):
        super(PerChannelView, self).__init__()

        self.widget = QtWidgets.QWidget()
        self.spectrum_plots = []
        layout = QtWidgets.QVBoxLayout()
        for i in range(2):
            plot = cls(i)
            layout.addWidget(plot)
            self.spectrum_plots.append(plot)
        self.widget.setLayout(layout)
        self.widget.setMinimumSize(500, 500)
        self.setWidget(self.widget)
        self.title = title

    def set_aac(self, aac, prev_aac):
        for plot in self.spectrum_plots:
            plot.set_aac(aac, prev_aac)

    def resizeEvent(self, event):
        self.widget.setFixedSize(event.size().width(), event.size().width())

class Analyzer:
    def __init__(self, track):
        self.track = track
        self.syntax_view = syntax.SyntaxView('Syntax')

        self.aac_views = [
            PerChannelView(SpectrumScalefactorPlot, 'Raw Spectrum/Scalefactors'),
            PerChannelView(RescaledSpectrumPlot, 'Rescaled Spectrum'),
            PerChannelView(SpectrumPlot, 'Spectrum'),
            PerChannelView(TNSSpectrumPlot, 'TNS Spectrum'),
            PerChannelView(RawSamplesPlot, 'Raw Samples'),
            PerChannelView(FinalSamplesPlot, 'Final Samples')
        ]

    def get_views(self):
        return [self.syntax_view] + self.aac_views

    def set_sample(self, sample):
        (bytes, location) = self.track.getsample(sample)
        aac = block.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())

        if sample > 0:
            (prev_bytes, prev_location) = self.track.getsample(sample - 1)
            prev_aac = block.RawDataBlock()
            prev_aac.parse(prev_bytes, prev_location, self.track.es_descriptor())
        else:
            prev_aac = None

        self.syntax_view.update_syntax(self.track.bytestream, aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        for aac_view in self.aac_views:
            aac_view.set_aac(aac, prev_aac)

class WaveformPlot(QtWidgets.QWidget):
    def __init__(self, track):
        super(WaveformPlot, self).__init__()
        self.track = track
        self.setMinimumHeight(200)
        self.sample_start = 0.0
        self.sample_zoom = 1.0

        self.block_values = [None] * track.numsamples()
        self.waveform_values = np.zeros([1024 * 100, 2])
        self.waveform_start = 0
        self.waveform_valid = False
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.populate_one_block)
        self.timer.start()

        for i in range(20):
            self.populate_block(i * track.numsamples() // 20)

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
        aac = block.RawDataBlock()
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

        self.update()
        self.timer.start()
        self.update_waveform()

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
            aac = block.RawDataBlock()
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

class StreamView(QtWidgets.QWidget):
    def __init__(self, track):
        super(StreamView, self).__init__()
        self.title = 'AAC Streams'
        self.track = track
        self.aac_analyzer = Analyzer(track)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.track.numsamples())
        self.spinbox.valueChanged.connect(self.spinbox_changed)
        hlayout.addWidget(self.spinbox)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        self.waveform_plot = WaveformPlot(track)
        vlayout.addWidget(self.waveform_plot)

        tabs = QtWidgets.QTabWidget()
        for view in self.aac_analyzer.get_views():
            tabs.addTab(view, view.title)

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.spinbox_changed(0)

    def spinbox_changed(self, value):
        self.aac_analyzer.set_sample(value)
