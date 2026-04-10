import sys

from PySide2 import QtWidgets

from hexdump import HexDumpView
from syntax import SyntaxAnalyzerView, SyntaxItem

class Analyzer():
    def analyze(self):
        return [SyntaxItem('Foo %i' % i) for i in range(100)]

class App(QtWidgets.QApplication):
    def __init__(self, args):
        super(App, self).__init__(args)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setMinimumSize(1024, 768)

        analyzer = Analyzer()
        self.analyzer_view = SyntaxAnalyzerView(analyzer)
        self.main_window.setCentralWidget(self.analyzer_view)
        self.main_window.show()

if __name__ == "__main__":
    app = App(sys.argv)
    app.exec_()
