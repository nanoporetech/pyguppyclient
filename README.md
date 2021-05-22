# pyguppyclient

[![PyPI version](https://badge.fury.io/py/pyguppyclient.svg)](https://badge.fury.io/py/pyguppyclient)

Full Python client library for communicating with `guppy_basecall_server`.

```bash
$ pip install pyguppyclient
```

## Requirements

Guppy 5.0 or later is required and the `guppy_basecall_server` must already be running.

```bash
$ guppy_basecall_server --config dna_r9.4.1_450bps_fast.cfg -p 5555 -l /tmp/guppy -x 'cuda:0'
```

## Example

The simplest usage is the `GuppyBasecallerClient` class which takes a `config` name and provides a `basecall` method that takes a read and returns a `CalledReadData` object.

```python
from pyguppyclient import GuppyBasecallerClient, yield_reads

config = "dna_r9.4.1_450bps_fast"
read_file = "reads.fast5"

with GuppyBasecallerClient(config_name=config, trace=True) as client:
    for read in yield_reads(read_file):
        called = client.basecall(read)
        print(read.read_id, called.seq[:50], called.move)
```

See the example client for the usage of the `Caller` class that uses multiprocessing to distribute the reading of `fast5` files.

```bash
$ ./examples/pyguppyclient -t 8 dna_r9.4.1_450bps_fast /data/reads > pyguppyclient.fastq
```

## Developer Quick Start

```bash
$ git clone https://github.com/nanoporetech/pyguppyclient.git
$ cd pyguppy-client
$ python3 -m venv venv3
$ source ./venv3/bin/activate
(venv3) $ pip install -r requirements.txt -r development.txt
(venv3) $ python setup.py develop
(venv3) $ make test
```

### Licence and Copyright

(c) 2020 Oxford Nanopore Technologies Ltd.

pyguppyclient is distributed under the terms of the Oxford Nanopore
Technologies, Ltd.  Public License, v. 1.0.  If a copy of the License
was not distributed with this file, You can obtain one at
http://nanoporetech.com

### Research Release

Research releases are provided as technology demonstrators to provide early access to features or stimulate Community development of tools. Support for this software will be minimal and is only provided directly by the developers. Feature requests, improvements, and discussions are welcome and can be implemented by forking and pull requests. However much as we would like to rectify every issue and piece of feedback users may have, the developers may have limited resource for support of this software. Research releases may be unstable and subject to rapid iteration by Oxford Nanopore Technologies.
