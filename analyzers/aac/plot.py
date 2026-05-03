import math

from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

class AxisLinearUnsigned:
    def __init__(self, range):
        self.range = range
        self.is_log = False
        self.is_signed = False

    def map(self, value):
        return value / self.range

class AxisLinearSigned:
    def __init__(self, range):
        self.range = range
        self.is_log = False
        self.is_signed = True

    def map(self, value):
        return (1 + value / self.range) / 2

class AxisLogarithmicUnsigned:
    def __init__(self, decades):
        self.decades = decades
        self.is_log = True
        self.is_signed = False

    def map(self, value):
        return math.log(1 + value, 10) / self.decades

class AxisLogarithmicSigned:
    def __init__(self, decades):
        self.decades = decades
        self.is_log = True
        self.is_signed = True

    def map(self, value):
        sign = 1 if value > 0 else -1
        return (1 + sign * math.log(1 + abs(value), 10) / self.decades) / 2

class PlotAxes:
    def __init__(self, horizontal, vertical):
        self.horizontal = horizontal
        self.vertical = vertical
    
    def draw(self, painter, rect):
        pen_major = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 1)
        pen_minor = QtGui.QPen(QtGui.QBrush(QtGui.QColor(192, 192, 192)), 1)
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        
        for (info, is_vertical) in ((self.horizontal, False), (self.vertical, True)):
            (axis, major_divisions, minor_divisions) = info
            def draw_line(value):
                v = axis.map(value)
                if is_vertical:
                    y = rect.bottom() - v * rect.height()
                    painter.drawLine(rect.left(), y, rect.right(), y)
                else:
                    x = rect.left() + v * rect.width()
                    painter.drawLine(x, rect.top(), x, rect.bottom())
                
            if axis.is_log:
                scale = 1
                for d in range(axis.decades):
                    if scale != 1:
                        painter.setPen(pen_major)
                        draw_line(scale)
                        if axis.is_signed:
                            draw_line(-scale)

                    painter.setPen(pen_minor)
                    for i in range(minor_divisions):
                        v = scale * ((i + 1) * 10 / minor_divisions)
                        draw_line(v)
                        if axis.is_signed:
                            draw_line(-v)
                    scale *= 10
            else:
                num_minor = minor_divisions * major_divisions
                for i in range(1, num_minor):
                    if i % minor_divisions == 0:
                        painter.setPen(pen_major)
                    else:
                        painter.setPen(pen_minor)
                
                    draw_line(i * axis.range / num_minor)
                    if axis.is_signed:
                        draw_line(-i * axis.range / num_minor)

            if axis.is_signed:
                painter.setPen(pen_center)
                draw_line(0)

    def try_hover(self, rect, x, y):
        return False

    def release_hover(self):
        pass

class PlotLine:
    def __init__(self, horizontal_axis, vertical_axis, width, colors, points, point_caption=None):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.width = width
        self.colors = colors
        self.points = points
        self.point_caption = point_caption
        self.hover_point = -1

    def draw(self, painter, rect):
        pens = [QtGui.QPen(QtGui.QColor(r, g, b), self.width) for (r, g, b) in self.colors]
        prev = None
        for (color, point_x, point_y, caption) in self.points:
            x = rect.left() + rect.width() * self.horizontal_axis.map(point_x)
            y = rect.bottom() - rect.height() * self.vertical_axis.map(point_y)
            if prev is not None:
                (prev_x, prev_y) = prev
                if self.hover_point == -1:
                    pens[color].setWidth(self.width)
                else:
                    pens[color].setWidth(self.width * 2)
                painter.setPen(pens[color])
                painter.drawLine(prev_x, prev_y, x, y)
            prev = (x, y)

        if self.hover_point != -1:
            (color, point_x, point_y, caption) = self.points[self.hover_point]
            x = rect.left() + rect.width() * self.horizontal_axis.map(point_x)
            y = rect.bottom() - rect.height() * self.vertical_axis.map(point_y)

            brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawEllipse(x - 5, y - 5, 10, 10)

            if caption:
                pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
                painter.setPen(pen)
                painter.drawText(rect.x(), rect.bottom() - 10, caption)

    def try_hover(self, rect, hover_x, hover_y):
        start = -1
        end = -1
        for (i, (color, point_x, point_y, caption)) in enumerate(self.points):
            x = rect.left() + rect.width() * self.horizontal_axis.map(point_x)
            y = rect.bottom() - rect.height() * self.vertical_axis.map(point_y)
            
            if x > hover_x - 10 and x < hover_x + 10:
                if start == -1:
                    start = i
                    min_y = max_y = y
                else:
                    end = i
                    max_y = max(max_y, y)
                    min_y = min(min_y, y)

        if hover_y > min_y - 10 and hover_y < max_y + 10:
            self.hover_point = (start + end) // 2
            return True

        self.hover_point = -1
        return False

    def release_hover(self):
        self.hover_point = -1

class PlotBar:
    def __init__(self, horizontal_axis, vertical_axis, colors, bars):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.colors = colors
        self.bars = bars
        self.hover_bar = -1

    def draw(self, painter, rect):
        brushes = [QtGui.QBrush(QtGui.QColor(r, g, b)) for (r, g, b) in self.colors]
        p = 0
        for (i, (color, width, height, caption)) in enumerate(self.bars):
            sx = rect.left() + rect.width() * self.horizontal_axis.map(p)
            sy = rect.bottom() - rect.height() * self.vertical_axis.map(0)
            ex = rect.left() + rect.width() * self.horizontal_axis.map(p + width)
            ey = rect.bottom() - rect.height() * self.vertical_axis.map(height)

            (x, w) = (sx, ex - sx) if ex > sx else (ex, sx - ex)
            (y, h) = (sy, ey - sy) if ey > sy else (ey, sy - ey)

            painter.fillRect(x, y, w - 1, h, brushes[color])
            if i == self.hover_bar:
                pen = QtGui.QPen(brushes[color].color().darker(), 3)
                painter.setPen(pen)
                painter.drawRect(x, y, w - 1, h)

            p += width

        if self.hover_bar != -1:
            (color, width, height, caption) = self.bars[self.hover_bar]
            if caption:
                pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
                painter.setPen(pen)
                painter.drawText(rect.x(), rect.bottom() - 10, caption)

    def try_hover(self, rect, hover_x, hover_y):
        p = 0
        for (i, (color, width, height, caption)) in enumerate(self.bars):
            sx = rect.left() + rect.width() * self.horizontal_axis.map(p)
            sy = rect.bottom() - rect.height() * self.vertical_axis.map(0)
            ex = rect.left() + rect.width() * self.horizontal_axis.map(p + width)
            ey = rect.bottom() - rect.height() * self.vertical_axis.map(height)

            (x, w) = (sx, ex - sx) if ex > sx else (ex, sx - ex)
            (y, h) = (sy, ey - sy) if ey > sy else (ey, sy - ey)

            if x < hover_x and x + w > hover_x and y < hover_y and y + h > hover_y:
                self.hover_bar = i
                return True
            p += width

        self.hover_bar = -1
        return False

    def release_hover(self):
        self.hover_bar = -1

class PlotView(QtWidgets.QWidget):
    def __init__(self):
        super(PlotView, self).__init__()
        self.setMouseTracking(True)
        self.set_num_windows(1)

    def reset(self):
        self.set_num_windows(self.num_windows)

    def add_plot(self, window, plot):
        self.plots[window].append(plot)

    def set_num_windows(self, num_windows):
        self.num_windows = num_windows
        self.plots = [[] for i in range(num_windows)]
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        for (i, window_plots) in enumerate(self.plots):
            rect = QtCore.QRect(self.width() * i / self.num_windows, 0, self.width() / self.num_windows, self.height())
            for plot in window_plots:
                plot.draw(painter, rect)

        window_pen = QtGui.QPen(QtGui.QColor(128, 128, 128), 8)
        painter.setPen(window_pen)
        for i in range(1, self.num_windows):
            x = self.width() * i / self.num_windows - 8
            painter.drawLine(x, 0, x, self.height())

        edge_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
        painter.setPen(edge_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        painter.end()

    def mouseMoveEvent(self, event):
        hover_caught = False
        for (i, window_plots) in enumerate(self.plots):
            rect = QtCore.QRect(self.width() * i / self.num_windows, 0, self.width() / self.num_windows, self.height())
            if rect.contains(event.localPos().x(), event.localPos().y()):
                for plot in reversed(window_plots):
                    if hover_caught:
                        plot.release_hover()
                    elif plot.try_hover(rect, event.localPos().x(), event.localPos().y()):
                        hover_caught = True
            else:
                for plot in window_plots:
                    plot.release_hover()

        self.update()

    def leaveEvent(self, event):
        for window_plots in self.plots:
            for plot in window_plots:
                plot.release_hover()
        self.update()
