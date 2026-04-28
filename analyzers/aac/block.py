import stream
from . import tables
import math
from syntax import format_enum

import numpy as np
import scipy.fft
import copy

ID_SCE = 0x0
ID_CPE = 0x1
ID_CCE = 0x2
ID_LFE = 0x3
ID_DSE = 0x4
ID_PCE = 0x5
ID_FIL = 0x6
ID_END = 0x7

ONLY_LONG_SEQUENCE = 0
LONG_START_SEQUENCE = 1
EIGHT_SHORT_SEQUENCE = 2
LONG_STOP_SEQUENCE = 3

enum_window_sequence = format_enum({
    0: 'ONLY_LONG_SEQUENCE',
    1: 'LONG_START_SEQUENCE',
    2: 'EIGHT_SHORT_SEQUENCE',
    3: 'LONG_STOP_SEQUENCE'
})

PRED_SFB_MAX = 1000

ZERO_HCB = 0
NOISE_HCB = 13
INTENSITY_HCB2 = 14
INTENSITY_HCB = 15

enum_hcb = format_enum({
    0: 'ZERO_HCB',
    13: 'NOISE_HCB',
    14: 'INTENSITY_HCB2',
    15: 'INTENSITY_HCB'
})

FIRST_PAIR_HCB = 5
ESC_HCB = 11
ESC_FLAG = 16

unsigned_cb = [0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1]
lav_cb = [0, 1, 1, 2, 2, 4, 4, 7, 7, 12, 12, 16]

def compile_huffman(cb):
    root = [None, None]
    for (index, (length, code)) in enumerate(cb):
        cur = root
        for i in range(length):
            bit = (code >> (length - i - 1)) & 1
            if i == length - 1:
                cur[bit] = index
            else:
                if cur[bit] is None:
                    cur[bit] = [None, None]    
                cur = cur[bit]

    tree = []
    def add_node(tree, node):
        index = len(tree)
        tree.extend([0, 0])
        for (n, child) in enumerate(node):
            if isinstance(child, int):
                tree[index + n] = child
            else:
                tree[index + n] = -add_node(tree, child)
        return index
    add_node(tree, root)
    return np.array(tree)

def construct_window(window_sequence):
    def sin_win(n, N):
        return math.sin((math.pi / N) * (n + 1/2))

    if window_sequence == ONLY_LONG_SEQUENCE:
        window = [sin_win(n, 2048) for n in range(2048)]
    elif window_sequence == LONG_START_SEQUENCE:
        window = [sin_win(n, 2048) for n in range(1024)] + [1] * 448 + [sin_win(n + 128, 256) for n in range(128)] + [0] * 448
    elif window_sequence == EIGHT_SHORT_SEQUENCE:
        window = [sin_win(n, 256) for n in range(256)]
    elif window_sequence == LONG_STOP_SEQUENCE:
        window = [0] * 448 + [sin_win(n, 256) for n in range(128)] + [1] * 448 + [sin_win(n + 1024, 2048) for n in range(1024)]

    return np.array(window)

spect_codebook = [0] + [compile_huffman(cb) for cb in (tables.spectral_cb_1, tables.spectral_cb_2, tables.spectral_cb_3, tables.spectral_cb_4, tables.spectral_cb_5, tables.spectral_cb_6, tables.spectral_cb_7, tables.spectral_cb_8, tables.spectral_cb_9, tables.spectral_cb_10, tables.spectral_cb_11)]
sf_codebook = compile_huffman(tables.scalefactor_cb)
windows = [construct_window(window_sequence) for window_sequence in range(4)]

class ParseObject:
    pass

class RawDataBlock:
    def parse(self, bytes, byte_start, es_descriptor):
        self.bitstream = stream.Bitstream(bytes, byte_start)
        self.parsed_block = self.parse_raw_data_block(es_descriptor)
        self.process(self.parsed_block)

    def syntax_items(self):
        return [self.parsed_block.syntax_item]

    def parse_raw_data_block(self, es_descriptor):
        self.bitstream.start_syntax_item('raw_data_block')
        block = ParseObject()
        while True:
            id = self.bitstream.getbits(3)
            if id == ID_CPE:
                block.cpe = self.parse_channel_pair_element(es_descriptor)
            elif id == ID_END:
                break
            else:
                break
        block.syntax_item = self.bitstream.finish_syntax_item()
        return block

    def parse_channel_pair_element(self, es_descriptor):
        self.bitstream.start_syntax_item('channel_pair_element')
        cpe = ParseObject()
        cpe.element_instance_tag = self.bitstream.getbits(4, 'element_instance_tag')
        cpe.common_window = self.bitstream.getbits(1, 'common_window')
        if cpe.common_window:
            cpe.ics_info = self.parse_ics_info()
            cpe.params = self.setup_params(cpe.ics_info, es_descriptor)
            cpe.ms_mask_present = self.bitstream.getbits(2, 'ms_mask_present')
            if cpe.ms_mask_present == 1:
                cpe.ms_used = [None] * cpe.params.num_window_groups
                self.bitstream.start_syntax_item('ms_used')
                for g in range(cpe.params.num_window_groups):
                    self.bitstream.start_syntax_item('group %i' % g)
                    cpe.ms_used[g] = [0] * cpe.ics_info.max_sfb
                    for sfb in range(cpe.ics_info.max_sfb):
                        cpe.ms_used[g][sfb] = self.bitstream.getbits(1, 'sfb %i' % sfb)
                    self.bitstream.finish_syntax_item()
                self.bitstream.finish_syntax_item()
        else:
            cpe.ics_info = None

        cpe.ics = [self.parse_individual_channel_stream(cpe.ics_info, es_descriptor), 
                   self.parse_individual_channel_stream(cpe.ics_info, es_descriptor)]
        self.bitstream.finish_syntax_item()
        return cpe

    def parse_ics_info(self):
        self.bitstream.start_syntax_item('ics_info')
        ics_info = ParseObject()
        ics_reserved_bit = self.bitstream.getbits(1)
        ics_info.window_sequence = self.bitstream.getbits(2, 'window_sequence', format=enum_window_sequence)
        ics_info.window_shape = self.bitstream.getbits(1, 'window_shape')
        if ics_info.window_sequence == EIGHT_SHORT_SEQUENCE:
            ics_info.max_sfb = self.bitstream.getbits(4, 'max_sfb')
            ics_info.scale_factor_grouping = self.bitstream.getbits(7, 'scale_factor_grouping')
        else:
            ics_info.max_sfb = self.bitstream.getbits(6, 'max_sfb')
            ics_info.predictor_data_present = self.bitstream.getbits(1, 'predictor_data_present')
        self.bitstream.finish_syntax_item()
        return ics_info

    def parse_individual_channel_stream(self, ics_info, es_descriptor):
        self.bitstream.start_syntax_item('individual_channel_stream')
        ics = ParseObject()
        ics.global_gain = self.bitstream.getbits(8, 'global_gain')
        ics.ics_info = ics_info or self.parse_ics_info()
        ics.params = self.setup_params(ics.ics_info, es_descriptor)
        ics.section_data = self.parse_section_data(ics.ics_info, ics.params)
        ics.scale_factor_data = self.parse_scale_factor_data(ics.section_data, ics.ics_info, ics.global_gain, ics.params)

        ics.pulse_data_present = self.bitstream.getbits(1)
        if ics.pulse_data_present:
            ics.pulse_data = self.parse_pulse_data()

        ics.tns_data_present = self.bitstream.getbits(1)
        if ics.tns_data_present:
            ics.tns_data = self.parse_tns_data(ics.params)

        ics.gain_control_data_present = self.bitstream.getbits(1)

        ics.spectral_data = self.parse_spectral_data(ics.section_data, ics.ics_info, ics.params)

        self.bitstream.finish_syntax_item()
        return ics

    def setup_params(self, ics_info, es_descriptor):
        params = ParseObject()

        fs_index = es_descriptor.decConfigDescr.decSpecificInfo.samplingFrequencyIndex
        frameLengthFlag = es_descriptor.decConfigDescr.decSpecificInfo.specificConfig.frameLengthFlag
        if frameLengthFlag == 0:
            num_swb_long_window = tables.num_swb_long_window_2048
            swb_offset_long_window = tables.swb_offset_long_window_2048
            num_swb_short_window = tables.num_swb_short_window_256
            swb_offset_short_window = tables.swb_offset_short_window_256
            long_window_length = 1024
            short_window_length = 128
        else:
            num_swb_long_window = tables.num_swb_long_window_1920
            swb_offset_long_window = tables.swb_offset_long_window_1920
            num_swb_short_window = tables.num_swb_short_window_240
            swb_offset_short_window = tables.swb_offset_short_window_240
            long_window_length = 960
            short_window_length = 120

        if ics_info.window_sequence in (ONLY_LONG_SEQUENCE, LONG_START_SEQUENCE, LONG_STOP_SEQUENCE):
            params.num_windows = 1
            params.num_window_groups = 1
            params.window_group_length = [1]
            params.window_length = long_window_length
            params.num_swb = num_swb_long_window[fs_index]
            params.sect_sfb_offset = [None]
            params.sect_sfb_offset[0] = [0] * (ics_info.max_sfb + 1)
            params.swb_offset = [0] * (ics_info.max_sfb + 1)
            for i in range(ics_info.max_sfb + 1):
                params.sect_sfb_offset[0][i] = swb_offset_long_window[fs_index][i]
                params.swb_offset[i] = swb_offset_long_window[fs_index][i]
        elif ics_info.window_sequence == EIGHT_SHORT_SEQUENCE:
            params.num_windows = 8
            params.num_window_groups = 1
            params.window_group_length = [1]
            params.window_length = short_window_length
            params.swb_offset = [0] * (num_swb_short_window[fs_index] + 1)
            for i in range(num_swb_short_window[fs_index] + 1):
                params.swb_offset[i] = swb_offset_short_window[fs_index][i]
            for i in range(params.num_windows - 1):
                bit_set = (1 << (6 - i)) & ics_info.scale_factor_grouping
                if bit_set == 0:
                    params.num_window_groups += 1
                    params.window_group_length.append(1)
                else:
                    params.window_group_length[-1] += 1

            params.sect_sfb_offset = [None] * params.num_window_groups
            for g in range(params.num_window_groups):
                offset = 0
                params.sect_sfb_offset[g] = [0] * (ics_info.max_sfb + 1)
                for i in range(ics_info.max_sfb):
                    width = swb_offset_short_window[fs_index][i+1] - swb_offset_short_window[fs_index][i]
                    width *= params.window_group_length[g]
                    params.sect_sfb_offset[g][i] = offset
                    offset += width
                params.sect_sfb_offset[g][ics_info.max_sfb] = offset

        return params

    def parse_section_data(self, ics_info, params):
        self.bitstream.start_syntax_item('section_data')
        sect = ParseObject()
        if ics_info.window_sequence == EIGHT_SHORT_SEQUENCE:
            sect_esc_val = (1 << 3) - 1
            sect_esc_len = 3
        else:
            sect_esc_val = (1 << 5) - 1
            sect_esc_len = 5

        sect.sfb_cb = [None] * params.num_window_groups
        sect.sect_cb = [None] * params.num_window_groups
        sect.sect_start = [None] * params.num_window_groups
        sect.sect_end = [None] * params.num_window_groups
        sect.num_sec = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            self.bitstream.start_syntax_item('group %i' % g)
            k = 0
            i = 0
            sect.sfb_cb[g] = []
            sect.sect_cb[g] = []
            sect.sect_start[g] = []
            sect.sect_end[g] = []
            while k < ics_info.max_sfb:
                self.bitstream.start_syntax_item()
                cb = self.bitstream.getbits(4)
                sect.sect_cb[g].append(cb)
                sect_len = 0
                while True:
                    sect_len_incr = self.bitstream.getbits(sect_esc_len)
                    if sect_len_incr == sect_esc_val:
                        sect_len += sect_esc_val
                    else:
                        break
                sect_len += sect_len_incr
                self.bitstream.finish_syntax_item('cb: %s, sect_len: %i' % (enum_hcb(cb), sect_len))

                sect.sect_start[g].append(k)
                sect.sect_end[g].append(k + sect_len)
                for sfb in range(sect_len):
                    sect.sfb_cb[g].append(cb)
                k += sect_len
                i += 1
            sect.num_sec[g] = i
            self.bitstream.finish_syntax_item()

        self.bitstream.finish_syntax_item()
        return sect

    def parse_scale_factor_data(self, section_data, ics_info, global_gain, params):
        self.bitstream.start_syntax_item('scale_factor_data')
        sfd = ParseObject()
        noise_pcm_flag = 1
        last_sf = global_gain
        last_is = 0
        sfd.sf = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            self.bitstream.start_syntax_item('group %i' % g)
            sfd.sf[g] = [0] * ics_info.max_sfb
            for sfb in range(ics_info.max_sfb):
                if section_data.sfb_cb[g][sfb] != ZERO_HCB:
                    if section_data.sfb_cb[g][sfb] in (INTENSITY_HCB, INTENSITY_HCB2):
                        dpcm_is = self.decode_huffman(sf_codebook) - 60
                        s = dpcm_is + last_is
                        sfd.sf[g][sfb] = s
                        last_is = s
                    else:
                        is_noise = 0
                        if is_noise:
                            pass
                        else:
                            dpcm_sf = self.decode_huffman(sf_codebook) - 60
                            s = dpcm_sf + last_sf
                            sfd.sf[g][sfb] = s
                            last_sf = s
            self.bitstream.finish_syntax_item()
        
        self.bitstream.finish_syntax_item()
        return sfd

    def parse_spectral_data(self, section_data, ics_info, params):
        self.bitstream.start_syntax_item('spectral_data')
        spectral_data = ParseObject()
        spectral_data.spec = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            self.bitstream.start_syntax_item('group %i' % g)
            spectral_data.spec[g] = [None] * params.window_group_length[g]
            for w in range(params.window_group_length[g]):
                spectral_data.spec[g][w] = [None] * ics_info.max_sfb
                for sfb in range(ics_info.max_sfb):
                    num_bins = params.swb_offset[sfb + 1] - params.swb_offset[sfb]
                    spectral_data.spec[g][w][sfb] = np.zeros(num_bins)

            for i in range(section_data.num_sec[g]):
                sect_cb = section_data.sect_cb[g][i]
                if sect_cb not in (ZERO_HCB, NOISE_HCB, INTENSITY_HCB, INTENSITY_HCB2):
                    if sect_cb < FIRST_PAIR_HCB:
                        dim = 4
                    else:
                        dim = 2

                    lav = lav_cb[sect_cb]
                    if unsigned_cb[sect_cb]:
                        mod = lav + 1
                        off = 0
                    else:
                        mod = 2 * lav + 1
                        off = lav

                    for sfb in range(section_data.sect_start[g][i], section_data.sect_end[g][i]):
                        num_bins = params.swb_offset[sfb + 1] - params.swb_offset[sfb]
                        for win in range(params.window_group_length[g]):
                            b = 0
                            while b < num_bins:
                                hcod = self.decode_huffman(spect_codebook[sect_cb])
                                val = []
                                idx = hcod
                                if dim == 4:
                                    w = int(idx/(mod*mod*mod)) - off
                                    idx -= (w+off)*(mod*mod*mod)
                                    x = int(idx/(mod*mod)) - off
                                    idx -= (x+off)*(mod*mod)
                                    val.extend([w,x])
                                y = int(idx/mod) - off
                                idx -= (y+off)*(mod)
                                z = idx - off
                                val.extend([y,z])

                                sign = [0] * dim
                                if unsigned_cb[sect_cb]:
                                    for n in range(dim):
                                        if val[n] != 0:
                                            s = self.bitstream.getbit()
                                            sign[n] = s

                                if sect_cb == ESC_HCB:
                                    for n in range(2):
                                        if val[n] == ESC_FLAG:
                                            val[n] = self.decode_escape()

                                for n in range(dim):
                                    if sign[n] == 1:
                                        val[n] *= -1

                                spectral_data.spec[g][win][sfb][b:b+dim] = val
                                b += dim
            self.bitstream.finish_syntax_item()

        self.bitstream.finish_syntax_item()
        return spectral_data

    def parse_pulse_data(self):
        self.bitstream.start_syntax_item('pulse_data')
        pulse = ParseObject()
        pulse.number_pulse = self.bitstream.getbits(2, 'number_pulse')
        pulse.pulse_start_sfb = self.bitstream.getbits(6, 'pulse_start_sfb')
        pulse.pulse_offset = [0] * pulse.number_pulse
        pulse.pulse_amp = [0] * pulse.number_pulse
        self.bitstream.start_syntax_item('pulses')
        for i in range(pulse.number_pulse):
            self.bitstream.start_syntax_item()
            pulse.pulse_offset[i] = self.bitstream.getbits(5)
            pulse.pulse_amp[i] = self.bitstream.getbits(4)
            self.bitstream.finish_syntax_item('pulse_offset: %i, pulse_amp: %i' % (pulse.pulse_offset[i], pulse.pulse_amp[i]))
        self.bitstream.finish_syntax_item()

        self.bitstream.finish_syntax_item()
        return pulse

    def parse_tns_data(self, params):
        self.bitstream.start_syntax_item('tns_data')
        tns = ParseObject()
        if params.window_length == 128:
            n_filt_len = 1
            length_len = 4
            order_len = 3
        else:
            n_filt_len = 2
            length_len = 6
            order_len = 5
        tns.n_filt = [0] * params.num_windows
        tns.coef_res = [0] * params.num_windows
        tns.length = [None] * params.num_windows
        tns.order = [None] * params.num_windows
        tns.direction = [None] * params.num_windows
        tns.coef_compress = [None] * params.num_windows
        tns.coef = [None] * params.num_windows
        for w in range(params.num_windows):
            self.bitstream.start_syntax_item('window %i' % w)
            tns.n_filt[w] = self.bitstream.getbits(n_filt_len, 'n_filt')
            if tns.n_filt[w]:
                tns.coef_res[w] = self.bitstream.getbits(1, 'coef_res')

            tns.length[w] = [0] * tns.n_filt[w]
            tns.order[w] = [0] * tns.n_filt[w]
            tns.direction[w] = [0] * tns.n_filt[w]
            tns.coef_compress[w] = [0] * tns.n_filt[w]
            tns.coef[w] = [None] * tns.n_filt[w]
            for filt in range(tns.n_filt[w]):
                self.bitstream.start_syntax_item('filter %i' % filt)
                tns.length[w][filt] = self.bitstream.getbits(length_len, 'length')
                tns.order[w][filt] = self.bitstream.getbits(order_len, 'order')
                if tns.order[w][filt]:
                    tns.direction[w][filt] = self.bitstream.getbits(1, 'direction')
                    tns.coef_compress[w][filt] = self.bitstream.getbits(1, 'coef_compress')
                    tns.coef[w][filt] = [0] * tns.order[w][filt]
                    coef_len = 4 if tns.coef_res[w] else 3
                    if tns.coef_compress[w][filt]:
                        coef_len -= 1
                    for i in range(tns.order[w][filt]):
                        tns.coef[w][filt][i] = self.bitstream.getbits(coef_len, 'coef %i' % i)
                self.bitstream.finish_syntax_item()
            self.bitstream.finish_syntax_item()

        self.bitstream.finish_syntax_item()
        return tns

    def decode_huffman(self, codebook):
        index = 0
        while True:
            bit = self.bitstream.getbit()
            val = codebook[index + bit]
            if val >= 0:
                return val
            else:
                index = -val

    def decode_escape(self):
        n = 0
        while True:
            bit = self.bitstream.getbit()
            if bit:
                n += 1
            else:
                break
        val = self.bitstream.getbits(n+4)
        return (1 << (n+4)) + val

    def process(self, parsed_block):
        ics_list = parsed_block.cpe.ics
        self.x_quant = self.process_noiseless_coding(ics_list)
        self.x_invquant = self.process_quantization(ics_list, self.x_quant)
        self.x_rescal = self.process_scalefactors(ics_list, self.x_invquant)
        spec = self.process_joint_stereo(parsed_block.cpe, self.x_rescal)
        self.spec = self.flatten_spectrum(ics_list, spec)
        self.tns_spec = self.process_tns(ics_list, self.spec)
        self.samples = self.process_filterbank(ics_list, self.tns_spec)
        self.windowed_samples = self.process_window(ics_list, self.samples)

    def process_noiseless_coding(self, ics_list):
        x_quant = [None] * len(ics_list)
        for (i, ics) in enumerate(ics_list):
            x_quant[i] = [None] * ics.params.num_window_groups
            for g in range(ics.params.num_window_groups):
                x_quant[i][g] = [None] * ics.params.window_group_length[g]
                for w in range(ics.params.window_group_length[g]):
                    x_quant[i][g][w] = [0] * ics.params.window_length
                    for sfb in range(ics.ics_info.max_sfb):
                        x_quant[i][g][w][sfb] = ics.spectral_data.spec[g][w][sfb].copy()
            
            if ics.pulse_data_present:
                pulse_data = ics.pulse_data
                k = ics.params.swb_offset[pulse_data.pulse_start_sfb]
                for j in range(pulse_data.number_pulse):
                    k += pulse_data.pulse_offset[j]
                    for s in range(pulse_data.pulse_start_sfb, ics.ics_info.max_sfb):
                        if k < ics.params.swb_offset[s+1]:
                            swb = s
                            bin = k - ics.params.swb_offset[s]
                            break
                    if x_quant[i][0][0][sfb][bin] > 0:
                        x_quant[i][0][0][sfb][bin] += pulse_data.pulse_amp[j]
                    else:
                        x_quant[i][0][0][sfb][bin] -= pulse_data.pulse_amp[j]
        return x_quant

    def process_quantization(self, ics_list, x_quant):
        x_invquant = [None] * len(ics_list)
        for (i, ics) in enumerate(ics_list):
            x_invquant[i] = [None] * ics.params.num_window_groups
            for g in range(ics.params.num_window_groups):
                x_invquant[i][g] = [None] * ics.params.window_group_length[g]
                for w in range(ics.params.window_group_length[g]):
                    x_invquant[i][g][w] = [None] * ics.params.window_length
                    for sfb in range(ics.ics_info.max_sfb):
                        x_invquant[i][g][w][sfb] = np.copysign(np.power(np.abs(x_quant[i][g][w][sfb]), [4/3]), x_quant[i][g][w][sfb])

        return x_invquant

    def process_scalefactors(self, ics_list, x_invquant):
        x_rescal = [None] * len(ics_list)
        for (i, ics) in enumerate(ics_list):
            x_rescal[i] = [None] * ics.params.num_window_groups
            for g in range(ics.params.num_window_groups):
                x_rescal[i][g] = [None] * ics.params.window_group_length[g]
                for w in range(ics.params.window_group_length[g]):
                    x_rescal[i][g][w] = [0] * ics.params.window_length
                    for sfb in range(ics.ics_info.max_sfb):
                        gain = 2.0 ** (0.25 * (ics.scale_factor_data.sf[g][sfb] - 100))
                        x_rescal[i][g][w][sfb] = np.multiply(gain, x_invquant[i][g][w][sfb])

        return x_rescal

    def process_joint_stereo(self, cpe, spec):
        params = cpe.params
        ics_info = cpe.ics_info

        l_spec = [None] * params.num_window_groups
        r_spec = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            l_spec[g] = [None] * params.window_group_length[g]
            r_spec[g] = [None] * params.window_group_length[g]
            for w in range(params.window_group_length[g]):
                l_spec[g][w] = [None] * ics_info.max_sfb
                r_spec[g][w] = [None] * ics_info.max_sfb
                for sfb in range(ics_info.max_sfb):
                    l_spec[g][w][sfb] = spec[0][g][w][sfb].copy()
                    r_spec[g][w][sfb] = spec[1][g][w][sfb].copy()

        if cpe.ms_mask_present >= 1:
            for g in range(params.num_window_groups):
                for w in range(params.window_group_length[g]):
                    for sfb in range(ics_info.max_sfb):
                        if (cpe.ms_mask_present == 2 or cpe.ms_used[g][sfb]) and cpe.ics[1].section_data.sfb_cb[g][sfb] < 13:
                            tmp = l_spec[g][w][sfb] - r_spec[g][w][sfb]
                            l_spec[g][w][sfb] += r_spec[g][w][sfb]
                            r_spec[g][w][sfb] = tmp
        
        params = cpe.ics[1].params
        ics_info = cpe.ics[1].ics_info
        for g in range(params.num_window_groups):
            for w in range(params.window_group_length[g]):
                for sfb in range(ics_info.max_sfb):
                    sfb_cb = cpe.ics[1].section_data.sfb_cb[g][sfb]
                    is_intensity = 1 if sfb_cb == 14 else -1 if sfb_cb == 15 else 0
                    invert_intensity = (1 - 2 * cpe.ms_used[g][sfb]) if cpe.ms_mask_present == 1 else 1
                    if is_intensity:
                        scale = is_intensity * invert_intensity * (0.5 ** (0.25 * cpe.ics[1].scale_factor_data.sf[g][sfb]))
                        r_spec[g][w][sfb] = scale * l_spec[g][w][sfb]

        return (l_spec, r_spec)

    def flatten_spectrum(self, ics_list, spec):
        flat = [None] * 2
        for i in range(2):
            params = ics_list[i].params
            ics_info = ics_list[i].ics_info
            flat[i] = [None] * params.num_window_groups
            for g in range(params.num_window_groups):
                flat[i][g] = [None] * params.window_group_length[g]
                for w in range(params.window_group_length[g]):
                    flat[i][g][w] = np.zeros(params.window_length)
                    for sfb in range(ics_info.max_sfb):
                        start = params.swb_offset[sfb]
                        end = params.swb_offset[sfb+1]
                        flat[i][g][w][start:end] = spec[i][g][w][sfb]

        spec = flat

        return spec

    def process_tns(self, ics_list, spec):
        tns_spec = [None] * 2
        for c in range(2):
            if not hasattr(ics_list[c], 'tns_data'):
                tns_spec[c] = spec[c]
                continue

            ics = ics_list[c]
            params = ics.params
            ics_info = ics.ics_info
            tns_data = ics.tns_data
            tns_spec[c] = [None] * params.num_window_groups
            win_idx = 0
            for g in range(params.num_window_groups):
                tns_spec[c][g] = [None] * params.window_group_length[g]
                for w in range(params.window_group_length[g]):
                    tns_spec[c][g][w] = spec[c][g][w].copy()
                    bottom = ics_info.max_sfb
                    for f in range(tns_data.n_filt[win_idx]):
                        top = bottom
                        bottom = max(top - tns_data.length[win_idx][f], 0)
                        tns_order = tns_data.order[win_idx][f]
                        if tns_order == 0:
                            continue

                        coef_res_bits = tns_data.coef_res[win_idx] + 3
                        coef_compress = tns_data.coef_compress[win_idx][f]
                        coef = tns_data.coef[win_idx][f]

                        sgn_mask = [ 0x2, 0x4, 0x8 ] 
                        neg_mask = [ ~0x3, ~0x7, ~0xf ] 
                        coef_res2 = coef_res_bits - coef_compress; 
                        s_mask = sgn_mask[coef_res2 - 2] 
                        n_mask = neg_mask[coef_res2 - 2]

                        tmp = [0] * tns_order
                        for i in range(tns_order):
                            tmp[i] = (coef[i] | n_mask) if (coef[i] & s_mask) else coef[i]

                        iqfac = ((1 << (coef_res_bits - 1)) - 0.5) / (math.pi / 2.0); 
                        iqfac_m = ((1 << (coef_res_bits - 1)) + 0.5) / (math.pi / 2.0); 
                        
                        tmp2 = [0] * tns_order
                        for i in range(tns_order): 
                            tmp2[i] = math.sin(tmp[i] / (iqfac if tmp[i] >= 0 else iqfac_m))

                        a = [0] * (tns_order + 1)
                        b = [0] * tns_order

                        a[0] = 1
                        for m in range(1, tns_order + 1):
                            for i in range(1, m):
                                b[i] = a[i] + tmp2[m - 1] * a[m - i]
                            for i in range(1, m):
                                a[i] = b[i]
                            a[m] = tmp2[m - 1]
                        lpc = a

                        start = params.swb_offset[bottom]
                        end = params.swb_offset[top]

                        if tns_data.direction[win_idx][f]:
                            inc = -1
                            (start, end) = (end - 1, start - 1)
                        else:
                            inc = 1
                        
                        n = start
                        while n != end:
                            t = tns_spec[c][g][w][n]
                            for i in range(1, tns_order + 1):
                                m = n - inc * i
                                if (inc == 1 and m < start) or (inc == -1 and m > start):
                                    s = 0
                                else:
                                    s = tns_spec[c][g][w][m]
                                t -= lpc[i] * s
                            tns_spec[c][g][w][n] = t

                            n += inc

                    win_idx += 1

        return tns_spec

    def process_filterbank(self, ics_list, spec):
        samples = [None] * 2
        for i in range(2):
            params = ics_list[i].params
 
            samples[i] = [None] * params.num_window_groups
            for g in range(params.num_window_groups):
                samples[i][g] = [None] * params.window_group_length[g]
                for w in range(params.window_group_length[g]):
                    spectrum = spec[i][g][w]
                    
                    samples[i][g][w] = self.imdct(spectrum)

        return samples

    def process_window(self, ics_list, samples):
        windowed_samples = [None] * 2
        for i in range(2):
            win_idx = 0
            params = ics_list[i].params
            ics_info = ics_list[i].ics_info
 
            windowed_samples[i] = np.zeros(2048)
            for g in range(params.num_window_groups):
                for w in range(params.window_group_length[g]):
                    start = 0
                    if ics_info.window_sequence == EIGHT_SHORT_SEQUENCE:
                        start = 448 + win_idx * 128
                    else:
                        start = 0

                    windowed_samples[i][start:start + params.window_length * 2] += np.multiply(samples[i][g][w], windows[ics_info.window_sequence])
                    win_idx += 1

        return windowed_samples

    def window(self, window_shape, window_sequence, n):
        return windows[window_sequence][n]

    def imdct(self, spectrum):
        idct = scipy.fft.idct(spectrum, type=4)
        s = np.concatenate([idct, np.flip(idct) * -1])
        N = len(spectrum)
        samples = np.concatenate([s[N//2:N*2], s[0:N//2] * -1])
        return samples