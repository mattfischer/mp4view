import struct
import io
from analyzers.mp4.es import ESDescriptor
import stream
from syntax import SyntaxItem

class Box:
    def __init__(self, bytestream, start):
        self.bytestream = bytestream
        self.start = start

        self.bytestream.seek(start)

        self.size = self.bytestream.getuint32()
        self.type = self.bytestream.getfixedstring(4)
        if self.size == 1:
            self.size = self.bytestream.getuint64()
        elif self.size == 0:
            self.size = self.bytestream.size - start

    def __str__(self):
        return 'Box: type %s' % self.type

    def print(self, prefix=''):
        print(prefix + str(self))
        if hasattr(self, 'boxes'):
            for box in self.boxes:
                box.print(prefix + '  ')

    def parseboxes(self):
        boxes = []
        while self.bytestream.pos < self.start + self.size:
            box = parsebox(self.bytestream)
            boxes.append(box)
            self.bytestream.seek(box.start + box.size)

        return boxes

    def findboxes(self, cls):
        boxes = []
        for box in getattr(self, 'boxes', []):
            if isinstance(box, cls):
                boxes.append(box)
        return boxes

    def findbox(self, cls):
        return self.findboxes(cls)[0]

    def analyze(self):
        return SyntaxItem('Box: \'%s\'' % self.type, self.start, self.size)

class FullBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.version = self.bytestream.getuint8()
        bytes = self.bytestream.read(3)
        self.flags = struct.unpack('!I', bytes.rjust(4))[0]

class FileTypeBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.major_brand = self.bytestream.getfixedstring(4)
        self.minor_version = self.bytestream.getuint32()
        self.compatible_brands = []
        while self.bytestream.pos < self.start + self.size:
            self.compatible_brands.append(self.bytestream.getfixedstring(4))

    def __str__(self):
        return 'FileTypeBox: major_brand %s, minor_version %s, compatible_brands %s' % (self.major_brand, self.minor_version, self.compatible_brands)

class MovieBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MovieBox'

class MovieHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64()
            self.modification_time = self.bytestream.getuint64()
            self.timescale = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint64()
        else:
            self.creation_time = self.bytestream.getuint32()
            self.modification_time = self.bytestream.getuint32()
            self.timescale = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint32()
        self.rate = self.bytestream.getuint32()
        self.volume = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.matrix = [self.bytestream.getuint32() for i in range(9)]
        pre_defined = [self.bytestream.getuint32() for i in range(6)]
        self.next_track_ID = self.bytestream.getuint32()

    def __str__(self):
        return 'MovieHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, rate %i, volume %i, matrix %s, next_track_ID %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.rate, self.volume, self.matrix, self.next_track_ID)

class TrackBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'TrackBox'

class TrackHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64()
            self.modification_time = self.bytestream.getuint64()
            self.track_ID = self.bytestream.getuint32()
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint64()
        else:
            self.creation_time = self.bytestream.getuint32()
            self.modification_time = self.bytestream.getuint32()
            self.track_ID = self.bytestream.getuint32()
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint32()
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.layer = self.bytestream.getuint16()
        self.alternate_group = self.bytestream.getuint16()
        self.volume = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()
        self.matrix = [self.bytestream.getuint32() for i in range(9)]
        self.width = self.bytestream.getuint32()
        self.height = self.bytestream.getuint32()

    def __str__(self):
        return 'TrackHeaderBox: creation_time %i, modification_time %i, track_ID %i, duration %i, layer %i, alternate_group %i, volume %i, matrix %s, width %i, height %i' % (self.creation_time, self.modification_time, self.track_ID, self.duration, self.layer, self.alternate_group, self.volume, self.matrix, self.width, self.height)

class MediaBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MediaBox'

class MediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64()
            self.modification_time = self.bytestream.getuint64()
            self.timescale = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint64()
        else:
            self.creation_time = self.bytestream.getuint32()
            self.modification_time = self.bytestream.getuint32()
            self.timescale = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint32()
        self.language = self.bytestream.getuint16()
        pre_defined = self.bytestream.getuint16()

    def __str__(self):
        return 'MediaHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, language %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.language)

class HandlerBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        pre_defined = self.bytestream.getuint32()
        self.handler_type = self.bytestream.getfixedstring(4)
        reserved = [self.bytestream.getuint32() for i in range(3)]
        self.name = self.bytestream.getstring(self.size)

    def __str__(self):
        return 'HandlerBox: handler_type %s, name %s' % (self.handler_type, self.name)

class MediaInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MediaInformationBox'

class SampleTableBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'SampleTableBox'

class SampleDescriptionBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32()
        self.boxes = []
        for i in range(entry_count):
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def __str__(self):
        return 'SampleDescriptionBox'

class SampleEntry(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        reserved = [self.bytestream.getuint8() for i in range(6)]
        self.data_reference_index = self.bytestream.getuint16()

    def __str__(self):
        return 'SampleEntry: data_reference_index %i' % self.data_reference_index

class AudioSampleEntry(SampleEntry):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.channel_count = self.bytestream.getuint16()
        self.samplesize = self.bytestream.getuint16()
        pre_defined = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()
        self.sample_rate = self.bytestream.getuint32()
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'AudioSampleEntry: data_reference_index %i, channel_count %i, samplesize %i, sample_rate %i' % (self.data_reference_index, self.channel_count, self.samplesize, self.sample_rate)

class TimeToSampleBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32()
        self.entries = []
        for i in range(entry_count):
            tuple = (self.bytestream.getuint32(), self.bytestream.getuint32())
            self.entries.append(tuple)

    def __str__(self):
        return 'TimeToSampleBox: %i entries' % len(self.entries)

class DataInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()
        
    def __str__(self):
        return 'DataInformationBox'

class DataReferenceBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32()
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'DataReferenceBox'

class DataEntryUrlBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.url = self.bytestream.getstring(self.size)
    
    def __str__(self):
        return 'DataEntryUrlBox: url %s' % self.url

class SampleSizeBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.sample_size = self.bytestream.getuint32()
        self.sample_count = self.bytestream.getuint32()
        self.sample_sizes = []
        if self.sample_size == 0:
            for i in range(self.sample_count):
                self.sample_sizes.append(self.bytestream.getuint32())
    
    def __str__(self):
        return 'SampleSizeBox: %i entries' % self.sample_count

    def get_size(self, idx):
        if self.sample_size != 0:
            return self.sample_size
        else:
            return self.sample_sizes[idx]
       
class SampleToChunkBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32()
        self.entries = []
        for i in range(entry_count):
            tuple = (self.bytestream.getuint32(), self.bytestream.getuint32(), self.bytestream.getuint32())
            self.entries.append(tuple)
    
    def __str__(self):
        return 'SampleToChunkBox: %i entries' % len(self.entries)

    def get_chunk(self, idx):
        first_sample = 0
        chunk = 1
        (first_chunk, samples_per_chunk, _) = self.entries[0]
        table_idx = 1
        (next_first_chunk, next_samples_per_chunk, _) = self.entries[table_idx]
        while first_sample + samples_per_chunk <= idx:
            chunk += 1
            if chunk == next_first_chunk:
                (first_chunk, samples_per_chunk) = (next_first_chunk, next_samples_per_chunk)
                table_idx += 1
                (next_first_chunk, next_samples_per_chunk, _) = self.entries[table_idx]
            first_sample += samples_per_chunk

        return (chunk, first_sample)

class ChunkOffsetBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32()
        self.entries = []
        for i in range(entry_count):
            self.entries.append(self.bytestream.getuint32())

    def __str__(self):
        return 'ChunkOffsetBox: %i entries' % len(self.entries)

    def get_offset(self, idx):
        return self.entries[idx - 1]

class FreeSpaceBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
    
    def __str__(self):
        return 'FreeSpaceBox'


class MediaDataBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
    
    def __str__(self):
        return 'MediaDataBox'

class SoundMediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.balance = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()

    def __str__(self):
        return 'SoundMediaHeaderBox: balance %i' % self.balance

class ESDBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        bytes = self.bytestream.read(self.start + self.size - self.bytestream.pos)
        self.descriptor = ESDescriptor(bytes)

    def __str__(self):
        return 'ESDBox'

    def print(self, prefix):
        print(prefix + str(self))
        self.descriptor.print(prefix + '  ')

def parsebox(bytestream):
    start = bytestream.pos
    bytestream.seek(start + 4)
    bytes = bytestream.read(4)
    type = bytes.decode()

    mapping = {
        'ftyp' : FileTypeBox,
        'moov' : MovieBox,
        'mvhd' : MovieHeaderBox,
        'trak' : TrackBox,
        'tkhd' : TrackHeaderBox,
        'mdia' : MediaBox,
        'mdhd' : MediaHeaderBox,
        'smhd' : SoundMediaHeaderBox,
        'hdlr' : HandlerBox,
        'minf' : MediaInformationBox,
        'stbl' : SampleTableBox,
        'stsd' : SampleDescriptionBox,
        'stts' : TimeToSampleBox,
        'dinf' : DataInformationBox,
        'dref' : DataReferenceBox,
        'url ' : DataEntryUrlBox,
        'stsz' : SampleSizeBox,
        'stsc' : SampleToChunkBox,
        'stco' : ChunkOffsetBox,
        'free' : FreeSpaceBox,
        'mdat' : MediaDataBox,
        'mp4a' : AudioSampleEntry,
        'esds' : ESDBox
    }
    cls = mapping.get(type, Box)
    return cls(bytestream, start)

class File:
    def __init__(self, bytestream):
        self.bytestream = bytestream

        self.boxes = []
        while self.bytestream.pos < self.bytestream.size:
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def findboxes(self, cls):
        boxes = []
        for box in self.boxes:
            if isinstance(box, cls):
                boxes.append(box)
        return boxes

    def findbox(self, cls):
        return self.findboxes(cls)[0]

    def es_descriptor(self):
        tracks = self.findbox(MovieBox).findboxes(TrackBox)
        track = tracks[0]
        sample_table = track.findbox(MediaBox).findbox(MediaInformationBox).findbox(SampleTableBox)
        esd_box = sample_table.findbox(SampleDescriptionBox).findbox(AudioSampleEntry).findbox(ESDBox)
        return esd_box.descriptor

    def getsample(self, idx):
        tracks = self.findbox(MovieBox).findboxes(TrackBox)
        track = tracks[0]
        sample_table = track.findbox(MediaBox).findbox(MediaInformationBox).findbox(SampleTableBox)
        sample_sizes = sample_table.findbox(SampleSizeBox)
        sample_to_chunk = sample_table.findbox(SampleToChunkBox)
        chunk_offsets = sample_table.findbox(ChunkOffsetBox)

        size = sample_sizes.get_size(idx)
        (chunk, first_sample) = sample_to_chunk.get_chunk(idx)
        skip_size = 0
        for sample in range(first_sample, idx):
            skip_size += sample_sizes.get_size(sample)
        offset = chunk_offsets.get_offset(chunk)
        location = offset + skip_size
        
        self.bytestream.file.seek(location)
        bytes = self.bytestream.file.read(size)
        return bytes