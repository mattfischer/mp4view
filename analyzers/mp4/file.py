import struct
import io
from analyzers.mp4.es import ESDescriptor
import stream
from syntax import SyntaxItem

class Box:
    def __init__(self, bytestream, start):
        self.bytestream = bytestream
        self.start = start
        self.syntax_items = []
        self.syntax_item_stack = []

        self.bytestream.seek(start)

        self.size = self.bytestream.getuint32('Size')
        self.type = self.bytestream.getfixedstring(4, 'Type')
        if self.size == 1:
            self.size = self.bytestream.getuint64('Size (extended)')
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

class FullBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.version = self.bytestream.getuint8('Version')
        self.flags = self.bytestream.getint(3, '!I', 'Flags', 4)

class FileTypeBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.major_brand = self.bytestream.getfixedstring(4, 'Major Brand')
        self.minor_version = self.bytestream.getuint32('Minor Version')
        self.compatible_brands = []
        self.bytestream.start_syntax_item('Compatible Brands')
        while self.bytestream.pos < self.start + self.size:
            self.compatible_brands.append(self.bytestream.getfixedstring(4, 'Brand'))
        self.bytestream.finish_syntax_item()

    def box_name():
        return 'FileTypeBox'

    def __str__(self):
        return 'FileTypeBox: major_brand %s, minor_version %s, compatible_brands %s' % (self.major_brand, self.minor_version, self.compatible_brands)

class MovieBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'MovieBox'

    def __str__(self):
        return 'MovieBox'

class MovieHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('Creation Time')
            self.modification_time = self.bytestream.getuint64('Modification Time')
            self.timescale = self.bytestream.getuint32('Timescale')
            self.duration = self.bytestream.getuint64('Duration')
        else:
            self.creation_time = self.bytestream.getuint32('Creation Time')
            self.modification_time = self.bytestream.getuint32('Modification Time')
            self.timescale = self.bytestream.getuint32('Timescale')
            self.duration = self.bytestream.getuint32('Duration')
        self.rate = self.bytestream.getuint32('Rate')
        self.volume = self.bytestream.getuint16('Volume')
        reserved = self.bytestream.getuint16()
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.bytestream.start_syntax_item('Matrix')
        self.matrix = [self.bytestream.getuint32('Value') for i in range(9)]
        self.bytestream.finish_syntax_item()
        pre_defined = [self.bytestream.getuint32() for i in range(6)]
        self.next_track_ID = self.bytestream.getuint32('Next Track ID')

    def box_name():
        return 'MovieHeaderBox'

    def __str__(self):
        return 'MovieHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, rate %i, volume %i, matrix %s, next_track_ID %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.rate, self.volume, self.matrix, self.next_track_ID)

class TrackBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'TrackBox'

    def __str__(self):
        return 'TrackBox'

class TrackHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('Creation Time')
            self.modification_time = self.bytestream.getuint64('Modification Time')
            self.track_ID = self.bytestream.getuint32('Track ID')
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint64('Duration')
        else:
            self.creation_time = self.bytestream.getuint32('Creation Time')
            self.modification_time = self.bytestream.getuint32('Modification Time')
            self.track_ID = self.bytestream.getuint32('Track ID')
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint32('Duration')
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.layer = self.bytestream.getuint16('Layer')
        self.alternate_group = self.bytestream.getuint16('Alternate Group')
        self.volume = self.bytestream.getuint16('Volume')
        reserved = self.bytestream.getuint16()
        self.bytestream.start_syntax_item('Matrix')
        self.matrix = [self.bytestream.getuint32('Value') for i in range(9)]
        self.bytestream.finish_syntax_item()
        self.width = self.bytestream.getuint32('Width')
        self.height = self.bytestream.getuint32('Height')

    def box_name():
        return 'TrackHeaderBox'

    def __str__(self):
        return 'TrackHeaderBox: creation_time %i, modification_time %i, track_ID %i, duration %i, layer %i, alternate_group %i, volume %i, matrix %s, width %i, height %i' % (self.creation_time, self.modification_time, self.track_ID, self.duration, self.layer, self.alternate_group, self.volume, self.matrix, self.width, self.height)

class MediaBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'MediaBox'

    def __str__(self):
        return 'MediaBox'

class MediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('Creation Time')
            self.modification_time = self.bytestream.getuint64('Modification Time')
            self.timescale = self.bytestream.getuint32('Timescale')
            self.duration = self.bytestream.getuint64('Duration')
        else:
            self.creation_time = self.bytestream.getuint32('Creation Time')
            self.modification_time = self.bytestream.getuint32('Modification Time')
            self.timescale = self.bytestream.getuint32('Timescale')
            self.duration = self.bytestream.getuint32('Duration')
        self.language = self.bytestream.getuint16('Language')
        pre_defined = self.bytestream.getuint16()

    def box_name():
        return 'MediaHeaderBox'

    def __str__(self):
        return 'MediaHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, language %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.language)

class HandlerBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        pre_defined = self.bytestream.getuint32()
        self.handler_type = self.bytestream.getfixedstring(4, 'Handler Type')
        reserved = [self.bytestream.getuint32() for i in range(3)]
        self.name = self.bytestream.getstring(self.size, 'Name')

    def box_name():
        return 'HandlerBox'

    def __str__(self):
        return 'HandlerBox: handler_type %s, name %s' % (self.handler_type, self.name)

class MediaInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'MediaInformationBox'

    def __str__(self):
        return 'MediaInformationBox'

class SampleTableBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'SampleTableBox'

    def __str__(self):
        return 'SampleTableBox'

class SampleDescriptionBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32('Entry Count')
        self.boxes = []
        for i in range(entry_count):
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def box_name():
        return 'SampleDescriptionBox'

    def __str__(self):
        return 'SampleDescriptionBox'

class SampleEntry(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        reserved = [self.bytestream.getuint8() for i in range(6)]
        self.data_reference_index = self.bytestream.getuint16('Data Reference Index')

    def __str__(self):
        return 'SampleEntry: data_reference_index %i' % self.data_reference_index

class AudioSampleEntry(SampleEntry):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.channel_count = self.bytestream.getuint16('Channel Count')
        self.samplesize = self.bytestream.getuint16('Sample Size')
        pre_defined = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()
        self.sample_rate = self.bytestream.getuint32('Sample Rate')
        self.boxes = self.parseboxes()

    def box_name():
        return 'AudioSampleEntry'

    def __str__(self):
        return 'AudioSampleEntry: data_reference_index %i, channel_count %i, samplesize %i, sample_rate %i' % (self.data_reference_index, self.channel_count, self.samplesize, self.sample_rate)

class TimeToSampleBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32('Entry Count')
        self.entries = []
        self.bytestream.start_syntax_item('Entries')
        for i in range(entry_count):
            self.bytestream.start_syntax_item('%i' % i)
            tuple = (self.bytestream.getuint32('Time'), self.bytestream.getuint32('Sample'))
            self.entries.append(tuple)
            self.bytestream.finish_syntax_item()
        self.bytestream.finish_syntax_item()

    def box_name():
        return 'TimeToSampleBox'

    def __str__(self):
        return 'TimeToSampleBox: %i entries' % len(self.entries)

class DataInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.boxes = self.parseboxes()

    def box_name():
        return 'DataInformationBox'

    def __str__(self):
        return 'DataInformationBox'

class DataReferenceBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        entry_count = self.bytestream.getuint32('Entry Count')
        self.boxes = self.parseboxes()

    def box_name():
        return 'DataReferenceBox'

    def __str__(self):
        return 'DataReferenceBox'

class DataEntryUrlBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.url = self.bytestream.getstring(self.size, 'URL')
    
    def box_name():
        return 'DataEntryUrlBox'

    def __str__(self):
        return 'DataEntryUrlBox: url %s' % self.url

class SampleSizeBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.sample_size = self.bytestream.getuint32('Sample Size')
        self.sample_count = self.bytestream.getuint32('Sample Count')
        self.sample_sizes = []
        if self.sample_size == 0:
            self.bytestream.start_syntax_item('Sample Sizes')
            for i in range(self.sample_count):
                self.sample_sizes.append(self.bytestream.getuint32('%i' % i))
            self.bytestream.finish_syntax_item()

    def box_name():
        return 'SampleSizeBox'

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
        entry_count = self.bytestream.getuint32('Entry Count')
        self.entries = []
        self.bytestream.start_syntax_item('Entries')
        for i in range(entry_count):
            self.bytestream.start_syntax_item('%i' % i)
            tuple = (self.bytestream.getuint32('First Chunk'), self.bytestream.getuint32('Samples Per Chunk'), self.bytestream.getuint32())
            self.bytestream.finish_syntax_item()
            self.entries.append(tuple)
        self.bytestream.finish_syntax_item()

    def box_name():
        return 'SampleToChunkBox'

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
        self.bytestream.start_syntax_item('Entries')
        for i in range(entry_count):
            value = self.bytestream.getuint32('%i' % i)
            self.entries.append(value)
        self.bytestream.finish_syntax_item()

    def box_name():
        return 'ChunkOffsetBox'

    def __str__(self):
        return 'ChunkOffsetBox: %i entries' % len(self.entries)

    def get_offset(self, idx):
        return self.entries[idx - 1]

class FreeSpaceBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
    
    def box_name():
        return 'FreeSpaceBox'

    def __str__(self):
        return 'FreeSpaceBox'


class MediaDataBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
    
    def box_name():
        return 'MediaDataBox'

    def __str__(self):
        return 'MediaDataBox'

class SoundMediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        self.balance = self.bytestream.getuint16('Balance')
        reserved = self.bytestream.getuint16()

    def box_name():
        return 'SoundMediaHeaderBox'

    def __str__(self):
        return 'SoundMediaHeaderBox: balance %i' % self.balance

class ESDBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start)
        bytes = self.bytestream.read(self.start + self.size - self.bytestream.pos)
        self.descriptor = ESDescriptor(bytes)

    def box_name():
        return 'ESDBox'

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
    cls = mapping.get(type)
    if cls:
        bytestream.start_syntax_item(cls.box_name())
        box = cls(bytestream, start)
    else:
        bytestream.start_syntax_item('Box (\'%s\')' % type)
        box = Box(bytestream, start)
    bytestream.seek(start + box.size)
    box.syntax_item = bytestream.finish_syntax_item()
    return box

class File:
    def __init__(self, bytestream):
        self.bytestream = bytestream

        self.boxes = []
        while self.bytestream.pos < self.bytestream.size:
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def analyze(self):
        return [box.syntax_item for box in self.boxes]

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