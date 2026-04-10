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

        self.highlight = (-1, -1)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self.viewport())
        painter.setFont(self.font)

        num_lines = self.height() // self.line_spacing + 2
        line = self.verticalScrollBar().value() // self.line_spacing
        start = self.verticalScrollBar().value() - line * self.line_spacing

        (highlight_start, highlight_end) = self.highlight
        if highlight_start != -1:
            brush = QtGui.QBrush(QtGui.QColor(192, 192, 192))
            highlight_start_line = highlight_start // 16
            highlight_start_char = highlight_start % 16
            highlight_end_line = highlight_end // 16
            highlight_end_char = highlight_end % 16

            if highlight_end_line >= line and highlight_start_line < line + num_lines:
                if highlight_start_line == highlight_end_line:
                    if highlight_start_line >= line and highlight_start_line <= line + num_lines:
                        painter.fillRect(20 + highlight_start_char * self.advance, (highlight_start_line - line) * self.line_spacing - start + 5, (highlight_end_char - highlight_start_char) * self.advance, self.line_spacing, brush)
                else:
                    if highlight_start_line >= line:
                        painter.fillRect(20 + highlight_start_char * self.advance, (highlight_start_line - line) * self.line_spacing - start + 5, (16 - highlight_start_char) * self.advance, self.line_spacing, brush)
                    if highlight_end_line <= line + num_lines:
                        painter.fillRect(20, (highlight_end_line - line) * self.line_spacing - start + 5, highlight_end_char * self.advance, self.line_spacing, brush)
                fill_start_line = max(highlight_start_line + 1, line)
                fill_end_line = min(highlight_end_line - 1, line + num_lines)
                if fill_end_line >= fill_start_line:
                    painter.fillRect(20, fill_start_line * self.line_spacing - start + 5, 16 * self.advance, (fill_end_line - fill_start_line + 1) * self.line_spacing, brush)
                
        self.file.seek(line * 16)
        for i in range(num_lines):
            bytes = self.file.read(16)
            for j in range(16):
                if len(bytes) > j:
                    painter.drawText(20 + j * self.advance, i * self.line_spacing - start, '%02x' % int(bytes[j]))
        painter.end()

    def setHighlight(self, start, end):
        self.highlight = (start, end)
        self.viewport().update()