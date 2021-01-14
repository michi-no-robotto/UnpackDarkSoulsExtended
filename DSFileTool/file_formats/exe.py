import hashlib
import mmap
import os

from DSFileTool.logger import Logger


class EXE:
    ORIGINAL_CHECKSUMS = {
        'steam':     '67bcab513c8f0ed6164279d85f302e06b1d8a53abff5df7f3d10e1d4dfd81459',  # noqa: E501
        'debug':     'b6958f3f0db5fdb7ce6f56bff14353d8d81da8bae3456795a39dbe217c1897cf',  # noqa: E501
        'data1.0.0': '88d1eec18eba2542c9c7e5e6903e89f9c075b20be5cd045ce6e568e7b22bea9d',  # noqa: E501
        'data1.0.1': '91de0e016d7d79d3f2f32c3c121ce85019167f2bbd3257867d117db86ce88602',  # noqa: E501
        'data1.0.2': '44d2dccb1d522f8a320784381ecf83aeb62643d0fc38ae2f4ddf3ca066b52b6c',  # noqa: E501
    }

    PATCHED_CHECKSUMS = {
        'steam':     '903a946273bfe123fe5c85740c3613374e2cf538564bb661db371c6cb5a421ff',  # noqa: E501
        'debug':     '473de70f0dd03048ca5dea545508f6776206424494334a9da091fb27c8e5a23f',  # noqa: E501
        'data1.0.0': '6a2d10991e9e5c4d0f3cb3282d421bce7f45632f145d354272bc06ed9d4b47d0',  # noqa: E501
        'data1.0.1': 'a3c673ec084dc840c1b87bf6304b4379a2e0e95f00c01d4edc9202416a1c1ebb',  # noqa: E501
        'data1.0.2': '71495d5a0d603bd5058453592b1faca3a4cd326910629e2e75ca4c1b1f8d1305',  # noqa: E501
    }

    PATCH_LOOKUPS = {
        'ORIGINAL': b'\xFF\xF6\x46\x21\x20\xB3\x03\x74\x12\x6A\x04\x68',
        'PATCHED':  b'\xFF\xF6\x46\x21\x20\xB3\x03\xEB\x12\x6A\x04\x68',
    }

    PATCH_LOCATIONS = {
        'steam': 0x8FB816,
        'debug': 0x8FB726,
        'data1.0.0': 0x922196,
        'data1.0.1': 0x922296,
        'data1.0.2': 0x924516,
    }

    PATCH_REPLACEMENTS = {
        'dvdbnd0': (
            b'd\x00v\x00d\x00b\x00n\x00d\x000\x00:\x00',
            b'd\x00v\x00d\x00r\x00o\x00o\x00t\x00:\x00',
        ),
        'dvdbnd1': (
            b'd\x00v\x00d\x00b\x00n\x00d\x001\x00:\x00',
            b'd\x00v\x00d\x00r\x00o\x00o\x00t\x00:\x00',
        ),
        'dvdbnd2': (
            b'd\x00v\x00d\x00b\x00n\x00d\x002\x00:\x00',
            b'd\x00v\x00d\x00r\x00o\x00o\x00t\x00:\x00'
        ),
        'dvdbnd3': (
            b'd\x00v\x00d\x00b\x00n\x00d\x003\x00:\x00',
            b'd\x00v\x00d\x00r\x00o\x00o\x00t\x00:\x00'
        ),
        'hkxbnd': (
            b'h\x00k\x00x\x00b\x00n\x00d\x00:\x00',
            b'm\x00a\x00p\x00h\x00k\x00x\x00:\x00'
        ),
        'tpfbnd': (
            b't\x00p\x00f\x00b\x00n\x00d\x00:\x00',
            b'm\x00a\x00p\x00:\x00/\x00t\x00x\x00'
        ),
        '%stpf': (
            b'%\x00s\x00t\x00p\x00f\x00',
            b'c\x00h\x00r\x00\x00\x00\x00\x00'
        ),
    }

    def __init__(self, base_path='./', forced_exe_name=None):
        self.base_path = base_path
        self.file_name = forced_exe_name
        self.file_path = None

        self.log = Logger()

    # Get the path to the .exe file
    def get_path(self):
        return self.file_path

    # Compute the SHA256 checksum of the .exe read in of chunks
    def get_checksum(self, chunk_size=65536):
        hash_string = hashlib.sha256()
        with open(self.file_path, 'rb') as f:
            for block in iter(lambda: f.read(chunk_size), b''):
                hash_string.update(block)
        return hash_string.hexdigest()

    # Validate the .exe and returns its status and patch address
    def validate(self):
        if not self.file_name:
            if os.path.isfile(os.path.join(self.base_path, 'DATA.exe')):
                self.file_name = 'DATA.exe'
            else:
                self.file_name = 'DARKSOULS.exe'

        if not self.file_path:
            self.file_path = os.path.join(self.base_path, self.file_name)
            if not os.path.isfile(self.file_path):
                return None, None

        checksum = self.get_checksum()
        for game_version, patch_location in self.PATCH_LOCATIONS.items():
            if checksum == self.ORIGINAL_CHECKSUMS[game_version]:
                return 'ORIGINAL', patch_location
            elif checksum == self.PATCHED_CHECKSUMS[game_version]:
                return 'PATCHED', patch_location

        # if here, no valid exe was found
        with open(self.file_path, 'rb+') as exe_file:
            mm = mmap.mmap(exe_file.fileno(), 0)
            for idx, lookup in self.PATCH_LOOKUPS.items():
                mm.seek(0)
                pos = mm.find(lookup)
                if pos != -1:
                    if idx == 'ORIGINAL':
                        return 'UNEXPECTED', pos + 7
                    else:
                        return 'PATCHED', pos + 7

        # if still here, no .exe was found at all
        return None, None

    # Patch the .exe to work with the unpacked data
    def patch(self, patch_location):
        with open(self.file_path, 'rb+') as f:
            mm = mmap.mmap(f.fileno(), 0)

            for name, replacement in self.PATCH_REPLACEMENTS.items():
                count = 0
                find_str = replacement[0]
                replace_str = replacement[1]

                mm.seek(0)
                next_pos = mm.find(find_str)
                while next_pos != -1:
                    mm.seek(next_pos)
                    mm.write(replace_str)
                    count += 1
                    next_pos = mm.find(find_str)

                if count > 0:
                    self.log.que(
                        f' - Patched {count} times {name} in {self.file_name}.'
                    )

            # Disable .dcx loading.
            mm.seek(patch_location)
            if mm.read_byte() == 0x74:
                mm.seek(-1, os.SEEK_CUR)
                mm.write_byte(0xEB)

            mm.flush()
            mm.close()
