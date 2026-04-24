import math

from .file import File
from .aac import AAC, INTENSITY_HCB, INTENSITY_HCB2
from .aac import ONLY_LONG_SEQUENCE, LONG_START_SEQUENCE, EIGHT_SHORT_SEQUENCE, LONG_STOP_SEQUENCE

from syntax import SyntaxView

from PySide2 import QtWidgets, QtGui

class AACSpectrumScalefactorPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACSpectrumScalefactorPlot, self).__init__()
        self.channel = channel
        self.aac = None

    def set_aac(self, aac):
        self.aac = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]

        prev = None
        regular_brush = QtGui.QBrush(QtGui.QColor(192, 192, 192))
        intensity_brush = QtGui.QBrush(QtGui.QColor(192, 192, 0))
        
        ms_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        lr_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 224, 176)), 2)

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)

        win_idx = 0
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]
                    val = ics.scale_factor_data.sf[g][sfb] - 100

                    sx = self.width() * (win_idx + start / ics.params.window_length) / ics.params.num_windows
                    ex = self.width() * (win_idx + end / ics.params.window_length) / ics.params.num_windows
                    w = ex - sx - 1
                    h = self.height() * val/128

                    if ics.section_data.sfb_cb[g][sfb] in (INTENSITY_HCB, INTENSITY_HCB2):
                        brush = intensity_brush
                    else:
                        brush = regular_brush

                    painter.fillRect(sx, self.height() - h, w, h, brush)

                    ms_used = (self.aac.parsed_block.cpe.ms_mask_present == 2 or 
                            (self.aac.parsed_block.cpe.ms_mask_present == 1 and self.aac.parsed_block.cpe.ms_used[g][sfb]))

                    if ms_used:
                        painter.setPen(ms_pen)
                    else:
                        painter.setPen(lr_pen)

                    for bin in range(start, end):
                        s = ics.spectral_data.spec[g][win][sfb][bin - start]
                        x = self.width() * (win_idx + bin / ics.params.window_length) / ics.params.num_windows
                        y = self.height() * (1 + s / 32) / 2
                        if prev:
                            (prev_x, prev_y) = prev
                            painter.drawLine(prev_x, prev_y, x, y)
                        prev = (x, y)

                prev = None
                win_idx += 1
                if win_idx < ics.params.num_windows:
                    painter.setPen(window_pen)
                    x = self.width() * win_idx / ics.params.num_windows
                    painter.drawLine(x, 0, x, self.height())

        painter.end()

class AACRescaledSpectrumPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACRescaledSpectrumPlot, self).__init__()
        self.channel = channel
        self.aac = None

    def set_aac(self, aac):
        self.aac = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        pen_major = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 1)
        pen_minor = QtGui.QPen(QtGui.QBrush(QtGui.QColor(192, 192, 192)), 1)
        
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
        for p in range(7):
            painter.setPen(pen_major)
            h = self.height() * p / 14
            h2 = self.height() / 2
            painter.drawLine(0, h2 + h, self.width(), h2 + h)
            painter.drawLine(0, h2 - h, self.width(), h2 - h)

            painter.setPen(pen_minor)
            x = 10 ** p
            for i in range(2, 10, 2):
                h = self.height() * math.log(x * i, 10) / 14
                painter.drawLine(0, h2 + h, self.width(), h2 + h)
                painter.drawLine(0, h2 - h, self.width(), h2 - h)

        for i in range(0, 1024, 16):
            if i % 64 == 0:
                painter.setPen(pen_major)
            else:
                painter.setPen(pen_minor)

            w = self.width() * i / 1024
            painter.drawLine(w, 0, w, self.height())

        ics = self.aac.parsed_block.cpe.ics[self.channel]

        ms_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        lr_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 224, 176)), 2)

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)

        prev = None
        win_idx = 0
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]

                    ms_used = (self.aac.parsed_block.cpe.ms_mask_present == 2 or 
                            (self.aac.parsed_block.cpe.ms_mask_present == 1 and self.aac.parsed_block.cpe.ms_used[g][sfb]))

                    if ms_used:
                        painter.setPen(ms_pen)
                    else:
                        painter.setPen(lr_pen)

                    for bin in range(start, end):
                        s = self.aac.x_rescal[self.channel][g][win][sfb][bin - start]
                        x = self.width() * (win_idx + bin / ics.params.window_length) / ics.params.num_windows
                        sign = 1 if s > 0 else -1
                        y = self.height() * (1 - sign * math.log(1 + abs(s), 10) / 7) / 2
                        if prev:
                            (prev_x, prev_y) = prev
                            painter.drawLine(prev_x, prev_y, x, y)
                        prev = (x, y)

                prev = None
                win_idx += 1
                if win_idx < ics.params.num_windows:
                    painter.setPen(window_pen)
                    x = self.width() * win_idx / ics.params.num_windows
                    painter.drawLine(x, 0, x, self.height())

        painter.end()

class AACSpectrumPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACSpectrumPlot, self).__init__()
        self.channel = channel
        self.aac = None

    def set_aac(self, aac):
        self.aac = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]

        pen_major = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 1)
        pen_minor = QtGui.QPen(QtGui.QBrush(QtGui.QColor(192, 192, 192)), 1)
        
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
        for p in range(7):
            painter.setPen(pen_major)
            h = self.height() * p / 14
            h2 = self.height() / 2
            painter.drawLine(0, h2 + h, self.width(), h2 + h)
            painter.drawLine(0, h2 - h, self.width(), h2 - h)

            painter.setPen(pen_minor)
            x = 10 ** p
            for i in range(2, 10, 2):
                h = self.height() * math.log(x * i, 10) / 14
                painter.drawLine(0, h2 + h, self.width(), h2 + h)
                painter.drawLine(0, h2 - h, self.width(), h2 - h)

        for i in range(0, 1024, 16):
            if i % 64 == 0:
                painter.setPen(pen_major)
            else:
                painter.setPen(pen_minor)

            w = self.width() * i / 1024
            painter.drawLine(w, 0, w, self.height())

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)

        prev = None
        win_idx = 0
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                painter.setPen(pen)
                for i in range(ics.params.window_length):
                    s = self.aac.spec[self.channel][g][win][i]
                    x = self.width() * (win_idx + i / ics.params.window_length) / ics.params.num_windows
                    sign = 1 if s > 0 else -1
                    y = self.height() * (1 - sign * math.log(1 + abs(s), 10) / 7) / 2
                    if prev:
                        (prev_x, prev_y) = prev
                        painter.drawLine(prev_x, prev_y, x, y)
                    prev = (x, y)

                prev = None
                win_idx += 1
                if win_idx < ics.params.num_windows:
                    painter.setPen(window_pen)
                    x = self.width() * win_idx / ics.params.num_windows
                    painter.drawLine(x, 0, x, self.height())

        painter.end()

class AACTnsSpectrumPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACTnsSpectrumPlot, self).__init__()
        self.channel = channel
        self.aac = None

    def set_aac(self, aac):
        self.aac = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]

        if hasattr(ics, 'tns_data'):
            tns_brush = QtGui.QBrush(QtGui.QColor(192, 192, 192))
            win_idx = 0
            for g in range(ics.params.num_window_groups):
                for win in range(ics.params.window_group_length[g]):        
                    bottom = ics.ics_info.max_sfb
                    for f in range(ics.tns_data.n_filt[win_idx]):
                        top = bottom
                        bottom = max(top - ics.tns_data.length[win_idx][f], 0)
                        tns_order = ics.tns_data.order[win_idx][f]
                        if tns_order > 0:
                            sfb_start = ics.params.swb_offset[bottom]
                            sfb_end = ics.params.swb_offset[top]
                            sx = self.width() * (win_idx + sfb_start / ics.params.window_length) / ics.params.num_windows
                            ex = self.width() * (win_idx + sfb_end / ics.params.window_length) / ics.params.num_windows
                            painter.fillRect(sx, 0, ex - sx, self.height(), tns_brush)
                    win_idx += 1

        pen_major = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 1)
        pen_minor = QtGui.QPen(QtGui.QBrush(QtGui.QColor(192, 192, 192)), 1)
        
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
        for p in range(7):
            painter.setPen(pen_major)
            h = self.height() * p / 14
            h2 = self.height() / 2
            painter.drawLine(0, h2 + h, self.width(), h2 + h)
            painter.drawLine(0, h2 - h, self.width(), h2 - h)

            painter.setPen(pen_minor)
            x = 10 ** p
            for i in range(2, 10, 2):
                h = self.height() * math.log(x * i, 10) / 14
                painter.drawLine(0, h2 + h, self.width(), h2 + h)
                painter.drawLine(0, h2 - h, self.width(), h2 - h)

        for i in range(0, 1024, 16):
            if i % 64 == 0:
                painter.setPen(pen_major)
            else:
                painter.setPen(pen_minor)

            w = self.width() * i / 1024
            painter.drawLine(w, 0, w, self.height())

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)

        prev = None
        win_idx = 0
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                painter.setPen(pen)
                for i in range(ics.params.window_length):
                    s = self.aac.tns_spec[self.channel][g][win][i]
                    x = self.width() * (win_idx + i / ics.params.window_length) / ics.params.num_windows
                    sign = 1 if s > 0 else -1
                    y = self.height() * (1 - sign * math.log(1 + abs(s), 10) / 7) / 2
                    if prev:
                        (prev_x, prev_y) = prev
                        painter.drawLine(prev_x, prev_y, x, y)
                    prev = (x, y)

                prev = None
                win_idx += 1
                if win_idx < ics.params.num_windows:
                    painter.setPen(window_pen)
                    x = self.width() * win_idx / ics.params.num_windows
                    painter.drawLine(x, 0, x, self.height())

        painter.end()

class AACRawSamplesPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACRawSamplesPlot, self).__init__()
        self.channel = channel
        self.aac = None

    def set_aac(self, aac):
        self.aac = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]
      
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)

        border_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)

        prev = None
        win_idx = 0
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                samples = self.aac.samples[self.channel][g][win]
                if samples is None:
                    continue

                painter.setPen(pen)
                for i in range(ics.params.window_length * 2):
                    s = samples[i]
                    x = self.width() * (win_idx + i / (ics.params.window_length * 2)) / ics.params.num_windows
                    y = self.height() * (1 - s / 32767) / 2
                    if prev:
                        (prev_x, prev_y) = prev
                        painter.drawLine(prev_x, prev_y, x, y)
                    prev = (x, y)

                prev = None
                win_idx += 1
                if win_idx < ics.params.num_windows:
                    painter.setPen(border_pen)
                    x = self.width() * win_idx / ics.params.num_windows
                    painter.drawLine(x, 0, x, self.height())

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 1)
        painter.setPen(window_pen)
        prev = None

        for i in range(0, self.width(), 10):
            n = i * 2048 / self.width() % (ics.params.window_length * 2)
            w = self.aac.window(ics.ics_info.window_shape, ics.ics_info.window_sequence, n)

            x = i
            y = self.height() * (1 - w)
            if prev:
                (prev_x, prev_y) = prev
                painter.drawLine(prev_x, prev_y, x, y)
            prev = (x, y)

        painter.end()

class AACFinalSamplesPlot(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACFinalSamplesPlot, self).__init__()
        self.channel = channel
        self.aac = None
        self.prev_aac = None

    def set_aac(self, aac):
        (self.aac, self.prev_aac) = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]
      
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)

        prev = None
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        samples = self.aac.windowed_samples[self.channel]
        if self.prev_aac:
            prev_samples = self.prev_aac.windowed_samples[self.channel]
        else:
            prev_samples = [0] * 2048

        if samples is not None:
            painter.setPen(pen)
            for i in range(1024):
                s = samples[i] + prev_samples[1024 + i]
                x = self.width() * i / 1024
                y = self.height() * (1 - s / 32767) / 2
                if prev:
                    (prev_x, prev_y) = prev
                    painter.drawLine(prev_x, prev_y, x, y)
                prev = (x, y)

        painter.end()

class AACPerChannelView(QtWidgets.QScrollArea):
    def __init__(self, cls):
        super(AACPerChannelView, self).__init__()

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

    def set_aac(self, aac):
        for plot in self.spectrum_plots:
            plot.set_aac(aac)

    def resizeEvent(self, event):
        self.widget.setFixedSize(event.size().width(), event.size().width())

class AACStreamView(QtWidgets.QWidget):
    def __init__(self, file):
        super(AACStreamView, self).__init__()
        self.title = 'AAC Streams'
        self.file = file

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.file.numsamples())
        self.spinbox.valueChanged.connect(self.spinbox_changed)
        hlayout.addWidget(self.spinbox)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        tabs = QtWidgets.QTabWidget()
        self.syntax_view = SyntaxView('Syntax')
        tabs.addTab(self.syntax_view, self.syntax_view.title)
        self.spec_sf_view = AACPerChannelView(AACSpectrumScalefactorPlot)
        tabs.addTab(self.spec_sf_view, 'Raw Spectrum/Scalefactors')
        self.rescaled_spectrum_view = AACPerChannelView(AACRescaledSpectrumPlot)
        tabs.addTab(self.rescaled_spectrum_view, 'Rescaled Spectrum')
        self.spectrum_view = AACPerChannelView(AACSpectrumPlot)
        tabs.addTab(self.spectrum_view, 'Spectrum')
        self.tns_spectrum_view = AACPerChannelView(AACTnsSpectrumPlot)
        tabs.addTab(self.tns_spectrum_view, 'TNS Spectrum')
        self.raw_samples_view = AACPerChannelView(AACRawSamplesPlot)
        tabs.addTab(self.raw_samples_view, 'Raw Samples')
        self.final_samples_view = AACPerChannelView(AACFinalSamplesPlot)
        tabs.addTab(self.final_samples_view, 'Final Samples')

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.spinbox_changed(0)

    def spinbox_changed(self, value):
        (bytes, location) = self.file.getsample(value)
        self.aac = AAC()
        self.aac.parse(bytes, location, self.file.es_descriptor())

        if value > 0:
            (bytes, location) = self.file.getsample(value - 1)
            self.prev_aac = AAC()
            self.prev_aac.parse(bytes, location, self.file.es_descriptor())
        else:
            self.prev_aac = None

        self.syntax_view.update_syntax(self.file.bytestream, self.aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        self.spec_sf_view.set_aac(self.aac)
        self.rescaled_spectrum_view.set_aac(self.aac)
        self.spectrum_view.set_aac(self.aac)
        self.tns_spectrum_view.set_aac(self.aac)
        self.raw_samples_view.set_aac(self.aac)
        self.final_samples_view.set_aac((self.aac, self.prev_aac))

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        views = []
        views.append(SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(AACStreamView(self.file))
        return views