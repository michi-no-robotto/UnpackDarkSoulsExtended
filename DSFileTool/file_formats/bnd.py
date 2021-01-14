import struct

from DSFileTool.file_formats.base import BaseFile


class BND(BaseFile):
    def __init__(self, content, base_path, n_base_path):
        super().__init__()
        self.content = content
        self.base_path = base_path
        self.n_base_path = n_base_path

    # Fixes the given filename and joins it with the appropriate basepath
    @staticmethod
    def relativize_filename(filename, basepath, n_basepath):
        if len(filename) >= 2 and filename[0:2].upper() == 'N:':
            return BND.fix_filename(n_basepath, filename[2:])
        else:
            return BND.fix_filename(basepath, filename)

    # Check if the given file is a .bnd header
    def is_header_bnd(self):
        return self.content[0:4] == b'BND3'

    # Unpack the .bnd file content from a BND3-packed file
    def unpack(self):
        created_file_list = []

        offset = 0
        offset = self.assert_bytes(offset, b'BND3')

        # skip the version number
        offset = 0x0c

        (flag, record_cnt, _) = struct.unpack_from(
                                            '<III', self.content, offset)
        offset += struct.calcsize('<III')

        err = f'File has unknown BND3 magic flag: {hex(flag)}.'
        assert flag == 0x74 or flag == 0x54 or flag == 0x70, err

        # skip to the records
        offset = 0x20

        count = 0
        for _ in range(record_cnt):
            if flag == 0x74 or flag == 0x54:
                (
                    record_sep, data_size, data_offset,
                    file_id, filename_offset, dummy_data_size
                ) = struct.unpack_from('<IIIIII', self.content, offset)
                offset += struct.calcsize('<IIIIII')

                err = 'File has malformed record structure. File size: ' + \
                      f'{data_size} does not match dummy file ' + \
                      f'data size: {dummy_data_size}.'
                assert data_size == dummy_data_size, err
            else:  # flag == 0x70
                (
                    record_sep, data_size, data_offset,
                    file_id, filename_offset
                ) = struct.unpack_from('<IIIII', self.content, offset)
                offset += struct.calcsize('<IIIII')

            err = 'File has malformed record structure. Record ' + \
                  f'has unknown record separator: {hex(record_sep)}.'
            assert record_sep == 0x40, err

            filename = str(self.extract_zero_str(filename_offset), 'shift_jis')
            filename = filename.replace('\\', '/')
            filename = self.relativize_filename(
                filename, self.base_path, self.n_base_path
            )
            filedata = self.content[data_offset:data_offset + data_size]

            created_file_list.append(filename)
            f = self.create_file(filename)
            f.write(filedata)
            f.flush()
            f.close()
            count += 1
        return created_file_list
