import logging
import os
import re
import sys

import huepy

from DSFileTool.tools import Dotdict, Singleton


class FileLogFormatter(logging.Formatter):
    def format(self, rec):
        msg = rec.msg
        msg = re.sub('\033' + r'\[[\d;]\d?m', '', msg)  # remove color/bold
        msg = re.sub(r'^\[\S\]\s', '', msg)  # remove command
        rec.msg = msg
        return super().format(rec)


class Logger(metaclass=Singleton):
    COLOR = Dotdict({
        'white': huepy.white,
        'grey': huepy.grey,
        'black': huepy.black,
        'green': huepy.green,
        'lightgreen': huepy.lightgreen,
        'cyan': huepy.cyan,
        'lightcyan': huepy.lightcyan,
        'red': huepy.red,
        'lightred': huepy.lightred,
        'blue': huepy.blue,
        'lightblue': huepy.lightblue,
        'purple': huepy.purple,
        'lightpurple': huepy.lightpurple,
        'orange': huepy.orange,
        'yellow': huepy.yellow,
    })

    STYLE = Dotdict({
        'bg': huepy.bg,
        'bold': huepy.bold,
        'italic': huepy.italic,
        'under': huepy.under,
        'strike': huepy.strike,
    })

    COMMAND = Dotdict({
        'info': (huepy.info, 'yellow'),
        'que': (huepy.que, 'lightblue'),
        'bad': (huepy.bad, 'lightred'),
        'good': (huepy.good, 'green'),
        'run': (huepy.run, 'white'),
        'plain': (lambda msg: msg, 'white'),
    })

    def __init__(self):
        self.logger = logging.getLogger('UnpackDarkSoulsExtended')

        self.formatter = logging.Formatter(
            fmt='%(asctime)s %(message)s', datefmt='[%d/%m %H:%M]'
        )

        self.stream = logging.StreamHandler()
        self.stream.setLevel(logging.DEBUG)
        self.stream.setFormatter(self.formatter)

        self.logger.addHandler(self.stream)
        self.logger.setLevel(logging.DEBUG)

    def start_log(self):
        logF = os.path.join('./', 'UnpackDarkSoulsExtended.log')
        if os.path.exists(logF):
            open(logF, 'w').close()

        self.logF = logging.FileHandler(filename=logF)
        self.logF.setLevel(logging.DEBUG)
        self.logF.setFormatter(FileLogFormatter(
            fmt='%(asctime)s %(message)s', datefmt='[%d/%m %H:%M]'
        ))
        self.logger.addHandler(self.logF)

    def __getattr__(self, name):
        return self.command(name)

    def command(self, name):
        def command_call(*args, no_timestamp=False, same_line=False):
            cmd = self.COMMAND[name]

            if args[0] not in self.COLOR:
                args = (cmd[1],) + args

            msg = self.parse_log(*args)
            if name == 'bad':
                msg = self.STYLE.bold(msg)
            msg = f'{cmd[0]("")}{msg}'

            if same_line:
                self.stream.terminator = ''

            if no_timestamp:
                self.stream.setFormatter(None)
                self.logger.info(msg)
                self.stream.setFormatter(self.formatter)
            else:
                self.logger.info(msg)

            self.stream.terminator = '\n'
            sys.stdout.flush()

        return command_call

    def parse_log(self, clr, msg, *args):
        msg = self.COLOR[clr](msg)
        if len(args) > 0:
            if args[0] not in self.COLOR:
                args = (clr,) + args
            msg = f'{msg} {self.STYLE.bold(self.parse_log(*args))}'
        return msg

    def log(self, *args):
        self.logger.info(self.parse_log(*args))

    def warn(self, *args, **kwargs):
        self.plain('yellow', 'WARNING:', *args, **kwargs)
