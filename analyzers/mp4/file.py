from .es import ESDescriptor

from syntax import format_fixed16, format_fixed8

import datetime

def mp4date(seconds):
    start = datetime.datetime(1904, 1, 1)
    date = start + datetime.timedelta(seconds=seconds)
    return date.strftime('%d/%m/%y %H:%M:%S')

class Box:
    def __init__(self, bytestream, start, box_name=None):
        self.bytestream = bytestream
        self.start = start

        self.bytestream.seek(start)

        self.size = self.bytestream.getuint32('size')
        self.type = self.bytestream.getfixedstring(4, 'type')
        if self.size == 1:
            self.size = self.bytestream.getuint64('largesize')
        elif self.size == 0:
            self.size = self.bytestream.size - start

        self.box_name = box_name or 'Box (\'%s\')' % self.type

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
    def __init__(self, bytestream, start, box_name):
        super().__init__(bytestream, start, box_name)
        self.version = self.bytestream.getuint8('version')
        self.flags = self.bytestream.getuint(3, 'flags')

class FileTypeBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'FileTypeBox')
        self.major_brand = self.bytestream.getfixedstring(4, 'major_brand')
        self.minor_version = self.bytestream.getuint32('minor_version')
        self.compatible_brands = []
        self.bytestream.start_syntax_item('compatible_brands')
        while self.bytestream.pos < self.start + self.size:
            self.compatible_brands.append(self.bytestream.getfixedstring(4, 'brand'))
        self.bytestream.finish_syntax_item()

class MovieBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MovieBox')
        self.boxes = self.parseboxes()

class MovieHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MovieHeaderBox')

        def format_duration(value):
            return '%.2f s' % (float(value) / self.timescale)

        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint64('modification_time', format=mp4date)
            self.timescale = self.bytestream.getuint32('timescale')
            self.duration = self.bytestream.getuint64('duration', format=format_duration)
        else:
            self.creation_time = self.bytestream.getuint32('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint32('modification_time', format=mp4date)
            self.timescale = self.bytestream.getuint32('timescale')
            self.duration = self.bytestream.getuint32('duration', format=format_duration)
        self.rate = self.bytestream.getuint32('rate', format=format_fixed16)
        self.volume = self.bytestream.getuint16('volume', format=format_fixed8)
        reserved = self.bytestream.getuint16()
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.bytestream.start_syntax_item('matrix')
        self.matrix = [self.bytestream.getuint32('%i' % i, format=format_fixed16) for i in range(9)]
        self.bytestream.finish_syntax_item()
        pre_defined = [self.bytestream.getuint32() for i in range(6)]
        self.next_track_ID = self.bytestream.getuint32('next_track_ID')

class TrackBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TrackBox')
        self.boxes = self.parseboxes()

class TrackHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TrackHeaderBox')

        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint64('modification_time', format=mp4date)
            self.track_ID = self.bytestream.getuint32('track_ID')
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint64('duration')
        else:
            self.creation_time = self.bytestream.getuint32('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint32('modification_time', format=mp4date)
            self.track_ID = self.bytestream.getuint32('track_ID')
            reserved = self.bytestream.getuint32()
            self.duration = self.bytestream.getuint32('duration')
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.layer = self.bytestream.getuint16('layer')
        self.alternate_group = self.bytestream.getuint16('alternate_group')
        self.volume = self.bytestream.getuint16('volume', format=format_fixed8)
        reserved = self.bytestream.getuint16()
        self.bytestream.start_syntax_item('matrix')
        self.matrix = [self.bytestream.getuint32('%i' % i, format=format_fixed16) for i in range(9)]
        self.bytestream.finish_syntax_item()
        self.width = self.bytestream.getuint32('width')
        self.height = self.bytestream.getuint32('height')

class MediaBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaBox')
        self.boxes = self.parseboxes()

class MediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaHeaderBox')

        def duration_format(value):
            return '%.2f s' % (float(value) / self.timescale)
            
        if self.version == 1:
            self.creation_time = self.bytestream.getuint64('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint64('modification_time', format=mp4date)
            self.timescale = self.bytestream.getuint32('timescale')
            self.duration = self.bytestream.getuint64('duration', format=duration_format)
        else:
            self.creation_time = self.bytestream.getuint32('creation_time', format=mp4date)
            self.modification_time = self.bytestream.getuint32('modification_time', format=mp4date)
            self.timescale = self.bytestream.getuint32('timescale')
            self.duration = self.bytestream.getuint32('duration', format=duration_format)
        self.language = self.bytestream.getuint16('language')
        pre_defined = self.bytestream.getuint16()

class HandlerBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'HandlerBox')
        pre_defined = self.bytestream.getuint32()
        self.handler_type = self.bytestream.getfixedstring(4, 'handler_type')
        reserved = [self.bytestream.getuint32() for i in range(3)]
        self.name = self.bytestream.getstring(self.size, 'name')

class MediaInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaInformationBox')
        self.boxes = self.parseboxes()

class SampleTableBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleTableBox')
        self.boxes = self.parseboxes()

class SampleDescriptionBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleDescriptionBox')
        entry_count = self.bytestream.getuint32('entry_count')
        self.boxes = []
        for i in range(entry_count):
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

class SampleEntry(Box):
    def __init__(self, bytestream, start, box_name):
        super().__init__(bytestream, start, box_name)
        reserved = [self.bytestream.getuint8() for i in range(6)]
        self.data_reference_index = self.bytestream.getuint16('data_reference_index')

class AudioSampleEntry(SampleEntry):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'AudioSampleEntry')
        reserved = [self.bytestream.getuint32() for i in range(2)]
        self.channel_count = self.bytestream.getuint16('channel_count')
        self.samplesize = self.bytestream.getuint16('samplesize')
        pre_defined = self.bytestream.getuint16()
        reserved = self.bytestream.getuint16()
        self.sample_rate = self.bytestream.getuint32('sample_rate', format=format_fixed16)
        self.boxes = self.parseboxes()

class TimeToSampleBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'TimeToSampleBox')
        entry_count = self.bytestream.getuint32('entry_count')
        self.entries = []
        self.bytestream.start_syntax_item('entries')
        for i in range(entry_count):
            self.bytestream.start_syntax_item()
            tuple = (self.bytestream.getuint32(), self.bytestream.getuint32())
            self.entries.append(tuple)
            self.bytestream.finish_syntax_item('sample_count: %i, sample_delta: %i' % (tuple[0], tuple[1]))
        self.bytestream.finish_syntax_item()

class DataInformationBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataInformationBox')
        self.boxes = self.parseboxes()

class DataReferenceBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataReferenceBox')
        entry_count = self.bytestream.getuint32('entry_count')
        self.boxes = self.parseboxes()

class DataEntryUrlBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'DataEntryUrlBox')
        self.url = self.bytestream.getstring(self.size, 'url')

class SampleSizeBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleSizeBox')
        self.sample_size = self.bytestream.getuint32('sample_size')
        self.sample_count = self.bytestream.getuint32('sample_count')
        self.sample_sizes = []
        if self.sample_size == 0:
            self.bytestream.start_syntax_item('sample_sizes')
            for i in range(self.sample_count):
                self.sample_sizes.append(self.bytestream.getuint32('%i' % i))
            self.bytestream.finish_syntax_item()

    def get_size(self, idx):
        if self.sample_size != 0:
            return self.sample_size
        else:
            return self.sample_sizes[idx]
       
class SampleToChunkBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SampleToChunkBox')
        entry_count = self.bytestream.getuint32('entry_count')
        self.entries = []
        self.bytestream.start_syntax_item('entries')
        for i in range(entry_count):
            self.bytestream.start_syntax_item()
            tuple = (self.bytestream.getuint32(), self.bytestream.getuint32(), self.bytestream.getuint32())
            self.bytestream.finish_syntax_item('first_chunk: %i, samples_per_chunk: %i, sample_description_index: %i' % (tuple[0], tuple[1], tuple[2]))
            self.entries.append(tuple)
        self.bytestream.finish_syntax_item()

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
        entry_count = self.bytestream.getuint32()
        self.entries = []
        self.bytestream.start_syntax_item('entries')
        for i in range(entry_count):
            value = self.bytestream.getuint32('%i' % i)
            self.entries.append(value)
        self.bytestream.finish_syntax_item()

    def get_offset(self, idx):
        return self.entries[idx - 1]

class FreeSpaceBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'FreeSpaceBox')

class MediaDataBox(Box):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'MediaDataBox')

class SoundMediaHeaderBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'SoundMediaHeaderBox')
        self.balance = self.bytestream.getuint16('balance')
        reserved = self.bytestream.getuint16()

class ESDBox(FullBox):
    def __init__(self, bytestream, start):
        super().__init__(bytestream, start, 'ESDBox')
        descriptor_start = self.bytestream.pos
        bytes = self.bytestream.read(self.start + self.size - self.bytestream.pos)
        self.descriptor = ESDescriptor(bytes, descriptor_start)
        self.bytestream.append_syntax_item(self.descriptor.syntax_item)

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
    bytestream.start_syntax_item(None, start)
    box = cls(bytestream, start)
    bytestream.seek(start + box.size)
    box.syntax_item = bytestream.finish_syntax_item(box.box_name)
    return box

class File:
    def __init__(self, bytestream):
        self.bytestream = bytestream

        self.boxes = []
        while self.bytestream.pos < self.bytestream.size:
            box = parsebox(self.bytestream)
            self.boxes.append(box)
            self.bytestream.seek(box.start + box.size)

    def syntax_items(self):
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
        return (bytes, location)