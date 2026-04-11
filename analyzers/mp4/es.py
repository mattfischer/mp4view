import stream

class BaseDescriptor:
    def __init__(self, bitstream):
        self.bitstream = bitstream
        self.tag = self.bitstream.getbits(8)
        nextByte = self.bitstream.getbits(1)
        sizeOfInstance = self.bitstream.getbits(7)
        while nextByte:
            nextByte = self.bitstream.getbits(1)
            sizeOfInstance = sizeOfInstance << 7 | self.bitstream.getbits(7)
        self.size = sizeOfInstance

class DecoderConfigDescriptor(BaseDescriptor):
    def __init__(self, bitstream):
        super().__init__(bitstream)
        self.objectTypeIndication = self.bitstream.getbits(8)
        self.streamType = self.bitstream.getbits(6)
        self.upStream = self.bitstream.getbits(1)
        reserved = self.bitstream.getbits(1)
        self.bufferSizeDB = self.bitstream.getbits(24)
        self.maxBitrate = self.bitstream.getbits(32)
        self.avbBitrate = self.bitstream.getbits(32)
        if self.objectTypeIndication == 0x40:
            self.decSpecificInfo = AudioSpecificConfig(self.bitstream)

    def __str__(self):
        return 'DecoderConfigDescriptor: objectTypeIndication 0x%x, streamType 0x%x' % (self.objectTypeIndication, self.streamType)

    def print(self, prefix):
        print(prefix + str(self))
        self.decSpecificInfo.print(prefix + '  ')

class AudioSpecificConfig(BaseDescriptor):
    def __init__(self, bitstream):
        super().__init__(bitstream)
        self.audioObjectType = self.GetAudioObjectType()
        self.samplingFrequencyIndex = self.bitstream.getbits(4)
        if self.samplingFrequencyIndex == 0xf:
            self.samplingFrequency = self.bitstream.getbits(24)
        self.channelConfiguration = self.bitstream.getbits(4)
        self.sbrPresentFlag = -1
        if self.audioObjectType == 5:
            self.extensionAudioType = self.audioObjectType
            self.sbrPresentFlag = 1
            self.extensionSamplingFrequencyIndex = self.bitstream.getbits(4)
            if self.extensionSamplingFrequencyIndex == 0xf:
                self.extensionSamplingFrequency = self.bitstream.getbits(24)
            self.audioObjectType = self.GetAudioObjectType()
        else:
            self.extensionAudioObjectType = 0
        
        if self.audioObjectType in (1, 2, 3, 4, 6, 7, 17, 19, 20, 21, 22, 23):
            self.specificConfig = GASpecificConfig(self.bitstream, self.samplingFrequencyIndex, self.channelConfiguration, self.audioObjectType)

    def __str__(self):
        return 'AudioSpecificConfig: type %i' % self.audioObjectType

    def print(self, prefix=''):
        print(prefix + str(self))
        print(prefix + '  ' + str(self.specificConfig))

    def GetAudioObjectType(self):
        audioObjectType = self.bitstream.getbits(5)
        if audioObjectType == 31:
            audioObjectType = 32 + self.bitstream.getbits(6)
        return audioObjectType

class GASpecificConfig:
    def __init__(self, bitstream, samplingFrequencyIndex, channelConfiguration, audioObjectType):
        self.bitstream = bitstream
        self.frameLengthFlag = self.bitstream.getbits(1)
        self.dependsOnCoreCoder = self.bitstream.getbits(1)
        if self.dependsOnCoreCoder:
            self.coreCoderDelay = self.bitstream.getbits(24)
        self.extensionFlag = self.bitstream.getbits(1)
        if not channelConfiguration:
            self.programConfigElement = ProgramConfigElement(self.bitstream)
        if audioObjectType in (6, 20):
            self.layerNr = self.bitstream.getbits(3)
        if self.extensionFlag:
            if audioObjectType == 22:
                self.numOfSubFrame = self.bitstream.getbits(5)
                self.layer_length = self.bitstream.getbits(11)
            if audioObjectType in (17, 19, 20, 23):
                self.aacSectionDataResilienceFlag = self.bitstream.getbits(1)
                self.aacScalefactorDataResilienceFlag = self.bitstream.getbits(1)
                self.aacSpectralDataResilienceFlag = self.bitstream.getbits(1)
            self.extensionFlag3 = self.bitstream.getbits(1)

    def __str__(self):
        return 'GASpecificConfig'

class ESDescriptor(BaseDescriptor):
    def __init__(self, bytes):
        bitstream = stream.Bitstream(bytes)
        super().__init__(bitstream)
        self.ES_ID = self.bitstream.getbits(16)
        self.streamDependenceFlag = self.bitstream.getbits(1)
        self.URL_Flag = self.bitstream.getbits(1)
        self.OCRstreamFlag = self.bitstream.getbits(1)
        self.streamPriority = self.bitstream.getbits(5)
        if self.streamDependenceFlag:
            self.dependsOn_ES_ID = self.bitstream.getbits(16)        
        if self.URL_Flag:
            URLlength = self.bitstream.getbits(8)
            self.URLstring = self.bitstream.getstring(URLlength)
        if self.OCRstreamFlag:
            self.OCR_ES_Id = self.bitstream.getbits(16)
        self.decConfigDescr = DecoderConfigDescriptor(self.bitstream)

    def __str__(self):
        return 'ESDescriptor: ES_ID 0x%x' % self.ES_ID

    def print(self, prefix=''):
        print(prefix + str(self))
        self.decConfigDescr.print(prefix + '  ')