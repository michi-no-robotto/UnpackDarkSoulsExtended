import os
import shutil
import sys

from DSFileTool.defaults import c4110
from DSFileTool.logger import Logger
from DSFileTool.tools import prompt, wait_before_exit
from DSFileTool.file_formats.bdt import BDT
from DSFileTool.file_formats.bnd import BND
from DSFileTool.file_formats.exe import EXE

log = Logger()


class Unpacker:
    UNPACKED_DIRS = [
        'chr', 'event', 'facegen', 'font', 'map', 'menu', 'msg', 'mtd',
        'obj', 'other', 'param', 'paramdef', 'parts', 'remo', 'script',
        'sfx', 'shader', 'sound'
    ]
    BACKUP_DIR = '_Backup'
    TEMP_DIR = '_TMP'
    TEMP_DATA_SUBDIR = 'DATA'
    TEMP_N_SUBDIR = 'N'

    # Recursively removes a directory
    @staticmethod
    def remove_directory(d):
        try:
            shutil.rmtree(d)
        except OSError:
            if not os.path.isdir(d):
                raise

    # Check if any existing directories match the ones from the archives
    @staticmethod
    def check_for_unpacked_dir():
        already_unpacked_dirs = []
        for d in Unpacker.UNPACKED_DIRS:
            if os.path.isdir(d):
                already_unpacked_dirs.append(d)
        return already_unpacked_dirs

    # Make a backup of the files in file_list into BACKUP_DIR
    @staticmethod
    def make_backups(file_list):
        if os.path.exists(Unpacker.BACKUP_DIR):
            Unpacker.remove_directory(Unpacker.BACKUP_DIR)

        try:
            os.makedirs(Unpacker.BACKUP_DIR)
        except OSError:
            if not os.path.isdir(Unpacker.BACKUP_DIR):
                raise

        for f in file_list:
            shutil.copy2(f, Unpacker.BACKUP_DIR)
            log.que(
                f' - Backed up file {os.path.basename(f)}.'
            )

    # Remove all unpacked directories
    @staticmethod
    def remove_unpacked_dirs(dirs):
        log.que(
            'lightcyan',
            'Deleting existing unpacked archive directories...'
        )
        for d in dirs:
            Unpacker.remove_directory(d)
        log.good('Done.')

    # Create all directories in UNPACKED_DIRS
    @staticmethod
    def create_unpacked_dirs():
        for d in Unpacker.UNPACKED_DIRS:
            try:
                os.makedirs(d)
            except OSError:
                if not os.path.isdir(d):
                    raise

    # Return a dictionary of all BDT/BHT pairs
    @staticmethod
    def build_bdt_bhd_pairing(file_list):
        bdt_list = [
            f for f in file_list if os.path.splitext(f)[1][-3:] == 'bdt'
        ]
        bhd_list = [
            f for f in file_list if os.path.splitext(f)[1][-3:] == 'bhd'
        ]

        return_dict = {bdt_file: [] for bdt_file in bdt_list}
        for bdt_file in bdt_list:
            (_, bdt_filename) = os.path.split(os.path.abspath(bdt_file))
            trimmed_bdt_filename = bdt_filename[:-3]
            for bhd_file in bhd_list:
                (_, bhd_filename) = os.path.split(os.path.abspath(bhd_file))
                trimmed_bhd_filename = bhd_filename[:-3]
                if trimmed_bdt_filename == trimmed_bhd_filename:
                    return_dict[bdt_file].append(bhd_file)

        return return_dict

    # Get the list of valid archive files
    @staticmethod
    def get_archives(base_path='./'):
        archive_list = dict()
        for file_obj in os.scandir(base_path):
            file_name = os.path.splitext(file_obj.name)[0]
            file_ext = os.path.splitext(file_obj.name)[1]
            if file_obj.is_file and file_ext in ['.bdt', '.bhd5']:
                archive_list.setdefault(file_name, [None, None])
                if file_ext == '.bdt':
                    archive_list[file_name][1] = file_obj.path
                elif file_ext == '.bhd5':
                    archive_list[file_name][0] = file_obj.path
        return archive_list

    # Unpack all .bdt archives in the archive list
    @staticmethod
    def unpack_archives(archive_list):
        BND_MANIFEST_FILE = 'bnd_manifest.txt'
        BND_MANIFEST_HEADER = '''
This manifest records the source *bnd file locations and their corresponding
list of included files. Use this manifest and the unpacked files in this
directory to examine the contents of all the .bnd files directly and then
unpack/modify/repack the associated .bnd file for any given unpacked file.

Note that the files in this directory are not read by the game and modifying
them has no effect, but can be useful for finding what file should be modified.


MANIFEST:'''

        created_files = []
        for archive in sorted(archive_list.values()):
            header_file = archive[0]
            data_file = archive[1]
            header_name = os.path.split(header_file)[1]
            data_name = os.path.split(data_file)[1]

            if not os.path.isfile(header_file):
                log.bad(
                    ' - Header file',
                    'white', header_name,
                    'lightred', 'is missing. Skipping.'
                )
                continue
            if not os.path.isfile(data_file):
                log.bad(
                    ' - Archive file',
                    'white', data_name,
                    'lightred', 'is missing. Skipping.'
                )
                continue

            log.que(
                f' - Unpacking archive {data_name} ' +
                f'using header {header_name}...'
            )
            new_files = BDT(header_file, data_file, os.getcwd()).unpack()
            created_files += new_files
        # remove duplicates
        created_files = list(set(created_files))

        log.que(' - Unpacking BND archives...')
        bnd_list = [
            f for f in created_files if os.path.splitext(f)[1][-3:] == 'bnd'
        ]
        msg_len = 0
        manifest_string_list = []
        for count, filepath in enumerate(sorted(bnd_list)):
            (directory, filename) = os.path.split(os.path.abspath(filepath))
            rel_directory = os.path.relpath(directory)

            msg = f'\r * ({count + 1}/{len(bnd_list)}) ' + \
                  f'Unpacking BND file {filename}...'
            print(msg, end='')

            with open(filepath, 'rb') as f:
                file_content = f.read()
                bnd_base_path = os.path.join(
                    os.getcwd(),
                    Unpacker.TEMP_DIR, Unpacker.TEMP_DATA_SUBDIR, rel_directory
                )
                bnd_n_base_path = os.path.join(
                    os.getcwd(),
                    Unpacker.TEMP_DIR, Unpacker.TEMP_N_SUBDIR
                )
                new_file_list = BND(
                    file_content, bnd_base_path, bnd_n_base_path
                ).unpack()
                created_files += new_file_list

                if len(new_file_list) > 0:
                    manifest_string_list.append(
                        os.path.join(rel_directory, filename)
                    )

                    for new_file in new_file_list:
                        new_file_rel = os.path.relpath(
                            new_file,
                            os.path.join(os.getcwd(), Unpacker.TEMP_DIR)
                        )
                        manifest_string_list.append(' ' + new_file_rel)

            print('\r' + ' ' * msg_len, end='')
            msg_len = len(msg)
            sys.stdout.flush()
        print('\r', end='')

        log.que(' - Writing custom copy of missing file(s)...')
        manifest_string_list.append('-- Custom --')
        filepath = c4110['PATH'].replace('\\', '/')
        bnd_n_base_path = os.path.join(
            os.getcwd(), Unpacker.TEMP_DIR, Unpacker.TEMP_N_SUBDIR
        )
        filepath_to_use = BND.relativize_filename(
            filepath, os.getcwd(), bnd_n_base_path
        )
        f = BND.create_file(filepath_to_use)
        f.write(c4110['DATA'])
        f.close()
        created_files.append(filepath_to_use)
        new_file_rel = os.path.relpath(
            filepath_to_use, os.path.join(os.getcwd(), Unpacker.TEMP_DIR)
        )
        manifest_string_list.append(r' {new_file_rel}')

        # populate the manifest
        manifest_file = os.path.join(
            os.getcwd(), Unpacker.TEMP_DIR, BND_MANIFEST_FILE
        )
        with open(manifest_file, 'w', encoding='shift_jis') as g:
            g.write(BND_MANIFEST_HEADER)
            g.write('\n'.join(manifest_string_list))

        log.que(' - Examining unpacked files for BDT/BHD pairs...')
        pairing_dict = Unpacker.build_bdt_bhd_pairing(list(set(created_files)))
        for bdt_file in pairing_dict:
            err = f'BDT File {bdt_file} has no corresponding header file.'
            assert len(pairing_dict[bdt_file]) != 0, err

        log.que(' - Unpacking BDT/BHD pairs...')
        pair_cnt = len(pairing_dict.keys())
        for count, bdt_file in enumerate(sorted(pairing_dict.keys())):
            print(f'\r * ({count + 1}/{pair_cnt}) Unpacking BDT/BHD pairs...')
            (_, bdt_filename) = os.path.split(os.path.abspath(bdt_file))
            match_bhd_file = pairing_dict[bdt_file][0]
            (_, bhd_filename) = os.path.split(os.path.abspath(match_bhd_file))

            print(
                f'  - Unpacking archive {bdt_filename} ' +
                f'using header {bhd_filename}...'
            )

            # redirect the output of the file depending on its extension
            (_, bdt_file_ext) = os.path.splitext(bdt_filename)
            if bdt_file_ext == '.chrtpfbdt':
                rel_directory = 'chr'
            elif bdt_file_ext == '.hkxbdt':
                rel_directory = 'map'
            elif bdt_file_ext == '.tpfbdt':
                rel_directory = os.path.join('map', 'tx')
            else:
                raise AssertionError(
                    f'Unrecognized *bdt file extension: {bdt_file_ext}.'
                )

            directory = os.path.abspath(
                os.path.join(os.getcwd(), rel_directory)
            )
            BDT(match_bhd_file, bdt_file, directory).unpack()

            # erase the previous two lines
            ANSI_CLEAR_LINE = '\x1b[K'
            ANSI_CURSOR_UP_LINE = '\x1b[1A'
            print('\r' + (ANSI_CURSOR_UP_LINE + ANSI_CLEAR_LINE) * 2, end='')

        log.que(' - Removing BDT/BHD pairs...')
        for bdt_file in pairing_dict.keys():
            match_bhd_file = pairing_dict[bdt_file][0]
            try:
                os.remove(bdt_file)
            except OSError:
                if not os.path.isfile(bdt_file):
                    raise
            try:
                os.remove(match_bhd_file)
            except OSError:
                if not os.path.isfile(match_bhd_file):
                    raise

    # Removes any Dark Souls archive files from the current directory
    @staticmethod
    def remove_archives(archive_list):
        log.que('lightcyan', 'Removing archives...')
        for archive in sorted(archive_list.values()):
            header_file = archive[0]
            data_file = archive[1]

            try:
                os.remove(header_file)
            except OSError:
                if os.path.isfile(header_file):
                    raise
            try:
                os.remove(data_file)
            except OSError:
                if os.path.isfile(data_file):
                    raise

        log.good('Done.')

    # Remove the temporary directory where *bnd files are unpacked
    @staticmethod
    def remove_temp_dir():
        log.que('lightcyan', 'Removing the temporary directory...')
        Unpacker.remove_directory(Unpacker.TEMP_DIR)
        log.good('Done.')

    # Locate and attempt to unpack any Dark Souls archive files in the path
    @staticmethod
    def attempt_unpack(path='./'):
        os.chdir(path)
        log.start_log()

        log.que('lightcyan', 'Preparing to unpack Dark Souls for modding...')
        log.que(' - Examining current directory...')

        already_unpacked = Unpacker.check_for_unpacked_dir()

        log.que(' - Examining Dark Souls executable...')

        exe_obj = EXE()
        (exe_status, patch_location) = exe_obj.validate()
        if exe_status not in ('ORIGINAL', 'PATCHED'):
            if exe_status == 'UNEXPECTED':
                log.warn(
                    'lightred',
                    'Executable does not match expected checksums,',
                    'white',
                    'but can still be patched using experimental methods.',
                    no_timestamp=True
                )
                if not prompt('Continue?'):
                    wait_before_exit(1)
            else:
                log.bad('No valid executable found.')
                log.bad('Check your current directory and try again.')
                wait_before_exit(1)

        log.que(' - Examining data archives...')
        only_patch_exe = False
        archive_list = Unpacker.get_archives()
        if (
            len(archive_list.keys()) == 0 and exe_status == 'PATCHED' and
            len(already_unpacked) == len(Unpacker.UNPACKED_DIRS) and
            os.path.isdir(Unpacker.BACKUP_DIR)
        ):
            log.info(
                'white',
                'Unpacking appears to be have been previously completed.',
                'Exiting.'
            )
            wait_before_exit(0)

        elif len(archive_list.keys()) == 0 and exe_status != 'PATCHED':
            log.info('white', 'No archives present, but unpatched .exe found.')
            log.warn(
                'lightred',
                'Patching the .exe alone will not unpack Dark Souls fully.',
                no_timestamp=True
            )
            if prompt('Patch .exe? Unpacking will abort after this step.'):
                only_patch_exe = True
            else:
                wait_before_exit(1)

        if not only_patch_exe:
            log.que(' - Examining directory contents...')
            if len(already_unpacked) > 0:
                log.info(
                    'white',
                    'The following destination directories already exist and',
                    'lightred', 'will be deleted',
                    'white', 'before unpacking begins:'
                )
                msg = ''
                for i, dir_name in enumerate(already_unpacked):
                    if i == 0:
                        msg += ' - '
                    if i != len(already_unpacked) - 1:
                        msg += f'{dir_name}, '
                    else:
                        msg += f'{dir_name}'
                log.info('grey', msg)

                log.warn(
                    'white', 'The current contents of these directories',
                    'lightred', 'will be lost.',
                    no_timestamp=True
                )
                if not prompt('Continue anyway?'):
                    wait_before_exit(1)

        should_make_backups = True
        if os.path.isdir(Unpacker.BACKUP_DIR):
            log.warn(
                'lightred', 'Backup directory',
                'white', Unpacker.BACKUP_DIR,
                'lightred', 'already exists.',
                'grey', 'Backed-up copies of current files',
                'red', 'WILL NOT',
                'grey', 'be created.',
                no_timestamp=True
            )
            if prompt('Continue anyway?'):
                should_make_backups = False
            else:
                wait_before_exit(1)

        if not only_patch_exe:
            if os.path.isdir(Unpacker.TEMP_DIR):
                log.warn(
                    'lightred', 'Temporary unpacking directory',
                    'white', Unpacker.TEMP_DIR,
                    'lightred', 'already exists.\n',
                    'grey', 'The current contents of this directory',
                    'red', 'WILL',
                    'grey', 'be lost.',
                    no_timestamp=True
                )
                if not prompt('Continue anyway?'):
                    wait_before_exit(1)

            should_remove_temp_dir = True
            log.warn(
                'white', 'Remove unpacked .bnd directory when done?',
                'This directory is useful for making mods only.',
                no_timestamp=True
            )
            if not prompt('Answer Yes if unsure.'):
                should_remove_temp_dir = False

        log.good('Done.')

        if should_make_backups:
            log.que('lightcyan', 'Making backups...')
            files_to_backup = [exe_obj.get_path()]
            if not only_patch_exe:
                files_to_backup += [
                    f for a in archive_list.values() for f in a
                ]
            Unpacker.make_backups(files_to_backup)
            log.good('Done.')
        else:
            log.que('lightcyan', 'Skipping backing-up important files.')

        if exe_status == 'PATCHED':
            log.que(
                'lightcyan',
                'Skipping patching (the .exe is already patched).'
            )
        else:
            log.que('lightcyan', 'Patching .exe file...')
            exe_obj.patch(patch_location)
            log.good('Done.')
            if exe_status == 'ORIGINAL':
                log.que('lightcyan', 'Verifying modifications...')
                (mod_exe_status, _) = exe_obj.validate()
                if mod_exe_status == 'PATCHED':
                    log.good('Done.')
                else:
                    log.bad(
                        'Patched .exe does not match expected checksum.'
                    )
                    if not prompt('Continue anyway?'):
                        wait_before_exit(1)
            else:
                log.info(
                    'Skipping checksum verification of a non-standard .exe.'
                )

        if only_patch_exe:
            log.info('Aborting unpacking after .exe modification.')
            wait_before_exit(0)

        if len(already_unpacked) > 0:
            Unpacker.remove_unpacked_dirs(already_unpacked)

        log.que('lightcyan', 'Unpacking archives...')
        Unpacker.create_unpacked_dirs()
        Unpacker.unpack_archives(archive_list)
        log.good('Done')

        Unpacker.remove_archives(archive_list)
        if should_remove_temp_dir:
            Unpacker.remove_temp_dir()

        log.good('Unpacking completed.')
        wait_before_exit(0)
