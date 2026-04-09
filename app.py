import sys

from PySide2 import QtWidgets

from hexdump import HexDumpView
from treeview import TreeModel

class App(QtWidgets.QApplication):
    def __init__(self, args):
        super(App, self).__init__(args)

        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setMinimumSize(1024, 768)

        layout = QtWidgets.QHBoxLayout()

        self.tree_view = QtWidgets.QTreeView()
        self.tree_model = TreeModel()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(True)
        layout.addWidget(self.tree_view)

        self.hex_dump_view = HexDumpView('app.py')
        layout.addWidget(self.hex_dump_view)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)

        self.main_window.setCentralWidget(central_widget)
        self.main_window.show()

if __name__ == "__main__":
    app = App(sys.argv)
    app.exec_()
