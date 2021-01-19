import sys
import io
import datetime
import os.path

LOG_BUFFER = io.StringIO()
sys.stderr = LOG_BUFFER
sys.stdout = LOG_BUFFER

if not os.path.exists('logs'):
    os.mkdir('logs')

def stash_log():
    with open(os.path.join('logs', datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')), 'w') as log:
        log.write(LOG_BUFFER.getvalue())

import atexit
atexit.register(stash_log)
