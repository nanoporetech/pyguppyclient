import os
import time
from unittest import TestCase, main

from pyguppyclient.decode import Config
from pyguppyclient.io import yield_reads
from pyguppyclient import GuppyBasecallerClient


class ClientTest(TestCase):

    port = 5555
    read_file = "tests/reads/testdata/single/read1.fast5"
    config_hac = os.environ.get("CONFIG_HAC", "dna_r9.4.1_450bps_hac")
    config_fast = os.environ.get("CONFIG_FAST", "dna_r9.4.1_450bps_fast")

    def setUp(self):
        self.read_loader = yield_reads(self.read_file)
        self.client = GuppyBasecallerClient(config_name=self.config_fast, port=self.port, trace=True, state=True)
        self.client.connect()

    def tearDown(self):
        self.client.disconnect()

    def test_get_configs(self):
        """ test loaded configs """
        self.assertTrue(self.config_fast in [Config(c).name for c in self.client.get_configs()])

    def test_without_read(self):
        """ test the client api without sending a read """
        self.client.get_statistics()
        self.client.get_configs()

    def test_read_without_state(self):
        """ test a read without state """
        self.client.pass_read(next(self.read_loader))
        time.sleep(1)
        self.client._get_called_read()

    def test_read_with_state(self):
        """ test a read with state """
        self.client.pass_read(next(self.read_loader))
        time.sleep(1)
        res, called = self.client._get_called_read()
        self.assertTrue(called.state is not None)
        self.assertTrue(called.trace is not None)
        self.assertTrue(called.move is not None)

    def test_invalid_config(self):
        """ try and load in invalid config """
        bad_client = GuppyBasecallerClient(config_name="not_a_config", port=self.port)
        with self.assertRaises(ConnectionError):
            bad_client.connect()


if __name__ == "__main__":
    os.environ["DEBUG_TRANSPORT"] = "1"
    main(verbosity=0)
