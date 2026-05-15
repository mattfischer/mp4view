import stream
import analyzers.avc.parse

class AVCDecoderConfigurationRecord:
    def __init__(self, bytes, byte_start):
        bitstream = stream.Bitstream(bytes, byte_start)
        bitstream.start_syntax_item('AVCDecoderConfigurationRecord')
        self.configurationVersion = bitstream.getbits(8, 'configurationVersion')
        self.AVCProfileIndication = bitstream.getbits(8, 'AVCProfileIndication')
        self.profile_compatibility = bitstream.getbits(8, 'profile_compatibility')
        self.AVCLevelIndication = bitstream.getbits(8, 'AVCLevelIndication')
        reserved = bitstream.getbits(6)
        self.lengthSizeMinusOne = bitstream.getbits(2, 'lengthSizeMinusOne')
        reserved = bitstream.getbits(3)

        numOfSequenceParameterSets = bitstream.getbits(5)
        bitstream.start_syntax_item('SequenceParameterSets')
        self.sps_nals = []
        for i in range(numOfSequenceParameterSets):
            sequenceParameterSetLength = bitstream.getbits(16)
            bitstream.start_syntax_item('%i' % i)
            sps_bytes = bytes[bitstream.pos // 8: bitstream.pos // 8 + sequenceParameterSetLength + 1]
            sps_nal = analyzers.avc.parse.NAL()
            sps_nal.parse(sps_bytes, byte_start + bitstream.pos // 8, sequenceParameterSetLength, None)
            self.sps_nals.append(sps_nal)
            bitstream.pos += sequenceParameterSetLength * 8
            bitstream.append_syntax_item(sps_nal.syntax_item)
            bitstream.finish_syntax_item()
        bitstream.finish_syntax_item()

        numOfPictureParameterSets = bitstream.getbits(8)
        bitstream.start_syntax_item('PictureParameterSets')
        self.pps_nals = []
        for i in range(numOfPictureParameterSets):
            pictureParameterSetLength = bitstream.getbits(16)
            bitstream.start_syntax_item('%i' % i)
            pps_bytes = bytes[bitstream.pos // 8: bitstream.pos // 8 + pictureParameterSetLength + 1]
            pps_nal = analyzers.avc.parse.NAL()
            pps_nal.parse(pps_bytes, byte_start + bitstream.pos // 8, pictureParameterSetLength, None)
            self.pps_nals.append(pps_nal)
            bitstream.pos += pictureParameterSetLength * 8
            bitstream.append_syntax_item(pps_nal.syntax_item)
            bitstream.finish_syntax_item()
        bitstream.finish_syntax_item()
        
        self.syntax_item = bitstream.finish_syntax_item()
