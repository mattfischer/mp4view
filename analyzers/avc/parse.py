import stream
import syntax

class AVCBitstream(stream.Bitstream):
    def __init__(self, bytes, byte_start):
        super(AVCBitstream, self).__init__(bytes, byte_start)

    def getbytes(self, start, end):
        return self.bytes[start:end]

    def get_exp_golomb(self):
        leading_zero_bits = 0
        while True:
            b = self.getbit()
            if b:
                break
            else:
                leading_zero_bits += 1

        val = (1 << leading_zero_bits) - 1 + self.getbits(leading_zero_bits)
        return val

    def get_ue(self, name=None, format=None):
        self.start_syntax_item()

        val = self.get_exp_golomb()

        title = None
        if name:
            if format:
                title = '%s: %s' % (name, format(val))
            else:
                title = '%s: %i' % (name, val)
        self.finish_syntax_item(title)
        return val

class ParseObject:
    pass

enum_nal_unit_type = syntax.format_enum({
    0: 'Unspecified',
    1: 'Coded slice',
    2: 'Coded slice data partition A',
    3: 'Coded slice data partition B',
    4: 'Coded slice data partition C',
    5: 'Coded slice of an IDR picture',
    6: 'Supplemental enhancement information (SEI)',
    7: 'Sequence parameter set',
    8: 'Picture parameter set',
    9: 'Picture delimiter',
    10: 'End of sequence',
    11: 'End of stream',
    12: 'Filler data'
})

enum_slice_type = syntax.format_enum({
    0: 'P (P slice)',
    1: 'B (B slice)',
    2: 'I (I slice)',
    3: 'SP (SP slice)',
    4: 'SI (SI slice)',
    5: 'P (P slice)',
    6: 'B (B slice)',
    7: 'I (I slice)',
    8: 'SP (SP slice)',
    9: 'SI (SI slice)'
})

class NAL:
    def parse(self, bytes, byte_start, length, avc_configuration):
        self.bitstream = AVCBitstream(bytes, byte_start)

        self.bitstream.start_syntax_item('NAL')
        forbidden_zero_bit = self.bitstream.getbits(1)
        self.nal_ref_idc = self.bitstream.getbits(2, 'nal_ref_idc')
        self.nal_unit_type = self.bitstream.getbits(5, 'nal_unit_type', format=enum_nal_unit_type)

        self.parse_nal(avc_configuration)
        
        self.syntax_item = self.bitstream.finish_syntax_item()

    def parse_nal(self, avc_configuration):
        if self.nal_unit_type == 1:
            self.slice_layer = self.parse_slice_layer_without_partitioning(avc_configuration)
        elif self.nal_unit_type == 5:
            self.slice_layer = self.parse_slice_layer_without_partitioning(avc_configuration)
        elif self.nal_unit_type == 6:
            pass

    def parse_slice_layer_without_partitioning(self, avc_configuration):
        self.bitstream.start_syntax_item('slice_layer_without_partitioning')
        slice_layer = ParseObject()
        slice_layer.slice_header = self.parse_slice_header(avc_configuration)
        slice_layer.slice_data = self.parse_slice_data()
        self.bitstream.finish_syntax_item()
        return slice_layer

    def parse_slice_header(self, avc_configuration):
        self.bitstream.start_syntax_item('slice_header')
        slice_header = ParseObject()
        slice_header.first_mb_in_slice = self.bitstream.get_ue('first_mb_in_slice')
        slice_header.slice_type = self.bitstream.get_ue('slice_type', format=enum_slice_type)
        slice_header.pic_parameter_set_id = self.bitstream.get_ue('pic_parameter_set_id')
        self.bitstream.finish_syntax_item()
        return slice_header

    def parse_slice_data(self):
        self.bitstream.start_syntax_item('slice_data')
        slice_data = ParseObject()

        self.bitstream.finish_syntax_item()
        return slice_data

class NALU:
    def parse(self, bytes, byte_start, avc_configuration):
        bitstream = stream.Bitstream(bytes, byte_start)
        bitstream.start_syntax_item('NALU')

        length_size = avc_configuration.avcConfig.lengthSizeMinusOne + 1

        total_length = 0
        self.nals = []
        while total_length < len(bytes):
            NALUnitLength = bitstream.getbits(8 * length_size)
            nal = NAL()
            total_length += length_size
            nal.parse(bytes[total_length:total_length + NALUnitLength], byte_start + total_length, NALUnitLength, avc_configuration)
            bitstream.append_syntax_item(nal.syntax_item)
            bitstream.pos += NALUnitLength * 8
            self.nals.append(nal)
            total_length += NALUnitLength
        self.syntax_item = bitstream.finish_syntax_item()