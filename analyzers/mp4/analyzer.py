import math

from .file import File
from .aac import AAC, INTENSITY_HCB, INTENSITY_HCB2
from .aac import ONLY_LONG_SEQUENCE, LONG_START_SEQUENCE, EIGHT_SHORT_SEQUENCE, LONG_STOP_SEQUENCE

from syntax import SyntaxView

from PySide2 import QtWidgets, QtGui, QtCore

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

class PlotLine:
    def __init__(self, horizontal_axis, vertical_axis, width, colors, points):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.width = width
        self.colors = colors
        self.points = points

    def draw(self, painter, rect):
        pens = [QtGui.QPen(QtGui.QColor(r, g, b), self.width) for (r, g, b) in self.colors]
        prev = None
        for (color, point_x, point_y) in self.points:
            x = rect.left() + rect.width() * self.horizontal_axis.map(point_x)
            y = rect.bottom() - rect.height() * self.vertical_axis.map(point_y)
            if prev is not None:
                (prev_x, prev_y) = prev
                painter.setPen(pens[color])
                painter.drawLine(prev_x, prev_y, x, y)
            prev = (x, y)

class PlotBar:
    def __init__(self, horizontal_axis, vertical_axis, colors, bars):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.colors = colors
        self.bars = bars

    def draw(self, painter, rect):
        brushes = [QtGui.QBrush(QtGui.QColor(r, g, b)) for (r, g, b) in self.colors]
        p = 0
        for (color, width, height) in self.bars:
            sx = rect.left() + rect.width() * self.horizontal_axis.map(p)
            sy = rect.bottom() - rect.height() * self.vertical_axis.map(0)
            ex = rect.left() + rect.width() * self.horizontal_axis.map(p + width)
            ey = rect.bottom() - rect.height() * self.vertical_axis.map(height)

            (x, w) = (sx, ex - sx) if ex > sx else (ex, sx - ex)
            (y, h) = (sy, ey - sy) if ey > sy else (ey, sy - ey)

            painter.fillRect(x, y, w - 1, h, brushes[color])
            p += width

class AACPlotView(QtWidgets.QWidget):
    def __init__(self):
        super(AACPlotView, self).__init__()
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
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        for (i, window_plots) in enumerate(self.plots):
            rect = QtCore.QRect(self.width() * i / self.num_windows, 0, self.width() / self.num_windows, self.height())
            for plot in window_plots:
                plot.draw(painter, rect)

        window_pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 128, 128)), 8)
        painter.setPen(window_pen)
        for i in range(1, self.num_windows):
            x = self.width() * i / self.num_windows
            painter.drawLine(x, 0, x, self.height())

        painter.end()

class AACSpectrumScalefactorPlot(AACPlotView):
    def __init__(self, channel):
        super(AACSpectrumScalefactorPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = AxisLinearUnsigned(ics.params.window_length)
        v_axis_scalefactor = AxisLinearUnsigned(128)
        v_axis_spectrum = AxisLinearSigned(32) 
        win_idx = 0
        scalefactor_colors = [(192, 192, 192), (192, 192, 0)]
        spectrum_colors = [(128, 176, 224), (128, 224, 176)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                scalefactor_bars = []
                spectrum_points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]
                    val = ics.scale_factor_data.sf[g][sfb] - 100
                    is_intensity = ics.section_data.sfb_cb[g][sfb] in (INTENSITY_HCB, INTENSITY_HCB2)
                    color = 1 if is_intensity else 0
                    scalefactor_bars.append((color, end - start, val))

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 0
                    for bin in range(start, end):
                        value = ics.spectral_data.spec[g][win][sfb][bin - start]
                        spectrum_points.append((color, bin, value))

                self.add_plot(win_idx, PlotBar(h_axis, v_axis_scalefactor, scalefactor_colors, scalefactor_bars))
                self.add_plot(win_idx, PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class AACRescaledSpectrumPlot(AACPlotView):
    def __init__(self, channel):
        super(AACRescaledSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = AxisLinearUnsigned(ics.params.window_length)
        v_axis = AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [(128, 176, 224), (128, 224, 176)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 0
                    for bin in range(start, end):
                        value = aac.x_rescal[self.channel][g][win][sfb][bin - start]
                        points.append((color, bin, value))

                self.add_plot(win_idx, PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class AACSpectrumPlot(AACPlotView):
    def __init__(self, channel):
        super(AACSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = AxisLinearUnsigned(ics.params.window_length)
        v_axis = AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [(128, 176, 224)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for i in range(ics.params.window_length):
                    value = aac.spec[self.channel][g][win][i]
                    points.append((0, i, value))

                self.add_plot(win_idx, PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class AACTnsSpectrumPlot(AACPlotView):
    def __init__(self, channel):
        super(AACTnsSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        if not hasattr(ics, 'tns_data'):
            return

        h_axis = AxisLinearUnsigned(ics.params.window_length)
        v_axis_spectrum = AxisLogarithmicSigned(7)
        v_axis_tns = AxisLinearUnsigned(1) 
        win_idx = 0
        tns_colors = [(192, 192, 192)]
        spectrum_colors = [(128, 176, 224)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                bottom = ics.ics_info.max_sfb
                tns_bars = []
                for f in range(ics.tns_data.n_filt[win_idx]):
                    top = bottom
                    bottom = max(top - ics.tns_data.length[win_idx][f], 0)
                    tns_order = ics.tns_data.order[win_idx][f]
                    sfb_start = ics.params.swb_offset[bottom]
                    sfb_end = ics.params.swb_offset[top]
                    value = 1 if tns_order > 0 else 0
                    tns_bars.insert(0, (0, sfb_end - sfb_start, value))

                if bottom > 0:
                    tns_bars.insert(0, (0, bottom, 0))

                spectrum_points = []
                for i in range(ics.params.window_length):
                    value = aac.tns_spec[self.channel][g][win][i]
                    spectrum_points.append((0, i, value))

                self.add_plot(win_idx, PlotBar(h_axis, v_axis_tns, tns_colors, tns_bars))
                self.add_plot(win_idx, PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis_spectrum, 1, 5)))
                self.add_plot(win_idx, PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class AACRawSamplesPlot(AACPlotView):
    def __init__(self, channel):
        super(AACRawSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = AxisLinearUnsigned(ics.params.window_length * 2)
        v_axis_samples = AxisLinearSigned(32767)
        v_axis_window = AxisLinearUnsigned(1)
        win_idx = 0
        sample_colors = [(128, 176, 224)]
        window_colors = [(128, 128, 128)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                sample_points = []
                window_points = []
                for i in range(ics.params.window_length * 2):
                    value = aac.samples[self.channel][g][win][i]
                    sample_points.append((0, i, value))
                    value = aac.window(ics.ics_info.window_shape, ics.ics_info.window_sequence, i)
                    window_points.append((0, i, value))

                self.add_plot(win_idx, PlotLine(h_axis, v_axis_window, 1, window_colors, window_points))
                self.add_plot(win_idx, PlotAxes((h_axis, 0, 0), (v_axis_samples, 0, 0)))
                self.add_plot(win_idx, PlotLine(h_axis, v_axis_samples, 2, sample_colors, sample_points))
                win_idx += 1

class AACFinalSamplesPlot(AACPlotView):
    def __init__(self, channel):
        super(AACFinalSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac_pair):
        (aac, prev_aac) = aac_pair
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.reset()

        samples = aac.windowed_samples[self.channel]
        if prev_aac:
            prev_samples = prev_aac.windowed_samples[self.channel]
        else:
            prev_samples = [0] * 2048

        h_axis = AxisLinearUnsigned(1024)
        v_axis = AxisLinearSigned(32767)
        win_idx = 0
        colors = [(128, 176, 224)]
        points = []
        for i in range(1024):
            value = samples[i] + prev_samples[1024 + i]
            points.append((0, i, value))

        self.add_plot(win_idx, PlotAxes((h_axis, 0, 0), (v_axis, 0, 0)))
        self.add_plot(win_idx, PlotLine(h_axis, v_axis, 2, colors, points))

class AACFinalSamplesPlot2(QtWidgets.QWidget):
    def __init__(self, channel):
        super(AACFinalSamplesPlot, self).__init__()
        self.channel = channel
        self.aac = None
        self.prev_aac = None

    def set_aac(self, aac):
        (self.aac, self.prev_aac) = aac
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        ics = self.aac.parsed_block.cpe.ics[self.channel]
      
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        painter.setPen(pen_center)
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)

        prev = None
        pen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(128, 176, 224)), 2)
        samples = self.aac.windowed_samples[self.channel]
        if self.prev_aac:
            prev_samples = self.prev_aac.windowed_samples[self.channel]
        else:
            prev_samples = [0] * 2048

        if samples is not None:
            painter.setPen(pen)
            for i in range(1024):
                s = samples[i] + prev_samples[1024 + i]
                x = self.width() * i / 1024
                y = self.height() * (1 - s / 32767) / 2
                if prev:
                    (prev_x, prev_y) = prev
                    painter.drawLine(prev_x, prev_y, x, y)
                prev = (x, y)

        painter.end()

class AACPerChannelView(QtWidgets.QScrollArea):
    def __init__(self, cls):
        super(AACPerChannelView, self).__init__()

        self.widget = QtWidgets.QWidget()
        self.spectrum_plots = []
        layout = QtWidgets.QVBoxLayout()
        for i in range(2):
            plot = cls(i)
            layout.addWidget(plot)
            self.spectrum_plots.append(plot)
        self.widget.setLayout(layout)
        self.widget.setMinimumSize(500, 500)
        self.setWidget(self.widget)

    def set_aac(self, aac):
        for plot in self.spectrum_plots:
            plot.set_aac(aac)

    def resizeEvent(self, event):
        self.widget.setFixedSize(event.size().width(), event.size().width())

class AACStreamView(QtWidgets.QWidget):
    def __init__(self, file):
        super(AACStreamView, self).__init__()
        self.title = 'AAC Streams'
        self.file = file

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.file.numsamples())
        self.spinbox.valueChanged.connect(self.spinbox_changed)
        hlayout.addWidget(self.spinbox)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        tabs = QtWidgets.QTabWidget()
        self.syntax_view = SyntaxView('Syntax')
        tabs.addTab(self.syntax_view, self.syntax_view.title)
        self.spec_sf_view = AACPerChannelView(AACSpectrumScalefactorPlot)
        tabs.addTab(self.spec_sf_view, 'Raw Spectrum/Scalefactors')
        self.rescaled_spectrum_view = AACPerChannelView(AACRescaledSpectrumPlot)
        tabs.addTab(self.rescaled_spectrum_view, 'Rescaled Spectrum')
        self.spectrum_view = AACPerChannelView(AACSpectrumPlot)
        tabs.addTab(self.spectrum_view, 'Spectrum')
        self.tns_spectrum_view = AACPerChannelView(AACTnsSpectrumPlot)
        tabs.addTab(self.tns_spectrum_view, 'TNS Spectrum')
        self.raw_samples_view = AACPerChannelView(AACRawSamplesPlot)
        tabs.addTab(self.raw_samples_view, 'Raw Samples')
        self.final_samples_view = AACPerChannelView(AACFinalSamplesPlot)
        tabs.addTab(self.final_samples_view, 'Final Samples')

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.spinbox_changed(0)

    def spinbox_changed(self, value):
        (bytes, location) = self.file.getsample(value)
        self.aac = AAC()
        self.aac.parse(bytes, location, self.file.es_descriptor())

        if value > 0:
            (bytes, location) = self.file.getsample(value - 1)
            self.prev_aac = AAC()
            self.prev_aac.parse(bytes, location, self.file.es_descriptor())
        else:
            self.prev_aac = None

        self.syntax_view.update_syntax(self.file.bytestream, self.aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        self.spec_sf_view.set_aac(self.aac)
        self.rescaled_spectrum_view.set_aac(self.aac)
        self.spectrum_view.set_aac(self.aac)
        self.tns_spectrum_view.set_aac(self.aac)
        self.raw_samples_view.set_aac(self.aac)
        self.final_samples_view.set_aac((self.aac, self.prev_aac))

class Analyzer:
    def __init__(self, stream):
        self.stream = stream
        self.file = File(stream)

    def analyze(self):
        views = []
        views.append(SyntaxView('MP4 File', self.stream, self.file.syntax_items()))
        views.append(AACStreamView(self.file))
        return views