import os


class BaseFile:
    def __init__(self, endian='small'):
        self.endian = endian

    # Create a file and its containing directories, if they don't exist
    @staticmethod
    def create_file(filename):
        path = os.path.dirname(filename)
        try:
            os.makedirs(path)
        except OSError:
            if not os.path.isdir(path):
                raise
        f = open(filename, 'wb+')
        return f

    # Join filepath to base
    @staticmethod
    def fix_filename(base, filepath):
        # if filepath begins with /, ./ prevents base from being ignored
        return os.path.normpath(os.path.join(base, './' + filepath))

    # Check the length of the bytes from the content starting at the offset
    def assert_byte(self, offset, byte, length=1):
        for i in range(0, length):
            err = f'Expected byte 0x{ord(byte):X} at offset 0x{offset:X}, ' + \
                  f'but received 0x{self.content[offset + i]:X}.'
            assert bytes([self.content[offset + i]]) == byte, err
        return offset + length

    # Check the bytes from the content starting at the offset
    def assert_bytes(self, offset, bytes_str):
        for byte in bytes_str:
            offset = self.assert_byte(offset, bytes([byte]), 1)
        return offset

    # Get a null-terminated string from the content starting at the offset
    def extract_zero_str(self, offset):
        extracted = b''
        while bytes([self.content[offset]]) != b'\x00':
            extracted = extracted + bytes([self.content[offset]])
            offset += 1
        return extracted
