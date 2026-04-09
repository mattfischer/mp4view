from PySide2 import QtCore
from PySide2.QtCore import Qt

class TreeItem:
    def __init__(self, name, children):
        self.name = name
        self.children = children
        self.parent = None
        for child in self.children:
            child.parent = self

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self):
        super(TreeModel, self).__init__()
        sub_items = [TreeItem('Subitem 1', []), TreeItem('Subitem 2', [])]
        self.items = [TreeItem('Item 1', sub_items), TreeItem('Item 2', [])]

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            item = parent.internalPointer()
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

