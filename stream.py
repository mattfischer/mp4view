import struct
import io

from syntax import SyntaxItem

class Bitstream:
    def __init__(self, bytes):
        self.bytes = bytes
        self.pos = 0

    def getbits(self, bits):
        start = int(self.pos / 8)
        end = int((self.pos + bits - 1) / 8)
        mod = (self.pos + bits - 1) % 8
        bytes = self.bytes[start:end+1]

        val = 0
        for byte in bytes:
            val = val << 8 | byte

        shift = 7 - mod
        val >>= shift

        mask = (1 << bits) - 1
        val &= mask

        self.pos += bits
        return val

    def getstring(self, length):
        start = int(self.pos / 8)
        string = self.bytes[start:start+length].decode('utf-8')
        self.pos += length * 8
        return string

class Bytestream:
    def __init__(self, file):
        self.file = file

        self.file.seek(0, io.SEEK_END)
        self.size = self.file.tell()
        self.file.seek(0)

        self.pos = 0

        self.syntax_item_stack = []

    def seek(self, pos):
        self.file.seek(pos)
        self.pos = pos

    def read(self, length):
        bytes = self.file.read(length)
        self.pos += length
        return bytes

    def start_syntax_item(self, name):
        self.syntax_item_stack.append((name, self.pos, []))

    def finish_syntax_item(self, extra_children=[]):
        (name, start, children) = self.syntax_item_stack.pop()
        size = self.pos - start
        item = SyntaxItem(name, start, size, children + extra_children)
        self.append_syntax_item(item)
        return item

    def append_syntax_item(self, item):
        if len(self.syntax_item_stack) > 0:
            (_, _, children) = self.syntax_item_stack[-1]
            children.append(item)

    def getint(self, size, format, name, just_size=-1):
        start = self.pos
        bytes = self.file.read(size)
        self.pos += size
        if just_size == -1:
            just_size = size
        value = struct.unpack(format, bytes.rjust(just_size))[0]
        if name:
            self.append_syntax_item(SyntaxItem('%s: %i' % (name, value), start, size))
        return value

    def getuint8(self, name=None):
        return self.getint(1, '!B', name)

    def getuint16(self, name=None):
        return self.getint(2, '!H', name)

    def getuint32(self, name=None):
        return self.getint(4, '!I', name)

    def getuint64(self, name=None):
        return self.getint(8, '!Q', name)

    def getfixedstring(self, length, name=None):
        start = self.pos
        size = length
        bytes = self.file.read(size)
        self.pos += size
        value = bytes.decode()
        if name:
            display = value
            if display[0] == '\0':
                display = '<null>'
            self.append_syntax_item(SyntaxItem('%s: \'%s\'' % (name, display), start, size))

        return value

    def getstring(self, maxsize, name=None):
        start = self.pos
        string = ''
        bytes = self.file.read(maxsize)
        end = bytes.find(0)
        size = end - start
        self.pos += end
        self.file.seek(self.pos)
        value = bytes[0:end].decode('utf-8')

        if name:
            self.append_syntax_item(SyntaxItem('%s: \'%s\'' % (name, value), start, size))

        return value