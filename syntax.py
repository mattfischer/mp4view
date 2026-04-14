from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Qt

from hexdump import HexDumpView

class SyntaxItem:
    def __init__(self, name, start, size, children=[], analyzer=None):
        self.name = name
        self.start = start
        self.size = size
        self.children = children
        self.parent = None
        self.analyzer = analyzer
        for child in self.children:
            child.parent = self

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

class SyntaxTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, syntax_items):
        super(SyntaxTreeModel, self).__init__()
        self.items = syntax_items

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            item = parent.internalPointer()
            if self.canFetchMore(parent):
                return 1
            else:
                return len(item.children)
        else:
            return len(self.items)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def parent(self, index):
        item = index.internalPointer()
        if item.parent:
            return self.createIndex(item.parent.row(), 0, item.parent)
        else:
            return QtCore.QModelIndex()

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if parent.isValid():
            parent_item = parent.internalPointer()
            if row < len(parent_item.children):
                return self.createIndex(row, column, parent_item.children[row])
        else:
            if row < len(self.items):
                return self.createIndex(row, column, self.items[row])

        return QtCore.QModelIndex()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            item = index.internalPointer()
            return item.name
        return None

    def canFetchMore(self, parent):
        item = parent.internalPointer()
        return (item is not None) and (item.analyzer is not None)

    def fetchMore(self, parent):
        item = parent.internalPointer()
        item.children = item.analyzer.analyze()
        for child in item.children:
            child.parent = item
        item.analyzer = None

class SyntaxView(QtWidgets.QWidget):
    def __init__(self, title, stream=None, syntax_items=[], parent=None):
        super(SyntaxView, self).__init__(parent)
        self.title = title

        layout = QtWidgets.QHBoxLayout()

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.clicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree_view, 1)

        self.hexdump_view = HexDumpView()
        layout.addWidget(self.hexdump_view)

        self.setLayout(layout)

        self.update_syntax(stream, syntax_items)
    
    def update_syntax(self, stream, syntax_items):
        self.model = SyntaxTreeModel(syntax_items)
        self.tree_view.setModel(self.model)
        self.hexdump_view.update_stream(stream)

    def on_item_clicked(self, index):
        item = index.internalPointer()
        self.hexdump_view.set_highlight(item.start, item.start + item.size)
        self.hexdump_view.ensure_visible(item.start)

def format_fixed16(value):
    return float(value) / 65536

def format_fixed8(value):
    return float(value) / 256

class format_enum:
    def __init__(self, values):
        self.values = values

    def __call__(self, value):
        if value in self.values:
            return '%i (%s)' % (value, self.values[value])
        else:
            return '%i' % value
