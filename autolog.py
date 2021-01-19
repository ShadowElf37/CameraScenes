"""
This works as a drop-in for any project
Just import in a file and all stdout/stderr will automatically go to a logs folder on exit
"""

import sys, io, datetime, os.path, atexit

LOG_BUFFER = sys.stdout = sys.stderr = io.StringIO()

if not os.path.exists('logs'):
    os.mkdir('logs')

def stash_log():
    with open(os.path.join('logs', datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')), 'w') as log:
        log.write(LOG_BUFFER.getvalue())

atexit.register(stash_log)
