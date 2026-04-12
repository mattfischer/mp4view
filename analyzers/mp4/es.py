import stream

from syntax import SyntaxItem

class BaseDescriptor:
    def __init__(self, bitstream):
        self.bitstream = bitstream
        self.tag = self.bitstream.getbits(8, 'Tag')
        start = self.bitstream.pos // 8
        nextByte = self.bitstream.getbits(1)
        sizeOfInstance = self.bitstream.getbits(7)
        while nextByte:
            nextByte = self.bitstream.getbits(1)
            sizeOfInstance = sizeOfInstance << 7 | self.bitstream.getbits(7)
        end = self.bitstream.pos // 8
        size = max(end - start, 1)
        self.size = sizeOfInstance
        bitstream.append_syntax_item(SyntaxItem('Size: %i' % self.size, start + bitstream.byte_start, size))

class DecoderConfigDescriptor(BaseDescriptor):
    def __init__(self, bitstream):
        bitstream.start_syntax_item('DecoderConfigDescriptor')
        super().__init__(bitstream)
        self.objectTypeIndication = self.bitstream.getbits(8, 'Object Type Indication')
        self.streamType = self.bitstream.getbits(6, 'Stream Type')
        self.upStream = self.bitstream.getbits(1, 'Up Stream')
        reserved = self.bitstream.getbits(1)
        self.bufferSizeDB = self.bitstream.getbits(24, 'Buffer Size DB')
        self.maxBitrate = self.bitstream.getbits(32, 'Max Bitrate')
        self.avgBitrate = self.bitstream.getbits(32, 'Average Bitrate')
        if self.objectTypeIndication == 0x40:
            self.decSpecificInfo = AudioSpecificConfig(self.bitstream)
        bitstream.finish_syntax_item()

    def __str__(self):
        return 'DecoderConfigDescriptor: objectTypeIndication 0x%x, streamType 0x%x' % (self.objectTypeIndication, self.streamType)

    def print(self, prefix):
        print(prefix + str(self))
        self.decSpecificInfo.print(prefix + '  ')

class AudioSpecificConfig(BaseDescriptor):
    def __init__(self, bitstream):
        bitstream.start_syntax_item('AudioSpecificConfig')
        super().__init__(bitstream)
        self.audioObjectType = self.GetAudioObjectType()
        self.samplingFrequencyIndex = self.bitstream.getbits(4, 'Sampling Frequency Index')
        if self.samplingFrequencyIndex == 0xf:
            self.samplingFrequency = self.bitstream.getbits(24, 'Sampling Frequency')
        self.channelConfiguration = self.bitstream.getbits(4, 'Channel Configuration')
        self.sbrPresentFlag = -1
        if self.audioObjectType == 5:
            self.extensionAudioType = self.audioObjectType
            self.sbrPresentFlag = 1
            self.extensionSamplingFrequencyIndex = self.bitstream.getbits(4, 'Extension Sampling Frequency Index')
            if self.extensionSamplingFrequencyIndex == 0xf:
                self.extensionSamplingFrequency = self.bitstream.getbits(24, 'Extension Sampling Frequency')
            self.audioObjectType = self.GetAudioObjectType()
        else:
            self.extensionAudioObjectType = 0
        
        if self.audioObjectType in (1, 2, 3, 4, 6, 7, 17, 19, 20, 21, 22, 23):
            self.specificConfig = GASpecificConfig(self.bitstream, self.samplingFrequencyIndex, self.channelConfiguration, self.audioObjectType)
        bitstream.finish_syntax_item()

    def __str__(self):
        return 'AudioSpecificConfig: type %i' % self.audioObjectType

    def print(self, prefix=''):
        print(prefix + str(self))
        print(prefix + '  ' + str(self.specificConfig))

    def GetAudioObjectType(self):
        start = self.bitstream.pos // 8
        audioObjectType = self.bitstream.getbits(5)
        if audioObjectType == 31:
            audioObjectType = 32 + self.bitstream.getbits(6)
        end = self.bitstream.pos // 8
        size = max(end - start, 1)
        self.bitstream.append_syntax_item(SyntaxItem('Audio Object Type: %i' % audioObjectType, start + self.bitstream.byte_start, size))

        return audioObjectType

class GASpecificConfig:
    def __init__(self, bitstream, samplingFrequencyIndex, channelConfiguration, audioObjectType):
        self.bitstream = bitstream
        self.bitstream.start_syntax_item('GASpecificConfig')
        self.frameLengthFlag = self.bitstream.getbits(1, 'Frame Length Flag')
        self.dependsOnCoreCoder = self.bitstream.getbits(1, 'Depends On Core Coder')
        if self.dependsOnCoreCoder:
            self.coreCoderDelay = self.bitstream.getbits(24, 'Core Coder Delay')
        self.extensionFlag = self.bitstream.getbits(1, 'Extension Flag')
        if not channelConfiguration:
            self.programConfigElement = ProgramConfigElement(self.bitstream)
        if audioObjectType in (6, 20):
            self.layerNr = self.bitstream.getbits(3, 'Layer Number')
        if self.extensionFlag:
            if audioObjectType == 22:
                self.numOfSubFrame = self.bitstream.getbits(5, 'Number of Subframe')
                self.layer_length = self.bitstream.getbits(11, 'Layer Length')
            if audioObjectType in (17, 19, 20, 23):
                self.aacSectionDataResilienceFlag = self.bitstream.getbits(1, 'AAC Section Data Resilience Flag')
                self.aacScalefactorDataResilienceFlag = self.bitstream.getbits(1, 'AAC Scalefactor Data Resilience Flag')
                self.aacSpectralDataResilienceFlag = self.bitstream.getbits(1, 'AAC Spectral Data Resilience Flag')
            self.extensionFlag3 = self.bitstream.getbits(1, 'Extension Flag 3')
        self.bitstream.finish_syntax_item()

    def __str__(self):
        return 'GASpecificConfig'

class ESDescriptor(BaseDescriptor):
    def __init__(self, bytes, byte_start):
        bitstream = stream.Bitstream(bytes, byte_start)
        bitstream.start_syntax_item('ESDescriptor')
        super().__init__(bitstream)
        self.ES_ID = self.bitstream.getbits(16, 'ES_ID')
        self.streamDependenceFlag = self.bitstream.getbits(1)
        self.URL_Flag = self.bitstream.getbits(1)
        self.OCRstreamFlag = self.bitstream.getbits(1)
        self.streamPriority = self.bitstream.getbits(5)
        if self.streamDependenceFlag:
            self.dependsOn_ES_ID = self.bitstream.getbits(16, 'Depends On ES_ID')        
        if self.URL_Flag:
            URLlength = self.bitstream.getbits(8)
            self.URLstring = self.bitstream.getstring(URLlength, 'URL')
        if self.OCRstreamFlag:
            self.OCR_ES_Id = self.bitstream.getbits(16, 'OCR ES_ID')
        self.decConfigDescr = DecoderConfigDescriptor(self.bitstream)
        self.syntax_item = bitstream.finish_syntax_item()

    def __str__(self):
        return 'ESDescriptor: ES_ID 0x%x' % self.ES_ID

    def print(self, prefix=''):
        print(prefix + str(self))
        self.decConfigDescr.print(prefix + '  ')