"""
pyguppyclient utils
"""

import os


def distribute(files, num_procs):
    """
    Distribute files accross num_procs, assumes files is sorted.

    >>> distribute([1, 2, 3, 4, 5, 6, 7, 8, 9], 4)
    [1, 5, 9, 2, 6, 3, 7, 4, 8]
    >>> distribute([1, 2, 3, 4, 5, 6, 7, 8], 4)
    [1, 5, 2, 6, 3, 7, 4, 8]
    >>> distribute([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 4)
    [1, 5, 9, 2, 6, 10, 3, 7, 4, 8]
    """
    shuf = list()

    for proc in range(num_procs):
        proc_idx = 0
        while proc_idx + proc < len(files):
            shuf.append(files[proc_idx+proc])
            proc_idx += num_procs
    return shuf


def batches(files, n=100, stride=1):
    """
    Yield successive n-sized batches from `files`.

    >>> list(batches([1, 2, 3, 4, 5, 6, 7, 8, 9]))
    [[1, 2, 3, 4, 5, 6, 7, 8, 9]]
    >>> list(batches([1, 2, 3, 4, 5, 6, 7, 8, 9], n=2))
    [[1, 2], [3, 4], [5, 6], [7, 8], [9]]
    >>> list(batches([1, 2, 3, 4, 5, 6, 7, 8, 9], n=3))
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    """
    for i in range(0, len(files), n):
        yield files[i:i + n]


def bases_fmt(bases, suffix="bases"):
    """
    Return bases in human readable format.

    >>> bases_fmt(10)
    '10 bases'
    >>> bases_fmt(10001)
    '10.00 Kbases'
    >>> bases_fmt(23123456789)
    '23.12 Gbases'
    """
    for idx, unit in enumerate(['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']):
        if abs(bases) < 1000.0:
            if idx == 0:
                return "%.0f %s%s" % (bases, unit, suffix)
            else:
                return "%.2f %s%s" % (bases, unit, suffix)
        bases /= 1000.0


def parse_config(filename):
    """
    Parse a config filename removing the path and the extension
    
    >>> parse_config('dna_r9.4.1_450bps_hac')
    'dna_r9.4.1_450bps_hac'
    >>> parse_config('dna_r9.4.1_450bps_hac.cfg')
    'dna_r9.4.1_450bps_hac'
    >>> parse_config('/tmp/data/dna_r9.4.1_450bps_hac.cfg')
    'dna_r9.4.1_450bps_hac'
    """
    if filename:
        if filename.endswith('.cfg'):
            filename = filename[:-4]
        return os.path.basename(filename)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
