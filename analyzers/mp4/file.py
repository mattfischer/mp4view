import struct
import io
from analyzers.mp4.es import ESDescriptor
import stream
from syntax import SyntaxItem

class Box:
    def start_syntax_item(self, name):
        self.syntax_item_stack.append((name, self.bytestream.pos, []))

    def finish_syntax_item(self):
        (name, start, children) = self.syntax_item_stack.pop()
        size = 0
        for child in children:
            size += child.size
        item = SyntaxItem(name, start, size, children)
        self.append_syntax_item(item)

    def append_syntax_item(self, item):
        if len(self.syntax_item_stack) > 0:
            (_, _, children) = self.syntax_item_stack[-1]
            children.append(item)
        else:
            self.syntax_items.append(item)

    def parse_uint8(self, name=None):
        start = self.bytestream.pos
        size = 1
        value = self.bytestream.getuint8()
        if name:
            self.append_syntax_item(SyntaxItem('%s: %i' % (name, value), start, size))
        return value

    def parse_uint16(self, name=None):
        start = self.bytestream.pos
        size = 2
        value = self.bytestream.getuint16()
        if name:
            self.append_syntax_item(SyntaxItem('%s: %i' % (name, value), start, size))
        return value

    def parse_uint32(self, name=None):
        start = self.bytestream.pos
        size = 4
        value = self.bytestream.getuint32()
        if name:
            self.append_syntax_item(SyntaxItem('%s: %i' % (name, value), start, size))
        return value

    def parse_uint64(self, name=None):
        start = self.bytestream.pos
        size = 8
        value = self.bytestream.getuint64()
        if name:
            self.append_syntax_item(SyntaxItem('%s: %i' % (name, value), start, size))
        return value

    def parse_fixedstring(self, length, name=None):
        start = self.bytestream.pos
        size = length
        value = self.bytestream.getfixedstring(length)
        if name:
            display = value
            if display[0] == '\0':
                display = '<null>'
            self.append_syntax_item(SyntaxItem('%s: \'%s\'' % (name, display), start, size))
        return value

    def parse_string(self, maxsize, name=None):
        start = self.bytestream.pos
        value = self.bytestream.getstring(maxsize)
        size = self.bytestream.pos - start
        if name:
            self.append_syntax_item(SyntaxItem('%s: \'%s\'' % (name, value), start, size))
        return value

    def __init__(self, bytestream, start, name=''):
        self.bytestream = bytestream
        self.start = start
        self.box_name = name
        self.syntax_items = []
        self.syntax_item_stack = []

        self.bytestream.seek(start)

        self.size = self.parse_uint32('Size')
        self.type = self.parse_fixedstring(4, 'Type')
        if self.size == 1:
            self.size = self.parse_uint64('Size (extended)')
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
        children = self.syntax_items
        if hasattr(self, 'boxes'):
            children += [box.analyze() for box in self.boxes]
        if self.box_name != '':
            name = self.box_name
        else:
            name = 'Box (\'%s\')' % self.type
        return SyntaxItem(name, self.start, self.size, children)

class FullBox(Box):
    def __init__(self, bytestream, start, name):
        super().__init__(bytestream, start, name)
        self.version = self.parse_uint8('Version')
        bytes = self.bytestream.read(3)
        self.flags = struct.unpack('!I', bytes.rjust(4))[0]

class FileTypeBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'FileTypeBox')
        self.major_brand = self.parse_fixedstring(4, 'Major Brand')
        self.minor_version = self.parse_uint32('Minor Version')
        self.compatible_brands = []
        self.start_syntax_item('Compatible Brands')
        while self.bytestream.pos < self.start + self.size:
            self.compatible_brands.append(self.parse_fixedstring(4, 'Brand'))
        self.finish_syntax_item()

    def __str__(self):
        return 'FileTypeBox: major_brand %s, minor_version %s, compatible_brands %s' % (self.major_brand, self.minor_version, self.compatible_brands)

class MovieBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MovieBox')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MovieBox'

class MovieHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MovieHeaderBox')
        if self.version == 1:
            self.creation_time = self.parse_uint64('Creation Time')
            self.modification_time = self.parse_uint64('Modification Time')
            self.timescale = self.parse_uint32('Timescale')
            self.duration = self.parse_uint64('Duration')
        else:
            self.creation_time = self.parse_uint32('Creation Time')
            self.modification_time = self.parse_uint32('Modification Time')
            self.timescale = self.parse_uint32('Timescale')
            self.duration = self.parse_uint32('Duration')
        self.rate = self.parse_uint32('Rate')
        self.volume = self.parse_uint16('Volume')
        reserved = self.parse_uint16()
        reserved = [self.parse_uint32() for i in range(2)]
        self.start_syntax_item('Matrix')
        self.matrix = [self.parse_uint32('Value') for i in range(9)]
        self.finish_syntax_item()
        pre_defined = [self.parse_uint32() for i in range(6)]
        self.next_track_ID = self.parse_uint32('Next Track ID')

    def __str__(self):
        return 'MovieHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, rate %i, volume %i, matrix %s, next_track_ID %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.rate, self.volume, self.matrix, self.next_track_ID)

class TrackBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TrackBox')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'TrackBox'

class TrackHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TrackHeaderBox')
        if self.version == 1:
            self.creation_time = self.parse_uint64('Creation Time')
            self.modification_time = self.parse_uint64('Modification Time')
            self.track_ID = self.parse_uint32('Track ID')
            reserved = self.parse_uint32()
            self.duration = self.parse_uint64('Duration')
        else:
            self.creation_time = self.parse_uint32('Creation Time')
            self.modification_time = self.parse_uint32('Modification Time')
            self.track_ID = self.parse_uint32('Track ID')
            reserved = self.parse_uint32()
            self.duration = self.parse_uint32('Duration')
        reserved = [self.parse_uint32() for i in range(2)]
        self.layer = self.parse_uint16('Layer')
        self.alternate_group = self.parse_uint16('Alternate Group')
        self.volume = self.parse_uint16('Volume')
        reserved = self.parse_uint16()
        self.start_syntax_item('Matrix')
        self.matrix = [self.parse_uint32('Value') for i in range(9)]
        self.finish_syntax_item()
        self.width = self.parse_uint32('Width')
        self.height = self.parse_uint32('Height')

    def __str__(self):
        return 'TrackHeaderBox: creation_time %i, modification_time %i, track_ID %i, duration %i, layer %i, alternate_group %i, volume %i, matrix %s, width %i, height %i' % (self.creation_time, self.modification_time, self.track_ID, self.duration, self.layer, self.alternate_group, self.volume, self.matrix, self.width, self.height)

class MediaBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaBox')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MediaBox'

class MediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaHeaderBox')
        if self.version == 1:
            self.creation_time = self.parse_uint64('Creation Time')
            self.modification_time = self.parse_uint64('Modification Time')
            self.timescale = self.parse_uint32('Timescale')
            self.duration = self.parse_uint64('Duration')
        else:
            self.creation_time = self.parse_uint32('Creation Time')
            self.modification_time = self.parse_uint32('Modification Time')
            self.timescale = self.parse_uint32('Timescale')
            self.duration = self.parse_uint32('Duration')
        self.language = self.parse_uint16('Language')
        pre_defined = self.parse_uint16()

    def __str__(self):
        return 'MediaHeaderBox: creation_time %i, modification_time %i, timescale %i, duration %i, language %i' % (self.creation_time, self.modification_time, self.timescale, self.duration, self.language)

class HandlerBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'HandlerBox')
        pre_defined = self.parse_uint32()
        self.handler_type = self.parse_fixedstring(4, 'Handler Type')
        reserved = [self.parse_uint32() for i in range(3)]
        self.name = self.parse_string(self.size, 'Name')

    def __str__(self):
        return 'HandlerBox: handler_type %s, name %s' % (self.handler_type, self.name)

class MediaInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaInformationBox')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'MediaInformationBox'

class SampleTableBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleTableBox')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'SampleTableBox'

class SampleDescriptionBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleDescriptionBox')
        entry_count = self.parse_uint32('Entry Count')
        self.boxes = []
        for i in range(entry_count):
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def __str__(self):
        return 'SampleDescriptionBox'

class SampleEntry(Box):
    def __init__(self, bytestream, start, name):
        super().__init__(bytestream, start, name)
        reserved = [self.parse_uint8() for i in range(6)]
        self.data_reference_index = self.parse_uint16('Data Reference Index')

    def __str__(self):
        return 'SampleEntry: data_reference_index %i' % self.data_reference_index

class AudioSampleEntry(SampleEntry):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'AudioSampleEntry')
        reserved = [self.parse_uint32() for i in range(2)]
        self.channel_count = self.parse_uint16('Channel Count')
        self.samplesize = self.parse_uint16('Sample Size')
        pre_defined = self.parse_uint16()
        reserved = self.parse_uint16()
        self.sample_rate = self.parse_uint32('Sample Rate')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'AudioSampleEntry: data_reference_index %i, channel_count %i, samplesize %i, sample_rate %i' % (self.data_reference_index, self.channel_count, self.samplesize, self.sample_rate)

class TimeToSampleBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TimeToSampleBox')
        entry_count = self.parse_uint32('Entry Count')
        self.entries = []
        self.start_syntax_item('Entries')
        for i in range(entry_count):
            self.start_syntax_item('Entry')
            tuple = (self.parse_uint32('Time'), self.parse_uint32('Sample'))
            self.entries.append(tuple)
            self.finish_syntax_item()
        self.finish_syntax_item()

    def __str__(self):
        return 'TimeToSampleBox: %i entries' % len(self.entries)

class DataInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataInformationBox')
        self.boxes = self.parseboxes()
        
    def __str__(self):
        return 'DataInformationBox'

class DataReferenceBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataReferenceBox')
        entry_count = self.parse_uint32('Entry Count')
        self.boxes = self.parseboxes()

    def __str__(self):
        return 'DataReferenceBox'

class DataEntryUrlBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataEntryUrlBox')
        self.url = self.parse_string(self.size, 'URL')
    
    def __str__(self):
        return 'DataEntryUrlBox: url %s' % self.url

class SampleSizeBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleSizeBox')
        self.sample_size = self.parse_uint32('Sample Size')
        self.sample_count = self.parse_uint32('Sample Count')
        self.sample_sizes = []
        if self.sample_size == 0:
            self.start_syntax_item('Sample Sizes')
            for i in range(self.sample_count):
                self.sample_sizes.append(self.parse_uint32('Size'))
            self.finish_syntax_item()

    def __str__(self):
        return 'SampleSizeBox: %i entries' % self.sample_count

    def get_size(self, idx):
        if self.sample_size != 0:
            return self.sample_size
        else:
            return self.sample_sizes[idx]
       
class SampleToChunkBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleToChunkBox')
        entry_count = self.parse_uint32('Entry Count')
        self.entries = []
        self.start_syntax_item('Entries')
        for i in range(entry_count):
            self.start_syntax_item('Entry')
            tuple = (self.parse_uint32('First Chunk'), self.parse_uint32('Samples Per Chunk'), self.parse_uint32())
            self.finish_syntax_item()
            self.entries.append(tuple)
        self.finish_syntax_item()

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
        super().__init__(bytestream, start, 'ChunkOffsetBox')
        entry_count = self.parse_uint32()
        self.entries = []
        self.start_syntax_item('Entries')
        for i in range(entry_count):
            value = self.parse_uint32('Entry')
            self.entries.append(value)
        self.finish_syntax_item()

    def __str__(self):
        return 'ChunkOffsetBox: %i entries' % len(self.entries)

    def get_offset(self, idx):
        return self.entries[idx - 1]

class FreeSpaceBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'FreeSpaceBox')
    
    def __str__(self):
        return 'FreeSpaceBox'


class MediaDataBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaDataBox')
    
    def __str__(self):
        return 'MediaDataBox'

class SoundMediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SoundMediaHeaderBox')
        self.balance = self.parse_uint16('Balance')
        reserved = self.parse_uint16()

    def __str__(self):
        return 'SoundMediaHeaderBox: balance %i' % self.balance

class ESDBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'ESDBox')
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