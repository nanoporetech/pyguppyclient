import os
import logging
from logging.handlers import RotatingFileHandler
from ont_fast5_api.fast5_interface import get_fast5_file

from pyguppyclient.decode import ReadData

logger = logging.getLogger("pyguppyclient")


def yield_reads(filename):
    """
    Yield a `RawRead` object for every read in the .fast5 `filename`.
    :param filename: Path to a fast5 file
    :return: `ReadData` for every read in the input file `filename`
    """
    with get_fast5_file(filename, 'r') as f5_fh:
        for read in f5_fh.get_reads():
            raw = read.handle[read.raw_dataset_name][:]
            channel_info = read.handle[read.global_key + 'channel_id'].attrs
            scaling = channel_info['range'] / channel_info['digitisation']
            offset = int(channel_info['offset'])
            yield ReadData(raw, read.read_id, scaling=scaling, offset=offset)


def load_reads(filename):
    """
    List containing a `RawRead` for every read in the .fast `filename`.
    :param filename: Path to a fast5 file
    :return: `ReadData` for every read in the input file `filename`
    """
    return list(yield_reads(filename))


def write_fasta(read_id, sequence, fd):
    """
    Write a read into a fastq format
    """
    fd.write(">%s\n" % read_id)
    fd.write("%s\n" % sequence)


def write_fastq(read_id, sequence, qstring, fd):
    """
    Write a read into a fastq format
    """
    fd.write('@%s\n' % read_id)
    fd.write('%s\n' % sequence)
    fd.write('+\n')
    fd.write('%s\n' % qstring)


def setup_logger(logdir, filename, level=logging.INFO):
    """
    Setup a logger
    """
    log_file = os.path.join(logdir, filename)
    handler = RotatingFileHandler(log_file, maxBytes=1e6, backupCount=9)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger("pyguppyclient")
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    logger = logging.getLogger("asyncio")
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


if __name__ == "__main__":
    import doctest
    doctest.testmod()
