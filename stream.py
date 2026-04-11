import struct
import io

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

    def seek(self, pos):
        self.file.seek(pos)
        self.pos = pos

    def read(self, length):
        bytes = self.file.read(length)
        self.pos += length
        return bytes

    def getuint8(self):
        bytes = self.file.read(1)
        self.pos += 1
        return struct.unpack('!B', bytes)[0]

    def getuint16(self):
        bytes = self.file.read(2)
        self.pos += 2
        return struct.unpack('!H', bytes)[0]

    def getuint32(self):
        bytes = self.file.read(4)
        self.pos += 4
        return struct.unpack('!I', bytes)[0]

    def getuint64(self):
        bytes = self.file.read(8)
        self.pos += 8
        return struct.unpack('!Q', bytes)[0]

    def getfixedstring(self, length):
        bytes = self.file.read(length)
        self.pos += length
        return bytes.decode()

    def getstring(self, maxsize):
        string = ''
        bytes = self.file.read(maxsize)
        end = bytes.find(0)
        self.pos += end
        self.file.seek(self.pos)
        return bytes[0:end].decode('utf-8')
