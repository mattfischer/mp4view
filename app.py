import sys

from PySide2 import QtWidgets

from hexdump import HexDumpView
from syntax import SyntaxAnalyzerView, SyntaxItem
from stream import Bytestream
from analyzers.mp4.file import File

class Analyzer():
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        return self.file.analyze()

class App(QtWidgets.QApplication):
    def __init__(self, args):
        super(App, self).__init__(args)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setMinimumSize(1024, 768)

        file = open('test.m4a', 'rb')
        self.stream = Bytestream(file)

        analyzer = Analyzer(self.stream)
        self.analyzer_view = SyntaxAnalyzerView(analyzer)
        self.main_window.setCentralWidget(self.analyzer_view)
        self.main_window.show()

if __name__ == "__main__":
    app = App(sys.argv)
    app.exec_()
