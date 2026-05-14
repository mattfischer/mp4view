from PySide2 import QtWidgets, QtCore

from . import parse

import syntax

class Analyzer:
    def __init__(self, track):
        self.track = track
        self.syntax_view = syntax.SyntaxView('Syntax')

    def get_views(self):
        return [self.syntax_view]

    def set_sample(self, sample):
        (bytes, location) = self.track.getsample(sample)

        nalu = parse.NALU()
        nalu.parse(bytes, location, self.track.avc_configuration())
        self.syntax_view.update_syntax(self.track.bytestream, [nalu.syntax_item])
        self.syntax_view.set_highlight(location, len(bytes))

class StreamView(QtWidgets.QWidget):
    def __init__(self, track, title):
        super(StreamView, self).__init__()
        self.title = title
        self.track = track
        self.avc_analyzer = Analyzer(track)
        self.selected_sample = 0

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.track.numsamples())
        self.spinbox.valueChanged.connect(self.on_spinbox_changed)
        hlayout.addWidget(self.spinbox)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        tabs = QtWidgets.QTabWidget()
        for view in self.avc_analyzer.get_views():
            tabs.addTab(view, view.title)

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.on_spinbox_changed(0)

    def on_selected_sample_changed(self, value):
        if self.spinbox.value() != value:
            self.spinbox.setValue(value)

    def on_spinbox_changed(self, value):
        self.selected_sample = value
        self.avc_analyzer.set_sample(value)
