import sys

from PySide2 import QtWidgets

from stream import Bytestream
import analyzers.mp4

class App(QtWidgets.QApplication):
    def __init__(self, args):
        super(App, self).__init__(args)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setMinimumSize(1024, 768)

        file = open('test.m4a', 'rb')
        self.stream = Bytestream(file)

        self.tab_widget = QtWidgets.QTabWidget()
        analyzer = analyzers.mp4.Analyzer(self.stream)
        for view in analyzer.analyze():
            self.tab_widget.addTab(view, view.title)
        self.main_window.setCentralWidget(self.tab_widget)
        self.main_window.show()

if __name__ == "__main__":
    app = App(sys.argv)
    app.exec_()
