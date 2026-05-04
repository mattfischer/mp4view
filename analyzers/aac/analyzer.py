from . import parse, plot, player, waveform
import syntax
import math

from PySide2 import QtWidgets, QtCore

SCALEFACTOR_COLOR = (192, 184, 192)
INTENSITY_COLOR = (224, 192, 128)

LINE_COLOR = (128, 176, 224)
MS_COLOR = (160, 212, 184)

TNS_COLOR = (248, 220, 220)

WINDOW_COLOR = (128, 128, 128)

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
        v_axis_intensity = plot.AxisLinearSigned(10)
        v_axis_spectrum = plot.AxisLinearSigned(32) 
        win_idx = 0
        scalefactor_colors = [SCALEFACTOR_COLOR]
        intensity_colors = [INTENSITY_COLOR]
        spectrum_colors = [LINE_COLOR, MS_COLOR, INTENSITY_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                scalefactor_bars = []
                intensity_bars = []
                spectrum_points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]
                    is_intensity = ics.section_data.sfb_cb[g][sfb] in (parse.INTENSITY_HCB, parse.INTENSITY_HCB2)
                    if is_intensity:
                        val = ics.scale_factor_data.sf[g][sfb]
                        caption = 'sfb %i: %i (intensity)' % (sfb, val)
                        intensity_bars.append((0, end - start, val, caption))
                        scalefactor_bars.append((0, end - start, 0, None))
                    else:
                        val = ics.scale_factor_data.sf[g][sfb] - 100
                        gain = 2.0 ** (0.25 * (ics.scale_factor_data.sf[g][sfb] - 100))
                        gain_db = 10 * math.log(gain, 10)
                        caption = 'sfb %i: %i (%.1f dB)' % (sfb, val, gain_db)
                        scalefactor_bars.append((0, end - start, val, caption))
                        intensity_bars.append((0, end - start, 0, None))

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    color = 1 if ms_used else 2 if is_intensity else 0
                    for bin in range(start, end):
                        value = ics.spectral_data.spec[g][win][sfb][bin - start]
                        caption = 'bin %i: %i %s' % (bin, value, '(M/S stereo)' if ms_used else '(intensity)' if is_intensity else '')
                        spectrum_points.append((color, bin, value, caption))

                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_scalefactor, scalefactor_colors, scalefactor_bars))
                self.add_plot(win_idx, plot.PlotBar(h_axis, v_axis_intensity, intensity_colors, intensity_bars))
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
        colors = [LINE_COLOR, MS_COLOR, INTENSITY_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for sfb in range(ics.ics_info.max_sfb):
                    start = ics.params.swb_offset[sfb]
                    end = ics.params.swb_offset[sfb+1]

                    ms_used = (cpe.ms_mask_present == 2 or (cpe.ms_mask_present == 1 and cpe.ms_used[g][sfb]))
                    is_intensity = ics.section_data.sfb_cb[g][sfb] in (parse.INTENSITY_HCB, parse.INTENSITY_HCB2)
                    color = 1 if ms_used else 2 if is_intensity else 0
                    for bin in range(start, end):
                        value = aac.x_rescal[self.channel][g][win][sfb][bin - start]
                        caption = 'bin %i: %.0f %s' % (bin, value, '(M/S stereo)' if ms_used else '(intensity)' if is_intensity else '')
                        points.append((color, bin, value, caption))

                self.add_plot(win_idx, plot.PlotAxes((h_axis, ics.params.window_length // 64, 4), (v_axis, 1, 5)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis, 2, colors, points))
                win_idx += 1

class JointStereoSpectrumPlot(plot.PlotView):
    def __init__(self, channel):
        super(JointStereoSpectrumPlot, self).__init__()
        self.channel = channel

    def set_aac(self, aac, prev_aac):
        cpe = aac.parsed_block.cpe
        ics = cpe.ics[self.channel]
        self.set_num_windows(ics.params.num_windows)

        h_axis = plot.AxisLinearUnsigned(ics.params.window_length)
        v_axis = plot.AxisLogarithmicSigned(7) 
        win_idx = 0
        colors = [LINE_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                points = []
                for i in range(ics.params.window_length):
                    value = aac.spec[self.channel][g][win][i]
                    caption = 'bin %i: %.0f' % (i, value)
                    points.append((0, i, value, caption))

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
        tns_colors = [TNS_COLOR]
        spectrum_colors = [LINE_COLOR]
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
                        caption = 'TNS order %i' % tns_order
                        tns_bars.insert(0, (0, sfb_end - sfb_start, value, caption))

                    if bottom > 0:
                        tns_bars.insert(0, (0, bottom, 0, None))
                else:
                    spectrum = aac.spec

                spectrum_points = []
                for i in range(ics.params.window_length):
                    value = spectrum[self.channel][g][win][i]
                    caption = 'bin %i: %.0f' % (i, value)
                    spectrum_points.append((0, i, value, caption))

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
        sample_colors = [LINE_COLOR]
        window_colors = [WINDOW_COLOR]
        for g in range(ics.params.num_window_groups):
            for win in range(ics.params.window_group_length[g]):
                sample_points = []
                window_points = []
                for i in range(ics.params.window_length * 2):
                    value = aac.samples[self.channel][g][win][i]
                    caption = 'sample %i: %i' % (i, value)
                    sample_points.append((0, i, value, caption))
                    value = aac.window(ics.ics_info.window_shape, ics.ics_info.window_sequence, i)
                    window_points.append((0, i, value, None))

                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_window, 1, window_colors, window_points, False))
                self.add_plot(win_idx, plot.PlotAxes((h_axis, 0, 0), (v_axis_samples, 0, 0)))
                self.add_plot(win_idx, plot.PlotLine(h_axis, v_axis_samples, 2, sample_colors, sample_points))
                win_idx += 1

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
            PerChannelView(RescaledSpectrumPlot, 'Spectrum (rescaled)'),
            PerChannelView(JointStereoSpectrumPlot, 'Spectrum (joint stereo)'),
            PerChannelView(TNSSpectrumPlot, 'Spectrum (TNS)'),
            PerChannelView(RawSamplesPlot, 'Samples'),
        ]

    def get_views(self):
        return [self.syntax_view] + self.aac_views

    def set_sample(self, sample):
        (bytes, location) = self.track.getsample(sample)
        aac = parse.RawDataBlock()
        aac.parse(bytes, location, self.track.es_descriptor())

        if sample > 0:
            (prev_bytes, prev_location) = self.track.getsample(sample - 1)
            prev_aac = parse.RawDataBlock()
            prev_aac.parse(prev_bytes, prev_location, self.track.es_descriptor())
        else:
            prev_aac = None

        self.syntax_view.update_syntax(self.track.bytestream, aac.syntax_items())
        self.syntax_view.set_highlight(location, len(bytes))

        for aac_view in self.aac_views:
            aac_view.set_aac(aac, prev_aac)

class StreamView(QtWidgets.QWidget):
    def __init__(self, track):
        super(StreamView, self).__init__()
        self.title = 'AAC Streams'
        self.track = track
        self.aac_analyzer = Analyzer(track)
        self.player = player.Player(track)
        self.selected_sample = 0

        self.play_stop_timer = QtCore.QTimer()
        self.play_stop_timer.setInterval(1000)
        self.play_stop_timer.setSingleShot(True)
        self.play_stop_timer.timeout.connect(self.on_play_stop_timeout)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(QtWidgets.QLabel('Sample:'))
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setMaximum(self.track.numsamples())
        self.spinbox.valueChanged.connect(self.on_spinbox_changed)
        hlayout.addWidget(self.spinbox)

        self.play_stop_button = QtWidgets.QPushButton()
        play_icon = self.play_stop_button.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        self.play_stop_button.setIcon(play_icon)
        self.play_stop_button.clicked.connect(self.on_play_stop_button_clicked)
        hlayout.addWidget(self.play_stop_button)
        hlayout.addStretch(1)

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addLayout(hlayout)

        self.waveform_plot = waveform.WaveformPlot(track)
        self.waveform_plot.set_select_listener(self.on_selected_sample_changed)
        vlayout.addWidget(self.waveform_plot)

        tabs = QtWidgets.QTabWidget()
        for view in self.aac_analyzer.get_views():
            tabs.addTab(view, view.title)

        vlayout.addWidget(tabs)

        self.setLayout(vlayout)

        self.on_spinbox_changed(0)

    def on_selected_sample_changed(self, value):
        if self.spinbox.value() != value:
            self.spinbox.setValue(value)

    def on_spinbox_changed(self, value):
        self.selected_sample = value
        self.waveform_plot.set_selected_sample(value)
        self.aac_analyzer.set_sample(value)

    def on_play_stop_button_clicked(self):
        self.player.play(self.selected_sample)
        stop_icon = self.play_stop_button.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)
        self.play_stop_button.setIcon(stop_icon)
        self.play_stop_timer.start()

    def on_play_stop_timeout(self):
        play_icon = self.play_stop_button.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        self.play_stop_button.setIcon(play_icon)
