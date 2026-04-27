from . import block, plot
import syntax

from PySide2 import QtWidgets

class SpectrumScalefactorPlot(plot.PlotView):
    def __init__(self, channel):
        super(SpectrumScalefactorPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis_scalefactor = plot.AxisLinearUnsigned(128)
        v_axis_spectrum = plot.AxisLinearSigned(32) 
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
                    is_intensity = ics.section_data.sfb_cb[g][sfb] in (block.INTENSITY_HCB, block.INTENSITY_HCB2)
                    color = 1 if is_intensity else 0
                    scalefactor_bars.append((color, end - start, val))

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 0
                    for bin in range(start, end):
                        value = ics.spectral_data.spec[g][win][sfb][bin - start]
                        spectrum_points.append((color, bin, value))

                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_scalefactor, scalefactor_colors, scalefactor_bars))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class RescaledSpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(RescaledSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis = plot.AxisLogarithmicSigned(7) 
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

                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class SpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(SpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis = plot.AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [(128, 176, 224)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for i in range(ics.params.window_length):
                    value = aac.spec[self.channel][g][win][i]
                    points.append((0, i, value))

                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class TNSSpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(TNSSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis_spectrum = plot.AxisLogarithmicSigned(7)
        v_axis_tns = plot.AxisLinearUnsigned(1) 
        win_idx = 0
        tns_colors = [(192, 192, 192)]
        spectrum_colors = [(128, 176, 224)]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                bottom = ics.ics_info.max_sfb
                tns_bars = []
                if hasattr(ics, 'tns_data'):
                    spectrum = aac.tns_spec
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
                else:
                    spectrum = aac.spec

                spectrum_points = []
                for i in range(ics.params.window_length):
                    value = spectrum[self.channel][g][win][i]
                    spectrum_points.append((0, i, value))

                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_tns, tns_colors, tns_bars))
                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis_spectrum, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_spectrum, 2, spectrum_colors, spectrum_points))
                win_idx += 1

class RawSamplesPlot(plot.PlotView):
    def __init__(self, channel):
        super(RawSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length * 2)
        v_axis_samples = plot.AxisLinearSigned(32767)
        v_axis_window = plot.AxisLinearUnsigned(1)
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

                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_window, 1, window_colors, window_points))
                self.add_plot(win_idx, plot.PlotAxes((h_axis, 0, 0), (v_axis_samples, 0, 0)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_samples, 2, sample_colors, sample_points))
                win_idx += 1

class FinalSamplesPlot(plot.PlotView):
    def __init__(self, channel):
        super(FinalSamplesPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        self.reset()

        samples = aac.windowed_samples[self.channel]
        if prev_aac:
            prev_samples = prev_aac.windowed_samples[self.channel]
        else:
            prev_samples = [0] * 2048

        h_axis = plot.AxisLinearUnsigned(1024)
        v_axis = plot.AxisLinearSigned(32767)
        win_idx = 0
        colors = [(128, 176, 224)]
        points = []
        for i in range(1024):
            value = samples[i] + prev_samples[1024 + i]
            points.append((0, i, value))

        self.add_plot(win_idx, plot.PlotAxes((h_axis, 0, 0), (v_axis, 0, 0)))
        self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))

class PerChannelView(QtWidgets.QScrollArea):
    def __init__(self, cls, title):
        super(PerChannelView, self).__init__()

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
        self.title = title

    def set_aac(self, aac, prev_aac):
        for plot in self.spectrum_plots:
            plot.set_aac(aac, prev_aac)

    def resizeEvent(self, event):
        self.widget.setFixedSize(event.size().width(), event.size().width())

class Analyzer:
    def __init__(self, track):
        self.track = track
        self.syntax_view = syntax.SyntaxView('Syntax')

        self.aac_views = [
            PerChannelView(SpectrumScalefactorPlot, 'Raw Spectrum/Scalefactors'),
            PerChannelView(RescaledSpectrumPlot, 'Rescaled Spectrum'),
            PerChannelView(SpectrumPlot, 'Spectrum'),
            PerChannelView(TNSSpectrumPlot, 'TNS Spectrum'),
            PerChannelView(RawSamplesPlot, 'Raw Samples'),
            PerChannelView(FinalSamplesPlot, 'Final Samples')
        ]

    def get_views(self):
        return [self.syntax_view] + self.aac_views

    def set_sample(self, sample):
        (bytes, location) = self.track.getsample(sample)
        aac = block.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())

        if sample > 0:
            (prev_bytes, prev_location) = self.track.getsample(sample - 1)
            prev_aac = block.RawDataBlock()
            prev_aac.parse(prev_bytes, prev_location, self.track.es_descriptor())
        else:
            prev_aac = None

        self.syntax_view.update_syntax(self.track.bytestream, aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        for aac_view in self.aac_views:
            aac_view.set_aac(aac, prev_aac)
