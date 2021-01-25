"""
This works as a drop-in for any project
Just import in a file and all stdout/stderr will automatically go to a logs folder on exit
"""

import sys, io, datetime, os.path, atexit

STDOUT = sys.stdout
STDERR = sys.stderr
LOG_BUFFER = sys.stdout = io.StringIO()

if not os.path.exists('logs'):
    os.mkdir('logs')

def dual_writer(writef1, writef2):
    def write(*args, **kwargs):
        writef1(*args, **kwargs)
        writef2(*args, **kwargs)
    return write


STDERR.write = dual_writer(STDERR.write, LOG_BUFFER.write)
LOG_BUFFER.write = dual_writer(STDOUT.write, LOG_BUFFER.write)

def stash_log():
    with open(os.path.join('logs', datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')), 'w') as log:
        log.write(LOG_BUFFER.getvalue())

atexit.register(stash_log)
