import math

from .file import File
from .aac import AAC

from syntax import SyntaxView

from PySide2 import QtWidgets, QtGui

class AACSpectrumPlot(QtWidgets.QWidget):
    def __init__(self):
        super(AACSpectrumPlot, self).__init__()
        self.spectrum_data = []
        self.ics = None

    def set_spectrum(self, spectrum_data, ics):
        self.spectrum_data = spectrum_data
        self.ics = ics
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

        for p in range(5):
            painter.setPen(pen_major)
            w = self.width() * p / 5
            painter.drawLine(w, 0, w, self.height())

            painter.setPen(pen_minor)
            x = 10 ** p
            for i in range(2, 10):
                w = self.width() * math.log(x * i, 10) / 5
                painter.drawLine(w, 0, w, self.height())

        brush = QtGui.QBrush(QtGui.QColor(192, 192, 192))
        for sfb in range(self.ics.ics_info.max_sfb):
            start = self.ics.params.swb_offset[sfb]
            end = self.ics.params.swb_offset[sfb+1]
            val = self.ics.scale_factor_data.sf[0][sfb]

            sx = self.width() * math.log(1 + 44 * start, 10) / 5
            ex = self.width() * math.log(1 + 44 * end, 10) / 5
            w = ex - sx - 1
            h = self.height() * val/256
            painter.fillRect(sx, self.height() - h, w, h, brush)

        prev = None
        num = len(self.spectrum_data[0][0])
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 1)
        painter.setPen(pen)
        for i in range(num):
            x = self.width() * math.log(1 + 44 * i, 10) / 5
            s = self.spectrum_data[0][0][i]
            sign = 1 if s > 0 else -1
            y = self.height() * (1 - sign * math.log(1 + abs(s), 10) / 7) / 2
            if prev:
                (prev_x, prev_y) = prev
                painter.drawLine(prev_x, prev_y, x, y)
            prev = (x, y) 
        painter.end()

class AACSpectrumView(QtWidgets.QScrollArea):
    def __init__(self):
        super(AACSpectrumView, self).__init__()

        self.widget = QtWidgets.QWidget()
        self.spectrum_plots = []
        layout = QtWidgets.QVBoxLayout()
        for i in range(2):
            plot = AACSpectrumPlot()
            layout.addWidget(plot)
            self.spectrum_plots.append(plot)
        self.widget.setLayout(layout)
        self.widget.setMinimumSize(500, 500)
        self.setWidget(self.widget)

    def set_spectrum(self, spectrum_data, ics):
        for i in range(2):
            self.spectrum_plots[i].set_spectrum(spectrum_data[i], ics[i])

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
        self.spectrum_view = AACSpectrumView()
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

        self.spectrum_view.set_spectrum(self.aac.spec, self.aac.block.cpe.ics)

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        views = []
        views.append(SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(AACStreamView(self.file))
        return views