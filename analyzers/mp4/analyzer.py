import io

from .file import File
from .aac import AAC

from syntax import SyntaxView

from PySide2 import QtWidgets, QtGui

class AACSpectrumPlot(QtWidgets.QWidget):
    def __init__(self):
        super(AACSpectrumPlot, self).__init__()
        self.spectrum_data = []

    def set_spectrum(self, spectrum_data):
        self.spectrum_data = spectrum_data
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        prev = None
        num = len(self.spectrum_data[0][0])
        for i in range(num):
            (x, y) = (self.width() * i / num, self.height() / 2 + self.height() * self.spectrum_data[0][0][i] / (65536 * 2 * 3.14))
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

    def set_spectrum(self, spectrum_data):
        for i in range(2):
            self.spectrum_plots[i].set_spectrum(spectrum_data[i])

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

        self.spectrum_view.set_spectrum(self.aac.spec)

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        views = []
        views.append(SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(AACStreamView(self.file))
        return views