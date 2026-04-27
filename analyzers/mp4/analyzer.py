from .file import File

import analyzers.aac
import syntax

from PySide2 import QtWidgets, QtGui, QtCore

class StreamView(QtWidgets.QWidget):
    def __init__(self, file):
        super(StreamView, self).__init__()
        self.title = 'AAC Streams'
        self.file = file
        self.aac_analyzer = analyzers.aac.Analyzer(file)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.file.numsamples())
        self.spinbox.valueChanged.connect(self.spinbox_changed)
        hlayout.addWidget(self.spinbox)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        tabs = QtWidgets.QTabWidget()
        for view in self.aac_analyzer.get_views():
            tabs.addTab(view, view.title)

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.spinbox_changed(0)

    def spinbox_changed(self, value):
        self.aac_analyzer.set_sample(value)

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def get_views(self):
        views = []
        views.append(syntax.SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(StreamView(self.file))
        return views