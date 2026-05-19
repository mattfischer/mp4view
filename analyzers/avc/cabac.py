class Decoder:
    def __init__(self, bitstream, slice_header, sps, pps):
        self.bitstream = bitstream
        self.slice_header = slice_header
        self.sps = sps
        self.pps = pps

        self.init_context()

    def init_context(self):
        SliceQPY = 26 + self.pps.pic_init_qp_minus26 + self.slice_header.slice_qp_delta
