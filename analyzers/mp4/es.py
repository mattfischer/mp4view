import stream

class BaseDescriptor:
    def __init__(self, bitstream):
        self.bitstream = bitstream
        self.tag = self.bitstream.getbits(8, 'tag')

        self.bitstream.start_syntax_item()
        nextByte = self.bitstream.getbits(1)
        sizeOfInstance = self.bitstream.getbits(7)
        while nextByte:
            nextByte = self.bitstream.getbits(1)
            sizeOfInstance = sizeOfInstance << 7 | self.bitstream.getbits(7)
        self.size = sizeOfInstance
        bitstream.finish_syntax_item('size: %i' % self.size)

class DecoderConfigDescriptor(BaseDescriptor):
    def __init__(self, bitstream):
        bitstream.start_syntax_item('DecoderConfigDescriptor')
        super().__init__(bitstream)
        self.objectTypeIndication = self.bitstream.getbits(8, 'objectTypeIndication')
        self.streamType = self.bitstream.getbits(6, 'streamType')
        self.upStream = self.bitstream.getbits(1, 'upStream')
        reserved = self.bitstream.getbits(1)
        self.bufferSizeDB = self.bitstream.getbits(24, 'bufferSizeDB')
        self.maxBitrate = self.bitstream.getbits(32, 'maxBitrate')
        self.avgBitrate = self.bitstream.getbits(32, 'avgBitrate')
        if self.objectTypeIndication == 0x40:
            self.decSpecificInfo = AudioSpecificConfig(self.bitstream)
        bitstream.finish_syntax_item()

class AudioSpecificConfig(BaseDescriptor):
    def __init__(self, bitstream):
        bitstream.start_syntax_item('AudioSpecificConfig')
        super().__init__(bitstream)
        self.audioObjectType = self.GetAudioObjectType()
        self.samplingFrequencyIndex = self.bitstream.getbits(4, 'samplingFrequencyIndex')
        if self.samplingFrequencyIndex == 0xf:
            self.samplingFrequency = self.bitstream.getbits(24, 'samplingFrequency')
        self.channelConfiguration = self.bitstream.getbits(4, 'channelConfiguration')
        self.sbrPresentFlag = -1
        if self.audioObjectType == 5:
            self.extensionAudioType = self.audioObjectType
            self.sbrPresentFlag = 1
            self.extensionSamplingFrequencyIndex = self.bitstream.getbits(4, 'extensionSamplingFrequencyIndex')
            if self.extensionSamplingFrequencyIndex == 0xf:
                self.extensionSamplingFrequency = self.bitstream.getbits(24, 'extensionSamplingFrequency')
            self.audioObjectType = self.GetAudioObjectType()
        else:
            self.extensionAudioObjectType = 0
        
        if self.audioObjectType in (1, 2, 3, 4, 6, 7, 17, 19, 20, 21, 22, 23):
            self.specificConfig = GASpecificConfig(self.bitstream, self.samplingFrequencyIndex, self.channelConfiguration, self.audioObjectType)
        bitstream.finish_syntax_item()

    def GetAudioObjectType(self):
        self.bitstream.start_syntax_item()
        audioObjectType = self.bitstream.getbits(5)
        if audioObjectType == 31:
            audioObjectType = 32 + self.bitstream.getbits(6)
        self.bitstream.finish_syntax_item('audioObjectType: %i' % audioObjectType)

        return audioObjectType

class GASpecificConfig:
    def __init__(self, bitstream, samplingFrequencyIndex, channelConfiguration, audioObjectType):
        self.bitstream = bitstream
        self.bitstream.start_syntax_item('GASpecificConfig')
        self.frameLengthFlag = self.bitstream.getbits(1, 'frameLengthFlag')
        self.dependsOnCoreCoder = self.bitstream.getbits(1, 'dependsOnCoreCoder')
        if self.dependsOnCoreCoder:
            self.coreCoderDelay = self.bitstream.getbits(24, 'coreCoderDelay')
        self.extensionFlag = self.bitstream.getbits(1, 'extensionFlag')
        if not channelConfiguration:
            self.programConfigElement = ProgramConfigElement(self.bitstream)
        if audioObjectType in (6, 20):
            self.layerNr = self.bitstream.getbits(3, 'layerNr')
        if self.extensionFlag:
            if audioObjectType == 22:
                self.numOfSubFrame = self.bitstream.getbits(5, 'numOfSubFrame')
                self.layer_length = self.bitstream.getbits(11, 'layer_length')
            if audioObjectType in (17, 19, 20, 23):
                self.aacSectionDataResilienceFlag = self.bitstream.getbits(1, 'aacSectionDataResilienceFlag')
                self.aacScalefactorDataResilienceFlag = self.bitstream.getbits(1, 'aacScalefactorDataResilienceFlag')
                self.aacSpectralDataResilienceFlag = self.bitstream.getbits(1, 'aacSpectralDataResilienceFlag')
            self.extensionFlag3 = self.bitstream.getbits(1, 'extensionFlag3')
        self.bitstream.finish_syntax_item()

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
            self.dependsOn_ES_ID = self.bitstream.getbits(16, 'dependsOn_ES_ID')        
        if self.URL_Flag:
            URLlength = self.bitstream.getbits(8)
            self.URLstring = self.bitstream.getstring(URLlength, 'URLstring')
        if self.OCRstreamFlag:
            self.OCR_ES_Id = self.bitstream.getbits(16, 'OCR_ES_ID')
        self.decConfigDescr = DecoderConfigDescriptor(self.bitstream)
        self.syntax_item = bitstream.finish_syntax_item()
