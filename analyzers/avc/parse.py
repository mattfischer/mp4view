import stream

class NAL:
    def parse(self, bytes, byte_start, length, avc_configuration):
        self.bitstream = stream.Bitstream(bytes, byte_start)
        self.bitstream.start_syntax_item('NAL')
        self.bitstream.pos += length * 8
        self.syntax_item = self.bitstream.finish_syntax_item()

class NALU:
    def parse(self, bytes, byte_start, avc_configuration):
        bitstream = stream.Bitstream(bytes, byte_start)
        bitstream.start_syntax_item('NALU')

        length_size = avc_configuration.avcConfig.lengthSizeMinusOne + 1

        total_length = 0
        self.nals = []
        while total_length < len(bytes):
            NALUnitLength = bitstream.getbits(8 * length_size, 'NALUnitLength')
            nal = NAL()
            total_length += length_size
            nal.parse(bytes[total_length:total_length + NALUnitLength], byte_start + total_length, NALUnitLength, avc_configuration)
            bitstream.append_syntax_item(nal.syntax_item)
            bitstream.pos += NALUnitLength * 8
            self.nals.append(nal)
            total_length += NALUnitLength
        self.syntax_item = bitstream.finish_syntax_item()