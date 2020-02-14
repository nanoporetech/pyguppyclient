import os
from unittest import TestCase, main

from ont_fast5_api.conversion_tools.conversion_utils import get_fast5_file_list

from pyguppyclient.caller import Caller


class CallerTest(TestCase):
    read_dir = "tests/reads/testdata/multi"
    config_fast = os.environ.get("CONFIG", "dna_r9.4.1_450bps_fast")

    def setUp(self):
        self.files = get_fast5_file_list(self.read_dir, recursive=False)

    def test_caller(self):
        """ test the caller """
        caller = Caller(config=self.config_fast)
        caller.basecall(self.files)


if __name__ == "__main__":
    main()
