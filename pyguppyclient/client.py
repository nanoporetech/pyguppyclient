"""
Guppy Client
"""

import time
import asyncio
import logging

import zmq
import zmq.asyncio
from zmq.error import Again
from zmq import Context, REQ, LINGER, RCVTIMEO

from pyguppyclient.utils import parse_config
from pyguppyclient.ipc import simple_request, simple_response
from pyguppyclient.ipc import SimpleRequestType, SimpleReplyType
from pyguppyclient.decode import Config, raw_read_message


logger = logging.getLogger("pyguppyclient")


class GuppyClientBase:
    """
    Blocking Guppy Base Client
    """
    def __init__(self, config_name, host="localhost", port=5555, timeout=0.1, retries=50):
        self.timeout = timeout
        self.retries = retries
        self.config_name = parse_config(config_name)
        self.context = Context()
        self.socket = self.context.socket(REQ)
        self.socket.set(LINGER, 0)
        self.socket.set(RCVTIMEO, 100)
        self.socket.connect("tcp://%s:%s" % (host, port))
        self.client_id = 0

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
        attempts = 0
        while attempts < self.retries:
            attempts += 1
            try:
                config = self._load_config(self.config_name)
                res = self.send(SimpleRequestType.CONNECT, data=0, text=config.name)
                self.client_id = res.Data()
                return res
            except ConnectionError:
                time.sleep(self.timeout)

        raise ConnectionError(
            "Connect with '{}' failed after {} attempts".format(self.config_name, attempts)
        )

    def disconnect(self):
        return self.send(SimpleRequestType.DISCONNECT)

    def shut_down(self):
        return self.send(SimpleRequestType.TERMINATE)

    def get_configs(self):
        res = self.send(SimpleRequestType.GET_CONFIGS)
        return [res.Configs(i) for i in range(res.ConfigsLength())]

    def _load_config(self, config_name):
        loaded_configs = {Config(c).name: Config(c) for c in self.get_configs()}
        if config_name not in loaded_configs:
            response = self.send(SimpleRequestType.LOAD_CONFIG, text=config_name)
            if response.Type() == SimpleReplyType.INVALID_CONFIG:
                raise ValueError("'%s' could not be loaded by the server" % config_name)
            n = 0
            while n <= self.retries:
                n += 1
                loaded_configs = {Config(c).name: Config(c) for c in self.get_configs()}
                if config_name in loaded_configs:
                    break
                time.sleep(self.timeout)
            else:
                raise TimeoutError("Failed to load config '{}' after {} attempts".format(config_name, n))

        return loaded_configs[config_name]

    def get_statistics(self):
        return self.send(SimpleRequestType.GET_STATISTICS)

    def pass_read(self, read):
        return self.send(raw_read_message(
            self.client_id,
            read.read_tag,
            read.read_id,
            read.daq_offset,
            read.daq_scaling,
            read.signal,
        ), simple=False)


class GuppyBasecallerClient(GuppyClientBase):
    """
    Blocking Guppy Basecall Client
    """
    def basecall(self, read, state=False, trace=False):
        """
        Basecall a `ReadData` object and get a `CalledReadData` object

        :param trace: flag for returning the flipflop trace table from the server.
        :param state: flag for returning the state table (requires --post_out).
        """
        n = 0
        self.pass_read(read)
        while n < self.retries:
            n += 1
            result = self._get_called_read(state=state, trace=trace)
            if result is not None:
                return result[1]
            time.sleep(self.timeout)

        raise TimeoutError(
            "Basecall response not received after {}s for read '{}'".format(self.timeout, read.read_id)
        )

    def _get_called_read(self, state=False, trace=False):
        """
        Get the `CalledReadData` object back from the server
        """
        flag = (not trace) ^ state << 1
        res = self.send(SimpleRequestType.GET_FIRST_CALLED_BLOCK, data=flag)
        if res is None:
            return

        read, called = res
        while not called.complete:
            _, block = self.send(SimpleRequestType.GET_NEXT_CALLED_BLOCK, data=read.read_tag)
            called += block

        return read, called


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

    async def __aenter__(self):
        await self.connect(self.config)
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
        response = await self.send(SimpleRequestType.CONNECT, data=0, text=config)
        await asyncio.sleep(self.sleep)
        self.client_id = response.Data()

    async def disconnect(self):
        await self.send(SimpleRequestType.DISCONNECT)

    async def get_configs(self):
        res = await self.send(SimpleRequestType.GET_CONFIGS)
        return [res.Configs(i) for i in range(res.ConfigsLength())]

    async def get_statistics(self):
        stats = await self.send(SimpleRequestType.GET_STATISTICS)
        return stats

    async def pass_read(self, read):
        return await self.send(raw_read_message(
            self.client_id,
            read.read_tag,
            read.read_id,
            read.daq_offset,
            read.daq_scaling,
            read.signal,
        ), simple=False
        )

    async def get_called_read(self, trace=False, state=False):
        flag = (not trace) ^ state << 1
        res = await self.send(SimpleRequestType.GET_FIRST_CALLED_BLOCK, data=flag)

        if not res: return

        read, called = res
        while not called.complete:
            _, block = await self.send(SimpleRequestType.GET_NEXT_CALLED_BLOCK, data=read.read_tag)
            called += block

        return res
