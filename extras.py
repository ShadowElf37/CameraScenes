import os


def get_lines_of_code(start_path='.', exts=('js', 'py', 'html', 'css')):
    total_lines = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            # skip if it is symbolic link
            if not os.path.islink(fp) and (os.path.splitext(fp)[1] or 'nope') in '.' + ' .'.join(exts):
                print('Counting', fp)
                with open(fp, 'rb') as f:
                    total_lines += sum([1 for l in f.readlines() if l.strip()])
    return total_lines


if __name__ == "__main__":
    print('Counted %s lines of code.' % get_lines_of_code(exts=['py']))
