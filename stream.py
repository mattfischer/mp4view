import struct
import io

from syntax import SyntaxItem

class Bitstream:
    def __init__(self, bytes, byte_start):
        self.bytes = bytes
        self.pos = 0

        self.syntax_item_stack = []
        self.byte_start = byte_start

    def start_syntax_item(self, name=None):
        start = int(self.pos / 8)
        self.syntax_item_stack.append((name, start, []))

    def finish_syntax_item(self, name=None):
        (start_name, start, children) = self.syntax_item_stack.pop()
        end = int(self.pos / 8)
        size = max(end - start, 1)
        if name is None:
            name = start_name
        item = SyntaxItem(name, start + self.byte_start, size, children)
        self.append_syntax_item(item)
        return item

    def append_syntax_item(self, item):
        if len(self.syntax_item_stack) > 0:
            (_, _, children) = self.syntax_item_stack[-1]
            children.append(item)

    def getbits(self, bits, name=None, format=None):
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

        size = max(end - start, 1)
        if name:
            if format:
                title = '%s: %s' % (name, format(val))
            else:
                title = '%s: %i' % (name, val)
            self.append_syntax_item(SyntaxItem(title, start + self.byte_start, size))
        
        return val

    def getstring(self, length, name=None):
        start = int(self.pos / 8)
        string = self.bytes[start:start+length].decode('utf-8')
        self.pos += length * 8

        if name:
            self.append_syntax_item(SyntaxItem('%s: \'%s\'' % (name, string), start + self.byte_start, length))
            
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

    def start_syntax_item(self, name=None, start=-1):
        if start == -1:
            start = self.pos
        self.syntax_item_stack.append((name, start, []))

    def finish_syntax_item(self, name=None):
        (start_name, start, children) = self.syntax_item_stack.pop()
        size = self.pos - start
        if name is None:
            name = start_name
        item = SyntaxItem(name, start, size, children)
        self.append_syntax_item(item)
        return item

    def append_syntax_item(self, item):
        if len(self.syntax_item_stack) > 0:
            (_, _, children) = self.syntax_item_stack[-1]
            children.append(item)

    def getuint(self, size, name, format=None):
        start = self.pos
        bytes = self.file.read(size)
        self.pos += size

        value = 0
        for byte in bytes:
            value = value << 8 | byte
        
        if name:
            if format:
                title = '%s: %s' % (name, format(value))
            else:
                title = '%s: %i' % (name, value)
            self.append_syntax_item(SyntaxItem(title, start, size))
        return value

    def getuint8(self, name=None, format=None):
        return self.getuint(1, name, format)

    def getuint16(self, name=None, format=None):
        return self.getuint(2, name, format)

    def getuint32(self, name=None, format=None):
        return self.getuint(4, name, format)

    def getuint64(self, name=None, format=None):
        return self.getuint(8, name, format)

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