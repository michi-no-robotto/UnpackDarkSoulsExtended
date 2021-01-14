import os
import sys
import struct

from DSFileTool.tools import build_name_hash_dict
from DSFileTool.file_formats.base import BaseFile
from DSFileTool.file_formats.dcx import DCX
from DSFileTool.logger import Logger


class BDT(BaseFile):
    def __init__(self, header_file, data_file, out_path=None):
        super().__init__()
        self.data_file = data_file
        self.out_path = out_path or os.path.split(data_file)[0]
        self.header_file = header_file
        with open(header_file, 'rb') as f:
            self.content = f.read()
        self.log = Logger()

    # Check if the given file is a .bhd header
    def is_header_bhd(self):
        return self.content[:12] == b'BHF307D7R6\x00\x00'

    # Check if the given file is a .bhd5 header
    def is_header_bhd5(self):
        return self.content[:4] == b'BHD5'

    # Parse the header to a dictionary containing tuples of offset and length
    def parse_bhd_header_to_dict(self):
        return_dict = {}

        offset = 0
        offset = self.assert_bytes(offset, b'BHF307D7R6\x00\x00')

        # skip the version number
        offset = 0x0c

        (flag, records_cnt) = struct.unpack_from('<II', self.content, offset)
        offset += struct.calcsize('<II')
        err = f'File has unknown BHD3 magic flag: {hex(flag)}'
        assert flag == 0x74 or flag == 0x54, err

        # skip to the records
        offset = 0x20

        for _ in range(records_cnt):
            (
                record_sep, filedata_size, filedata_offset, file_id,
                filename_offset, dummy_filedata_size
            ) = struct.unpack_from('<IIIIII', self.content, offset)
            offset += struct.calcsize('<IIIIII')

            err = 'File has malformed record structure.' + \
                  f'File data size: {filedata_size} does not match ' + \
                  f'dummy file data size: {dummy_filedata_size}.'
            assert filedata_size == dummy_filedata_size, err

            err = 'File has malformed record structure. Record' + \
                  f' has unknown record separator: {hex(record_sep)}.'
            assert record_sep == 0x40, err

            filename = str(self.extract_zero_str(filename_offset), 'shift_jis')
            filename = filename.replace('\\', '/')
            return_dict[filename] = (filedata_offset, filedata_size)
        return return_dict

    # Parse the header to a dictionary containing tuples of offset and length
    def parse_bhd5_header_to_dict(self):
        name_hash_dict = build_name_hash_dict()
        return_dict = {}

        offset = 0
        offset = self.assert_bytes(offset, b'BHD5\xFF')
        offset = self.assert_byte(offset, b'\x00', 3)
        offset = self.assert_byte(offset, b'\x01', 1)
        offset = self.assert_byte(offset, b'\x00', 3)

        (file_size,) = struct.unpack_from('<I', self.content, offset)
        offset += struct.calcsize('<I')
        (bin_cnt, bin_offset) = struct.unpack_from('<II', self.content, offset)
        offset += struct.calcsize('<II')

        for _ in range(bin_cnt):
            (record_bin_cnt, record_bin_offst) = struct.unpack_from(
                                            '<II', self.content, offset)
            offset += struct.calcsize('<II')

            for _ in range(record_bin_cnt):
                (
                    record_hash, record_size, record_offset, zero
                ) = struct.unpack_from('<IIII', self.content, record_bin_offst)
                record_bin_offst += struct.calcsize('<IIII')

                err = 'Required record terminator is non-zero.' + \
                      f'Actual value is {zero}.'
                assert zero == 0, err

                try:
                    name = name_hash_dict[record_hash]
                except KeyError:
                    raise AssertionError(
                        f'Name hash {hex(record_hash)} ' +
                        'was not found in the name hash dictionary.'
                    )
                return_dict[name] = (record_offset, record_size)
        return return_dict

    # Pack a filelist into a header/data file pair
    def pack(self, file_list):
        raise NotImplementedError

    # Unpack the data file using the header contents
    def unpack(self):
        created_file_list = []

        if self.is_header_bhd():
            file_dict = self.parse_bhd_header_to_dict()
        elif self.is_header_bhd5():
            file_dict = self.parse_bhd5_header_to_dict()
        else:
            raise AssertionError('Header file does not match known formats.')

        file_cnt = len(file_dict.keys())
        with open(self.data_file, 'rb') as d:
            HEADER_STRING = b'BDF307D7R6\x00\x00\x00\x00\x00\x00'
            HEADER_OFFSET = len(HEADER_STRING)

            d.seek(0)

            err = 'Header of data file is missing. ' + \
                  'Data file is possibly corrupt or malformed.'
            assert d.read(HEADER_OFFSET) == HEADER_STRING, err

            count = 0
            for name in file_dict:
                (record_offset, record_size) = file_dict[name]
                file_path = self.fix_filename(self.out_path, name)
                d.seek(record_offset)
                content = d.read(record_size)

                if (dcx := DCX(content)).is_dcx_file():
                    if file_path[-4:] == '.dcx':
                        file_path = file_path[:-4]
                    content = dcx.decompress()
                elif os.path.isfile(file_path):
                    # skip duplicates (fade.drb, menu.drb, nowloading.drb)
                    file_path = file_path + '.xxx'

                count += 1
                created_file_list.append(file_path)
                f = self.create_file(file_path)
                f.write(content)
                f.close()

                print(
                    '\r * Unpacking files from archive ' +
                    f'({count}/{file_cnt})...',
                    end=''
                )
                sys.stdout.flush()
        print('\r' + ' ' * 50 + '\r', end='')

        return created_file_list
