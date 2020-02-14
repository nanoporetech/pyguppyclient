import random

import numpy as np
from flatbuffers import Builder

from pyguppyclient.guppy_ipc.Content import Content
import pyguppyclient.guppy_ipc.MessageData as MessageData

import pyguppyclient.guppy_ipc.ReadBlockData as ReadBlockData
import pyguppyclient.guppy_ipc.ReadBlockType as ReadBlockType
import pyguppyclient.guppy_ipc.TraceData as TraceData
import pyguppyclient.guppy_ipc.FlipflopTraceData as FlipflopTraceData
import pyguppyclient.guppy_ipc.RunlengthTraceData as RunlengthTraceData
from pyguppyclient.guppy_ipc.ProtocolVersion import CreateProtocolVersion


PROTO_VERSION = (1, 0, 0)


class Config:
    """
    Simple configuration class
    """
    def __init__(self, configuration):
        self.name = configuration.ConfigName().decode()
        self.label_length = configuration.LabelLength()
        self.model_type = configuration.ModelType().decode()
        self.model_stride = configuration.ModelStride()

    def __repr__(self):
        return "%s" % (self.__class__.__name__)


class ReadData:
    """
    Lightweight read class suitable for sending to guppy_basecall_server.

    :param signal: np.int16 raw daq signal.
    :param read_id: unique identifier for the `read`.
    :param offset: the channel offset value.
    :param scaling: the channel scaling value.
    """
    def __init__(self, signal, read_id, offset=0, scaling=1.0):
        self.signal = signal
        self.read_id = read_id
        self.total_samples = len(signal)
        self.daq_offset = offset
        self.daq_scaling = scaling
        self.block_index = None
        self.total_blocks = None
        self.read_tag = random.randint(0, int(2**32 - 1))

    def __repr__(self):
        return "%s" % (self.__class__.__name__)


class CalledReadData:
    """
    Lightweight called read class returned from guppy_basecall_server.

    :param seq: the basecalled sequence.
    :param seqlen: the expected sequence length.
    :param qual: the per base quality string for the call.
    :param qscore: the median quality score.
    :param events: the number of timesteps output.
    :param state: the full posterior probabilities from the network prior to decoding.
    :param state_size: the number of features in the posterior output.
    :param model_type: the type of model used for basecalling.
    :param model_stride: the model stride.
    :param trimmed_samples: the number of samples discarded for the basecall.
    :param move: the move table for aligning the call sequence back to the signal.
    :param trace: the flipflip trace table.
    :param mod_probs: the modified base probabilities.
    :param mod_alphabet: a string containing the model labels.
    :param mod_long_names: a list of modified base long names.
    """
    def __init__(
            self, seq, qual, events, seqlen, state_size,  model_type,
            trimmed_samples, model_stride, qscore, state=None, move=None,
            weight=None, trace=None, mod_alpha=None, mod_probs=None,
            long_names=None, barcode=None, scaling=None, complete=True
    ):
        self.seq = seq
        self.qual = qual
        self.qscore = qscore
        self.events = events
        self.seqlen = seqlen
        self.state_size = state_size
        self.model_type = model_type
        self.model_stride = model_stride
        self.trimmed_samples = trimmed_samples
        self.state = state
        self.move = move
        self.weight = weight
        self.trace = trace
        self.barcode = barcode
        self.scaling = scaling
        self.complete = complete
        self.mod_probs = mod_probs
        self.mod_alphabet = mod_alpha
        self.mod_long_names = long_names

    def __repr__(self):
        return '%s' % (self.__class__.__name__)

    def _concat(self, a, b):
        if isinstance(a, np.ndarray):
            return np.concatenate([a, b])
        return a

    def __iadd__(self, other):
        self.complete = other.complete
        self.seq += other.seq
        self.qual += other.qual
        self.state = self._concat(self.state, other.state)
        self.move = self._concat(self.move, other.move)
        self.weight = self._concat(self.weight, other.weight)
        self.trace =  self._concat(self.trace, other.trace)
        self.mod_probs = self._concat(self.mod_probs, other.mod_probs)
        return self


def set_file_identifier(buff):
    """
    https://github.com/google/flatbuffers/issues/4814
    """
    buff[4:8] = b'%04x' % PROTO_VERSION[0]
    return buff


def raw_read_message(client_id, read_tag, read_id, daq_offset, daq_scaling, raw):
    builder = Builder(raw.size * 2 + 200)
    read_id_offset = builder.CreateString(read_id)
    raw_offset = builder.CreateNumpyVector(raw)

    # Create the ReadBlockData object.
    ReadBlockData.ReadBlockDataStart(builder)
    ReadBlockData.ReadBlockDataAddType(
        builder,
        ReadBlockType.ReadBlockType.PASS_FIRST_RAW_BLOCK
    )
    ReadBlockData.ReadBlockDataAddReadTag(
        builder,
        read_tag
    )
    ReadBlockData.ReadBlockDataAddBlockIndex(
        builder,
        0
    )
    ReadBlockData.ReadBlockDataAddTotalBlocks(
        builder,
        1
    )
    ReadBlockData.ReadBlockDataAddTotalSamples(
        builder,
        raw.size
    )
    ReadBlockData.ReadBlockDataAddDaqOffset(
        builder,
        daq_offset
    )
    ReadBlockData.ReadBlockDataAddDaqScaling(
        builder,
        daq_scaling
    )
    ReadBlockData.ReadBlockDataAddReadId(
        builder,
        read_id_offset
    )
    ReadBlockData.ReadBlockDataAddRawData(
        builder,
        raw_offset
    )

    content_offset = ReadBlockData.ReadBlockDataEnd(builder)

    # Create Message Data
    MessageData.MessageDataStart(builder)

    MessageData.MessageDataAddVersion(
        builder,
        CreateProtocolVersion(builder, *PROTO_VERSION)
    )

    MessageData.MessageDataAddSenderId(
        builder,
        client_id
    )

    MessageData.MessageDataAddContentType(
        builder,
        Content.ReadBlockData
    )

    MessageData.MessageDataAddContent(
        builder,
        content_offset
    )

    end = MessageData.MessageDataEnd(builder)
    builder.Finish(end)

    return set_file_identifier(builder.Output())


def called_read_block(res):

    if res.ContentType() != Content.ReadBlockData:
        raise Exception("Unhandled Response %s" % res.ContentType())

    read_block = ReadBlockData.ReadBlockData()
    read_block.Init(res.Content().Bytes, res.Content().Pos)

    read_obj = ReadData([], read_block.ReadId().decode())
    read_obj.read_tag = read_block.ReadTag()
    read_obj.block_index = read_block.BlockIndex()
    read_obj.total_blocks = read_block.TotalBlocks()
    read_obj.total_samples = read_block.TotalSamples()
    read_obj.daq_offset = read_block.DaqOffset()
    read_obj.daq_scaling = read_block.DaqScaling()
    read_obj.signal = read_block.RawDataAsNumpy()

    called_read = None
    called_data = read_block.CalledData()

    if called_data is not None:

        called_read = CalledReadData(
            called_data.Sequence().decode(),
            called_data.Qstring().decode(),
            called_data.TotalEvents(),
            called_data.TotalSequenceLength(),
            called_data.StateSize(),
            called_data.ModelType().decode(),
            called_data.TrimmedSamples(),
            called_data.ModelStride(),
            called_data.MeanQscore(),
        )

        if called_data.StateDataLength() > 0:
            state_data = called_data.StateDataAsNumpy()
            state_size = called_data.StateSize()
            called_read.state = format_state_data(state_data, state_size)

        trace_data = called_data.TraceResults()

        if trace_data is not None:
            if called_data.TraceResultsType() == TraceData.TraceData.FlipflopTraceData:
                trace_obj = FlipflopTraceData.FlipflopTraceData()
                trace_obj.Init(called_data.TraceResults().Bytes, called_data.TraceResults().Pos)
                called_read.move, called_read.trace = format_flipflop_trace(trace_obj)
            if called_data.TraceResultsType() == TraceData.TraceData.RunlengthTraceData:
                trace_obj = RunlengthTraceData.RunlengthTraceData()
                trace_obj.Init(called_data.TraceResults().Bytes, called_data.TraceResults().Pos)
                called_read.trace = format_runlength_trace(trace_obj)

        barcode_data = called_data.BarcodeResults()
        if barcode_data is not None:
            called_read.barcode = format_barcode_data(barcode_data)

        mod_data = called_data.BaseModResults()
        if mod_data is not None:
            called_read.mod_alphabet = mod_data.Alphabet().decode()
            called_read.mod_long_names = mod_data.LongNames().decode().split(' ')
            called_read.mod_probs = format_mod_data(mod_data, len(called_read.mod_alphabet))

        scaling_data = called_data.ScalingResults()
        if scaling_data is not None:
            called_read.scaling = format_scaling_data(scaling_data)
        called_read.complete = (read_block.TotalBlocks() == read_block.BlockIndex() + 1)

    return read_obj, called_read


def format_state_data(state_data, state_size):
    n = int(state_data.size / state_size)
    return state_data.reshape(n, state_size)


def format_flipflop_trace(trace_data):
    if trace_data.MoveDataLength() > 0:
        move = trace_data.MoveDataAsNumpy()
    else:
        move = None

    if trace_data.TraceDataLength() > 0:
        scaled_trace = trace_data.TraceDataAsNumpy()
        trace = scaled_trace * (1.0 / 255.0)
        n = int(trace.size / 8)
        trace = trace.reshape(n, 8)
    else:
        trace = None
    return move, trace


def format_mod_data(mod_data, alphabet_size):
    scaled_probs = mod_data.ModProbsAsNumpy()
    mod_probs = scaled_probs * (1.0 / 255.0)
    return mod_probs.reshape(alphabet_size, -1)


def format_runlength_trace(trace_data):
    return {
        'base': trace_data.BaseAsNumpy(),
        'shape': trace_data.ShapeAsNumpy(),
        'scale': trace_data.ScaleAsNumpy(),
        'weight': trace_data.WeightAsNumpy(),
        'index': trace_data.IndexAsNumpy(),
        'runlength': trace_data.RunlengthAsNumpy()
    }


def format_barcode_data(barcode_data):
    barcode_results = {
        'trim_front': barcode_data.BarcodeTrimFront(),
        'trim_rear': barcode_data.BarcodeTrimRear(),
        'id': barcode_data.Id(),
        'normalized_id': barcode_data.NormalisedId(),
        'kit': barcode_data.Kit(),
        'variant': barcode_data.Variant(),
        'score': barcode_data.Score()
    }
    front = barcode_data.Front()
    if front:
        barcode_results['front'] = {
            'id': front.Id(),
            'barcode_sequence': front.BarcodeSequence(),
            'aligned_sequence': front.AlignedSequence(),
            'score': front.Score(),
            'begin': front.Begin()
        }
    back = barcode_data.Back()
    if back:
        barcode_results['back'] = {
            'id': back.Id(),
            'barcode_sequence': back.BarcodeSequence(),
            'aligned_sequence': back.AlignedSequence(),
            'score': back.Score(),
            'begin': back.Begin()
        }
    mid_front = barcode_data.MidFront()
    if mid_front:
        barcode_results['mid_front'] = {
            'id': mid_front.Id(),
            'score': mid_front.Score(),
            'end': mid_front.End()
        }
    mid_rear = barcode_data.MidRear()
    if mid_rear:
        barcode_results['mid_rear'] = {
            'id': mid_rear.Id(),
            'score': mid_rear.Score(),
            'end': mid_rear.End()
        }
    return barcode_results



def format_scaling_data(scaling_data):
    return {
        'median': scaling_data.Median(),
        'med_abs_dev': scaling_data.MedAbsDev(),
        'pt_median': scaling_data.PtMedian(),
        'ptsd': scaling_data.Ptsd(),
        'adapter_max': scaling_data.AdapterMax(),
        'pt_detect_success': scaling_data.PtDetectSuccess()
    }
