from DSFileTool.logger import Logger
from DSFileTool.unpacker import Unpacker

if __name__ == '__main__':
    try:
        Unpacker.attempt_unpack()
    except KeyboardInterrupt:
        log = Logger()
        print('')
        log.info('User aborted the script.')
