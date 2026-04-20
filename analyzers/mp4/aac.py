import stream
from . import aac_tables
import math
from syntax import format_enum

import numpy as np
import scipy.fft

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
    return tree

spect_codebook = [0] + [compile_huffman(cb) for cb in (aac_tables.spectral_cb_1, aac_tables.spectral_cb_2, aac_tables.spectral_cb_3, aac_tables.spectral_cb_4, aac_tables.spectral_cb_5, aac_tables.spectral_cb_6, aac_tables.spectral_cb_7, aac_tables.spectral_cb_8, aac_tables.spectral_cb_9, aac_tables.spectral_cb_10, aac_tables.spectral_cb_11)]
sf_codebook = compile_huffman(aac_tables.scalefactor_cb)

class Object:
    def printitem(self, name, entry, prefix=''):
        try:
            has_object = False
            for item in entry:
                if isinstance(item, Object):
                    has_object = True
            if has_object:
                for item in entry:
                    self.printitem(name, item, prefix)
                return
        except TypeError:
            pass

        if isinstance(entry, Object):
            print(prefix+'%s:' % name)
            entry.print(prefix+'  ')
        else:
            print(prefix+'%s: %s' % (name, entry))

    def print(self, prefix=''):
        for (name, entry) in self.__dict__.items():
            self.printitem(name, entry, prefix)
class AAC:
    def parse(self, bytes, byte_start, es_descriptor):
        self.bitstream = stream.Bitstream(bytes, byte_start)
        self.block = self.raw_data_block(es_descriptor)
        self.process()

    def syntax_items(self):
        return [self.block.syntax_item]

    def raw_data_block(self, es_descriptor):
        self.bitstream.start_syntax_item('raw_data_block')
        block = Object()
        while True:
            id = self.bitstream.getbits(3)
            if id == ID_CPE:
                block.cpe = self.channel_pair_element(es_descriptor)
            elif id == ID_END:
                break
            else:
                break
        block.syntax_item = self.bitstream.finish_syntax_item()
        return block

    def channel_pair_element(self, es_descriptor):
        self.bitstream.start_syntax_item('channel_pair_element')
        cpe = Object()
        cpe.element_instance_tag = self.bitstream.getbits(4, 'element_instance_tag')
        cpe.common_window = self.bitstream.getbits(1, 'common_window')
        if cpe.common_window:
            cpe.ics_info = self.ics_info()
            cpe.params = self.params(cpe.ics_info, es_descriptor)
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

        cpe.ics = [self.individual_channel_stream(cpe.ics_info, es_descriptor), 
                   self.individual_channel_stream(cpe.ics_info, es_descriptor)]
        self.bitstream.finish_syntax_item()
        return cpe

    def ics_info(self):
        self.bitstream.start_syntax_item('ics_info')
        ics_info = Object()
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

    def individual_channel_stream(self, ics_info, es_descriptor):
        self.bitstream.start_syntax_item('individual_channel_stream')
        ics = Object()
        ics.global_gain = self.bitstream.getbits(8, 'global_gain')
        ics.ics_info = ics_info or self.ics_info()
        ics.params = self.params(ics.ics_info, es_descriptor)
        ics.section_data = self.section_data(ics.ics_info, ics.params)
        ics.scale_factor_data = self.scale_factor_data(ics.section_data, ics.ics_info, ics.global_gain, ics.params)

        ics.pulse_data_present = self.bitstream.getbits(1)
        if ics.pulse_data_present:
            ics.pulse_data = self.pulse_data()

        ics.tns_data_present = self.bitstream.getbits(1)
        if ics.tns_data_present:
            ics.tns_data = self.tns_data(ics.params)

        ics.gain_control_data_present = self.bitstream.getbits(1)

        ics.spectral_data = self.spectral_data(ics.section_data, ics.ics_info, ics.params)

        self.bitstream.finish_syntax_item()
        return ics

    def params(self, ics_info, es_descriptor):
        params = Object()

        fs_index = es_descriptor.decConfigDescr.decSpecificInfo.samplingFrequencyIndex
        frameLengthFlag = es_descriptor.decConfigDescr.decSpecificInfo.specificConfig.frameLengthFlag
        if frameLengthFlag == 0:
            num_swb_long_window = aac_tables.num_swb_long_window_2048
            swb_offset_long_window = aac_tables.swb_offset_long_window_2048
            num_swb_short_window = aac_tables.num_swb_short_window_256
            swb_offset_short_window = aac_tables.swb_offset_short_window_256
            long_window_length = 1024
            short_window_length = 128
        else:
            num_swb_long_window = aac_tables.num_swb_long_window_1920
            swb_offset_long_window = aac_tables.swb_offset_long_window_1920
            num_swb_short_window = aac_tables.num_swb_short_window_240
            swb_offset_short_window = aac_tables.swb_offset_short_window_240
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

    def section_data(self, ics_info, params):
        self.bitstream.start_syntax_item('section_data')
        sect = Object()
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

    def scale_factor_data(self, section_data, ics_info, global_gain, params):
        self.bitstream.start_syntax_item('scale_factor_data')
        sfd = Object()
        noise_pcm_flag = 1
        last_sf = global_gain
        last_is = 0
        sfd.sf = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            self.bitstream.start_syntax_item('group %i' % g)
            sfd.sf[g] = [0] * ics_info.max_sfb
            for sfb in range(ics_info.max_sfb):
                if section_data.sfb_cb[g][sfb] != ZERO_HCB:
                    is_intensity = 0
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

    def spectral_data(self, section_data, ics_info, params):
        self.bitstream.start_syntax_item('spectral_data')
        spectral_data = Object()
        spectral_data.spec = [None] * params.num_window_groups
        for g in range(params.num_window_groups):
            self.bitstream.start_syntax_item('group %i' % g)
            spectral_data.spec[g] = [None] * params.window_group_length[g]
            for w in range(params.window_group_length[g]):
                spectral_data.spec[g][w] = [None] * ics_info.max_sfb
                for sfb in range(ics_info.max_sfb):
                    num_bins = params.swb_offset[sfb + 1] - params.swb_offset[sfb]
                    spectral_data.spec[g][w][sfb] = [0] * num_bins

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
                                            s = self.bitstream.getbits(1)
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

    def pulse_data(self):
        self.bitstream.start_syntax_item('pulse_data')
        pulse = Object()
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

    def tns_data(self, params):
        self.bitstream.start_syntax_item('tns_data')
        tns = Object()
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
            bit = self.bitstream.getbits(1)
            val = codebook[index + bit]
            if val >= 0:
                return val
            else:
                index = -val

    def decode_escape(self):
        n = 0
        while True:
            bit = self.bitstream.getbits(1)
            if bit:
                n += 1
            else:
                break
        val = self.bitstream.getbits(n+4)
        return (1 << (n+4)) + val

    def process(self):
        x_quant = [None] * len(self.block.cpe.ics)
        for (i, ics) in enumerate(self.block.cpe.ics):
            x_quant[i] = [None] * ics.params.num_window_groups
            for g in range(ics.params.num_window_groups):
                x_quant[i][g] = [None] * ics.params.window_group_length[g]
                for w in range(ics.params.window_group_length[g]):
                    x_quant[i][g][w] = [None] * ics.ics_info.max_sfb
                    for sfb in range(ics.ics_info.max_sfb):
                        x_quant[i][g][w][sfb] = ics.spectral_data.spec[g][w][sfb]
            
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

        self.x_invquant = [None] * len(self.block.cpe.ics)
        self.x_rescal = [None] * len(self.block.cpe.ics)
        for (i, ics) in enumerate(self.block.cpe.ics):
            self.x_invquant[i] = [None] * ics.params.num_window_groups
            self.x_rescal[i] = [None] * ics.params.num_window_groups
            for g in range(ics.params.num_window_groups):
                self.x_invquant[i][g] = [None] * ics.params.window_group_length[g]
                self.x_rescal[i][g] = [None] * ics.params.window_group_length[g]
                for w in range(ics.params.window_group_length[g]):
                    self.x_invquant[i][g][w] = [None] * ics.ics_info.max_sfb
                    self.x_rescal[i][g][w] = [None] * ics.ics_info.max_sfb
                    for sfb in range(ics.ics_info.max_sfb):
                        num_bins = ics.params.swb_offset[sfb+1] - ics.params.swb_offset[sfb]
                        self.x_invquant[i][g][w][sfb] = [0] * num_bins
                        self.x_rescal[i][g][w][sfb] = [0] * num_bins
                        gain = 2.0 ** (0.25 * (ics.scale_factor_data.sf[g][sfb] - 100))
                        for b in range(num_bins):
                            x = x_quant[i][g][w][sfb][b]
                            self.x_invquant[i][g][w][sfb][b] = math.copysign(abs(float(x)) ** (4/3), x) 
                            self.x_rescal[i][g][w][sfb][b] = gain * self.x_invquant[i][g][w][sfb][b]
        l_spec = self.x_rescal[0]
        r_spec = self.x_rescal[1]

        if self.block.cpe.ms_mask_present >= 1:
            params = self.block.cpe.params
            ics_info = self.block.cpe.ics_info
            for g in range(params.num_window_groups):
                for w in range(params.window_group_length[g]):
                    for sfb in range(ics_info.max_sfb):
                        if (self.block.cpe.ms_mask_present == 2 or self.block.cpe.ms_used[g][sfb]) and self.block.cpe.ics[1].section_data.sfb_cb[g][sfb] < 13:
                            num_bins = params.swb_offset[sfb+1] - params.swb_offset[sfb]
                            for b in range(num_bins):
                                tmp = l_spec[g][w][sfb][b] - r_spec[g][w][sfb][b]
                                l_spec[g][w][sfb][b] = l_spec[g][w][sfb][b] + r_spec[g][w][sfb][b]
                                r_spec[g][w][sfb][b] = tmp
        
        params = self.block.cpe.ics[1].params
        ics_info = self.block.cpe.ics[1].ics_info
        for g in range(params.num_window_groups):
            for w in range(params.window_group_length[g]):
                for sfb in range(ics_info.max_sfb):
                    sfb_cb = self.block.cpe.ics[1].section_data.sfb_cb[g][sfb]
                    is_intensity = 1 if sfb_cb == 14 else -1 if sfb_cb == 15 else 0
                    invert_intensity = (1 - 2 * self.block.cpe.ms_used[g][sfb]) if self.block.cpe.ms_mask_present == 1 else 1
                    if is_intensity:
                        scale = is_intensity * invert_intensity * (0.5 ** (0.25 * self.block.cpe.ics[1].scale_factor_data.sf[g][sfb]))
                        num_bins = params.swb_offset[sfb+1] - params.swb_offset[sfb]
                        for b in range(num_bins):
                            r_spec[g][w][sfb][b] = scale * l_spec[g][w][sfb][b]
    
        flat = [None] * 2
        for i in range(2):
            spec = l_spec if i == 0 else r_spec
            params = self.block.cpe.ics[i].params
            ics_info = self.block.cpe.ics[i].ics_info
            flat[i] = [None] * params.num_window_groups
            for g in range(params.num_window_groups):
                flat[i][g] = [None] * params.window_group_length[g]
                for w in range(params.window_group_length[g]):
                    flat[i][g][w] = [0] * params.swb_offset[-1]
                    for sfb in range(ics_info.max_sfb):
                        num_bins = params.swb_offset[sfb+1] - params.swb_offset[sfb]
                        for b in range(num_bins):
                            flat[i][g][w][params.swb_offset[sfb]+b] = spec[g][w][sfb][b]
        self.spec = flat

        samples = [None] * 2
        for i in range(2):
            params = self.block.cpe.ics[i].params
            ics_info = self.block.cpe.ics[i].ics_info
            samples[i] = [None] * params.num_window_groups
            for g in range(params.num_window_groups):
                samples[i][g] = [None] * params.window_group_length[g]
                for w in range(params.window_group_length[g]):
                    spectrum = self.spec[i][g][w]
                    if len(spectrum) == 0:
                        continue

                    idct = scipy.fft.idct(spectrum, type=4)
                    s = np.concatenate([idct, np.flip(idct) * -1])
                    n = ics.params.window_length
                    s = np.concatenate([s[n//2:n*2], s[0:n//2] * -1])
                    samples[i][g][w] = s
        self.samples = samples