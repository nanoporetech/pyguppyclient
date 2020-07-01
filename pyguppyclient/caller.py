"""
pyguppyclient callers objects
"""

import math
import logging
from itertools import chain
from time import sleep
from multiprocessing import Manager
from concurrent.futures import ProcessPoolExecutor

from pyguppyclient.io import yield_reads
from pyguppyclient.utils import distribute, batches, parse_config
from pyguppyclient.client import GuppyBasecallerClient

logger = logging.getLogger("pyguppyclient")
logger.setLevel(logging.DEBUG)


class Caller:
    """
    A caller that uses multiprocessing to distribute the reading of
    fast5 files, and use multiple clients to basecall reads concurrently.

    :param config: the guppy config file to use for basecalling.
    :param callback: function for process the results, it will be passed a ReadData,
                     CalledReadData and Lock object. The Caller use multiple processes
                     for performance so a lock is provide for accessing a shared resource
                     such as a file handle.
    :param host: the host address of the guppy_basecall_server.
    :param port: the port of the guppy_basecall_server.
    :param procs: the number of processes to use.
    :param inflight: number of inflight reads to limit each process to.
    """

    def __init__(self, config, callback=None, host='127.0.0.1', port=5555, inflight=50, procs=4):
        self.host = host
        self.port = port
        self.procs = procs
        self.snooze = 1e-2
        self.callback = callback
        self.inflight = inflight
        self.config = parse_config(config)

    def basecall(self, files):
        """
        Basecall a list `files` across a process pool of workers.

        :param files: a list of filenames to basecall.
        :returns: a tuple of the total reads and raw samples processed.
        """
        if len(files) == 0: raise FileNotFoundError("No files found to basecall")

        manager = Manager()
        batch_size = math.ceil(len(files) / self.procs)
        files = distribute(files, self.procs)
        work = batches(files, n=min(batch_size, self.inflight))
        self.lock = manager.Lock()

        with ProcessPoolExecutor(max_workers=self.procs) as pool:
            return sum(pool.map(self.basecall_batch, work))

    def basecall_batch(self, files):
        """
        Basecall a list `files`.

        :param files: a list of filenames to basecall.
        :returns: the total number of raw samples processed.
        """
        done = 0
        samples = 0
        reads = [read for fn in files for read in yield_reads(fn)]

        with GuppyBasecallerClient(config_name=self.config, host=self.host, port=self.port) as client:
            # submit reads
            for read in reads:
                client.pass_read(read)

            # poll to collect called reads
            while done < len(reads):
                res = client._get_called_read()

                if res is None:
                    sleep(self.snooze)
                    continue

                done += 1
                read, called = res
                samples += called.trimmed_samples

                if self.callback:
                    self.callback(read, called, self.lock)

        return samples
