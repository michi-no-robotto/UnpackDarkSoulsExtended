from collections import OrderedDict
import struct
import zlib

from DSFileTool.file_formats.base import BaseFile


class DCX(BaseFile):
    def __init__(self, content=None):
        super().__init__(endian='big')
        self.content = content

    def get_content(self):
        return self.content

    # Check if the bytes at the start of the content match a .dcx file
    def is_dcx_file(self):
        return self.content[0:4] == b'DCX\x00'

    # Get the compressed .dcx content
    def compress(self):
        header = OrderedDict([
            ('signature', b'DCX\x00'),
            ('unknown1', 0x10000.to_bytes(4, 'big')),
            ('dcs_offset', 0x18.to_bytes(4, 'big')),
            ('dcp_offset', 0x24.to_bytes(4, 'big')),
            ('redundant_dcp_offset', 0x24.to_bytes(4, 'big')),
            ('dcs_header_size', 0x2c.to_bytes(4, 'big')),
            ('dcs_signature', b'DCS\x00'),
            ('uncompressed_size', 0x00.to_bytes(4, 'big')),
            ('compressed_size',  0x00.to_bytes(4, 'big')),
            ('dcp_signature', b'DCP\x00'),
            ('dcp_method', b'DFLT'),
            ('dca_offset', 0x20.to_bytes(4, 'big')),
            ('compression_level', 0x09000000.to_bytes(4, 'big')),
            ('unknown2', 0x00.to_bytes(12, 'big')),
            ('zlib_version', 0x00010100.to_bytes(4, 'big')),
            ('dca_signature', b'DCA\x00'),
            ('dca_header_size', 0x08.to_bytes(4, 'big')),
            ('dca_signature', b'DCA\x00'),
            ('unknown3', b'\x78\xDA'),
        ])

        c_obj = zlib.compressobj(level=6, wbits=-15)
        data = c_obj.compress(self.content) + c_obj.flush(zlib.Z_FULL_FLUSH)
        header['uncompressed_size'] = len(self.content).to_bytes(4, 'big')
        header['compressed_size'] = len(data).to_bytes(4, 'big')

        return b''.join(list(header.values()) + [data[:-2]])

    # Get the decompressed the .dcx content
    def decompress(self):
        offset = 0
        offset = self.assert_bytes(offset, b'DCX\x00')

        req_1, = struct.unpack_from('<I', self.content, offset)
        offset += struct.calcsize('<I')
        req_2, req_3, req_4 = struct.unpack_from('>III', self.content, offset)
        offset += struct.calcsize('>III')

        byte = 0x100
        err = f'Expected DCX header int 0x{byte:X}, but received {hex(req_1)}'
        assert req_1 == byte, err
        byte = 0x18
        assert req_2 == byte, err
        byte = 0x24
        assert req_3 == byte, err
        assert req_4 == byte, err

        header_length, = struct.unpack_from('>I', self.content, offset)
        offset += struct.calcsize('>I')

        offset = self.assert_bytes(offset, b'DCS\x00')

        uncomp_size, comp_size = struct.unpack_from(
            '>II', self.content, offset
        )
        offset += struct.calcsize('>II')

        offset = self.assert_bytes(offset, b'DCP\x00')
        offset = self.assert_bytes(offset, b'DFLT')

        # skip the portion of the header whose meaning is unknown / not needed
        offset += 0x18

        offset = self.assert_bytes(offset, b'DCA\x00')
        comp_header_length, = struct.unpack_from('>I', self.content, offset)
        offset += struct.calcsize('>I')

        offset = self.assert_bytes(offset, b'\x78\xDA')

        # the previous two bytes are included in the compressed data
        comp_size -= 2

        dec_obj = zlib.decompressobj(wbits=-15)
        return dec_obj.decompress(
            self.content[offset:offset + comp_size], uncomp_size
        )
