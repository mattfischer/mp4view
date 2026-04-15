import math

from .file import File
from .aac import AAC, INTENSITY_HCB, INTENSITY_HCB2

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

        ics = self.aac.block.cpe.ics[self.channel]

        prev = None
        regular_brush = QtGui.QBrush(QtGui.QColor(192, 192, 192))
        intensity_brush = QtGui.QBrush(QtGui.QColor(192, 192, 0))
        
        ms_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        lr_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 224, 176)), 2)
    
        for sfb in range(ics.ics_info.max_sfb):
            start = ics.params.swb_offset[sfb]
            end = ics.params.swb_offset[sfb+1]
            val = ics.scale_factor_data.sf[0][sfb]

            sx = self.width() * start / ics.params.window_length
            ex = self.width() * end / ics.params.window_length
            w = ex - sx - 1
            h = self.height() * val/256

            if ics.section_data.sfb_cb[0][sfb] in (INTENSITY_HCB, INTENSITY_HCB2):
                brush = intensity_brush
            else:
                brush = regular_brush

            painter.fillRect(sx, self.height() - h, w, h, brush)

            ms_used = (self.aac.block.cpe.ms_mask_present == 2 or 
                       (self.aac.block.cpe.ms_mask_present == 1 and self.aac.block.cpe.ms_used[0][sfb]))

            if ms_used:
                painter.setPen(ms_pen)
            else:
                painter.setPen(lr_pen)

            for bin in range(start, end):
                s = ics.spectral_data.spec[0][0][sfb][bin - start]
                x = self.width() * bin / ics.params.window_length
                y = self.height() * (1 + s / 32) / 2
                if prev:
                    (prev_x, prev_y) = prev
                    painter.drawLine(prev_x, prev_y, x, y)
                prev = (x, y)

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

        for i in range(0, 512, 16):
            if i % 64 == 0:
                painter.setPen(pen_major)
            else:
                painter.setPen(pen_minor)

            w = self.width() * i / 512
            painter.drawLine(w, 0, w, self.height())

        ics = self.aac.block.cpe.ics[self.channel]

        spectrum_data = self.aac.spec[self.channel]

        prev = None
        num = len(spectrum_data[0][0])
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 1)
        painter.setPen(pen)
        for i in range(num):
            x = self.width() * i / num
            s = spectrum_data[0][0][i]
            sign = 1 if s > 0 else -1
            y = self.height() * (1 - sign * math.log(1 + abs(s), 10) / 7) / 2
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
        self.spectrum_view = AACPerChannelView(AACSpectrumPlot)
        tabs.addTab(self.spectrum_view, 'Spectrum')

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.spinbox_changed(0)

    def spinbox_changed(self, value):
        (bytes, location) = self.file.getsample(value)
        self.aac = AAC()
        self.aac.parse(bytes, location, self.file.es_descriptor())

        self.syntax_view.update_syntax(self.file.bytestream, self.aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        self.spec_sf_view.set_aac(self.aac)
        self.spectrum_view.set_aac(self.aac)

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        views = []
        views.append(SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(AACStreamView(self.file))
        return views