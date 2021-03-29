"""
Guppy Client
"""

import time
import asyncio
import logging
from collections import deque

import zmq
import zmq.asyncio
from zmq.error import Again
from zmq import Context, REQ, LINGER, RCVTIMEO

from pyguppyclient.utils import parse_config
from pyguppyclient.ipc import simple_request, simple_response
from pyguppyclient.ipc import SimpleRequestType, SimpleReplyType
from pyguppyclient.decode import Config, PROTO_VERSION, pcl_called_read
from pyguppy_client_lib.client_lib import GuppyClient as PCLClient


logger = logging.getLogger("pyguppyclient")


class GuppyClientBase:
    """
    Blocking Guppy Base Client
    """
    def __init__(self, config_name, host="localhost", port=5555, timeout=0.1, retries=50, state=False, trace=False):
        self.timeout = timeout
        self.retries = retries
        self.config_name = parse_config(config_name)
        self.address = "%s:%s" % (host, port)
        self.context = Context()
        self.socket = self.context.socket(REQ)
        self.socket.set(LINGER, 0)
        self.socket.set(RCVTIMEO, 100)
        self.socket.connect("tcp://%s" % self.address)
        self.client_id = 0
        self.pcl_client = PCLClient(self.address, self.config_name)
        self.pcl_client.set_params({'state_data_enabled': state})
        self.pcl_client.set_params({'move_and_trace_enabled': trace})
        _init_pcl_client(self.pcl_client)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def send(self, message, data=None, text=None, simple=True):
        if simple:
            request = simple_request(message, client_id=self.client_id, text=text, data=data)
        else:
            request = message
        try:
            self.socket.send(request)
        except Again:
            self.socket.send(request)

        return simple_response(self.recv())

    def recv(self):
        for _ in range(self.retries):
            try:
                message = self.socket.recv()
                break
            except Again:
                time.sleep(self.timeout)
        else:
            raise Again()
        return message

    def connect(self):
        result = self.pcl_client.result
        ret = self.pcl_client.connect()
        if ret == result.already_connected:
            pass
        elif ret != result.success:
            raise ConnectionError(
                "Connect with '{}' failed: {}".format(
                    self.config_name, self.pcl_client.get_error_message()
                )
            )

    def disconnect(self):
        return self.pcl_client.disconnect()

    def shut_down(self):
        return self.send(SimpleRequestType.TERMINATE)

    def get_configs(self):
        res = self.send(SimpleRequestType.GET_CONFIGS)
        return [res.Configs(i) for i in range(res.ConfigsLength())]

    def get_statistics(self):
        return self.pcl_client.get_server_stats(self.address, 5)

    def pass_read(self, read):
        read_dict = {
            "read_tag": int(read.read_tag),
            "read_id": str(read.read_id),
            "daq_offset": float(read.daq_offset),
            "daq_scaling": float(read.daq_scaling),
            "raw_data": read.signal,
        }
        return self.pcl_client.pass_read(read_dict)


class GuppyBasecallerClient(GuppyClientBase):
    """
    Blocking Guppy Basecall Client
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.read_cache = deque()

    def basecall(self, read):
        """
        Basecall a `ReadData` object and get a `CalledReadData` object
        """
        n = 0
        self.pass_read(read)
        while n < self.retries:
            n += 1
            result = self._get_called_read()
            if result is not None:
                return result
            time.sleep(self.timeout)

        raise TimeoutError(
            "Basecall response not received after {}s for read '{}'".format(self.timeout, read.read_id)
        )

    def _get_called_read(self):
        """
        Get the `CalledReadData` object back from the server
        """
        if len(self.read_cache) == 0:
            reads = self.pcl_client.get_completed_reads()
            self.read_cache.extend(reads)

        try:
            read = self.read_cache.pop()
            return read, pcl_called_read(read)
        except IndexError:
            return


class GuppyAsyncClientBase:
    """
    Async Guppy Client Base
    """

    def __init__(self, config=None, host='localhost', port=5555, sleep=0):
        self.sleep = sleep
        self.config = config
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s:%s" % (host, port))
        self.socket.set(zmq.LINGER, 0)
        self.socket.set(zmq.RCVTIMEO, 500)
        self.client_id = 0
        self.pcl_client = PCLClient("%s:%s" % (host, port), self.config_name)
        _init_pcl_client(self.pcl_client)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await self.disconnect()

    async def send(self, message, data=None, text=None, simple=True):
        if simple:
            request = simple_request(message, client_id=self.client_id, data=data, text=text)
        else:
            request = message
        try:
            await self.socket.send(request)
        except Again:
            await self.socket.send(request)
        try:
            response = simple_response(await self.socket.recv())
        except Again:
            response = simple_response(await self.socket.recv())
        return response

    async def connect(self, config):
        result = self.pcl_client.result
        ret = await self.pcl_client.connect()
        if ret == result.already_connected:
            pass
        elif ret != result.success:
            raise ConnectionError(
                "Connect with '{}' failed: {}".format(self.config_name,
                                                      self.pcl_client.get_error_message())
            )

    async def disconnect(self):
        await self.pcl_client.disconnect()

    async def get_configs(self):
        res = await self.send(SimpleRequestType.GET_CONFIGS)
        return [res.Configs(i) for i in range(res.ConfigsLength())]

    async def get_statistics(self):
        stats = await self.pcl_client.get_server_stats(self.address, 5)
        return stats

    async def pass_read(self, read):
        read_dict = {
            "read_tag": int(read.read_tag),
            "read_id": str(read.read_id),
            "daq_offset": float(read.daq_offset),
            "daq_scaling": float(read.daq_scaling),
            "raw_data": read.signal,
        }
        return await self.pcl_client.pass_read(read_dict)

    async def get_called_read(self):
        """
        Get the `CalledReadData` object back from the server
        """
        if len(self.read_cache) == 0:
            reads, _ = await self.pcl_client.get_completed_reads()
            self.read_cache.extend(reads)

        try:
            read = self.read_cache.pop()
            return read, pcl_called_read(read)
        except IndexError:
            return


def _init_pcl_client(pcl_client):
    """
    Perform basic initialisation of a pyguppy_client_lib client.
    """
    pcl_proto_major_version = pcl_client.get_protocol_version()[0]
    if pcl_proto_major_version != PROTO_VERSION[0]:
        raise Exception("pyguppy_client_lib IPC major version {} does not "
                        "match pyguppyclient IPC major version {} -- "
                        "install correct version of "
                        "pyguppy_client_lib.".format(pcl_proto_major_version,
                                                     PROTO_VERSION[0]))
    params = {
        "max_reads_queued": 10000  # Number of reads the pcl_client can hold
    }
    pcl_client.set_params(params)
