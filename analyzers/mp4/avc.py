import stream

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
        for i in range(numOfSequenceParameterSets):
            sequenceParameterSetLength = bitstream.getbits(16)
            bitstream.start_syntax_item('%i' % i)
            sequenceParameterSetNALUnit = bitstream.getbits(sequenceParameterSetLength * 8)
            bitstream.finish_syntax_item()
        bitstream.finish_syntax_item()

        numOfPictureParameterSets = bitstream.getbits(8)
        bitstream.start_syntax_item('PictureParameterSets')
        for i in range(numOfPictureParameterSets):
            pictureParameterSetLength = bitstream.getbits(16)
            bitstream.start_syntax_item('%i' % i)
            pictureParameterSetNALUnit = bitstream.getbits(pictureParameterSetLength * 8)
            bitstream.finish_syntax_item()
        bitstream.finish_syntax_item()
        
        self.syntax_item = bitstream.finish_syntax_item()
