import sys
import os
import os.path

from PySide2 import QtWidgets

from stream import Bytestream
import analyzers.mp4

class App(QtWidgets.QApplication):
    def __init__(self, args):
        super(App, self).__init__(args)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setWindowTitle('MP4 Viewer')
        self.main_window.setMinimumSize(1024, 768)

        self.tab_widget = QtWidgets.QTabWidget()
        self.main_window.setCentralWidget(self.tab_widget)

        menu_bar = QtWidgets.QMenuBar()
        file_menu = menu_bar.addMenu('&File')
        open_action = QtWidgets.QAction('&Open', self)
        open_action.triggered.connect(self.on_file_open)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QtWidgets.QAction('&Exit', self)
        exit_action.triggered.connect(self.on_file_exit)
        file_menu.addAction(exit_action)
        self.main_window.setMenuBar(menu_bar)
        self.main_window.show()

        if len(args) > 1:
            filename = args[1]
            if os.path.exists(filename):
                self.load_file(filename)

    def on_file_open(self):
        (filename, selected_filter) = QtWidgets.QFileDialog.getOpenFileName(self.main_window, 'Open File', filter='Media Files (*.m4a);;All Files (*)')
        if filename and os.path.exists(filename):
            self.load_file(filename)

    def on_file_exit(self):
        self.quit()

    def load_file(self, filename):
        file = open(filename, 'rb')
        self.stream = Bytestream(file)

        analyzer = analyzers.mp4.Analyzer(self.stream)
        self.tab_widget.clear()
        for view in analyzer.get_views():
            self.tab_widget.addTab(view, view.title)

if __name__ == "__main__":
    app = App(sys.argv)
    app.exec_()
