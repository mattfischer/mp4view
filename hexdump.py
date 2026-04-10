import os.path
from PySide2 import QtGui, QtWidgets

class HexDumpView(QtWidgets.QAbstractScrollArea):
    def __init__(self, filename):
        super(HexDumpView, self).__init__()
        self.font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        metrics = QtGui.QFontMetrics(self.font)
        self.advance = metrics.horizontalAdvance('xx ')
        self.line_spacing = metrics.lineSpacing()
        self.setMinimumWidth(16*self.advance + 60)

        self.file = open(filename, 'rb')
        size = os.path.getsize(filename)
        num_lines = size / 16
        self.verticalScrollBar().setRange(0, num_lines * self.line_spacing)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self.viewport())
        painter.setFont(self.font)

        num_lines = self.height() // self.line_spacing + 2
        line = self.verticalScrollBar().value() // self.line_spacing
        start = self.verticalScrollBar().value() - line * self.line_spacing
        self.file.seek(line * 16)
        for i in range(num_lines):
            bytes = self.file.read(16)
            for j in range(16):
                if len(bytes) > j:
                    painter.drawText(20 + j * self.advance, i * self.line_spacing - start, '%02x' % int(bytes[j]))
        painter.end()
