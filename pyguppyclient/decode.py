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


PROTO_VERSION = (7, 0, 0)


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


def pcl_called_read(pcl_read):
    """
    Converts a read returned by pyguppy_client_lib into a CalledRead
    """
    datasets = pcl_read['datasets']
    metadata = pcl_read['metadata']

    seq = datasets['sequence']
    qual = datasets['qstring']
    events = int(metadata['duration'] / metadata['model_stride'])
    seqlen = metadata['sequence_length']
    state_size = metadata['state_size']
    model_type = metadata['basecall_type']
    trimmed_samples = metadata['duration'] - metadata['trimmed_samples']
    model_stride = metadata['model_stride']
    qscore = metadata['mean_qscore']

    state = datasets.get('state_data')
    move = datasets.get('movement')

    trace = None
    weight = None
    if 'flipflop_trace' in datasets:
        trace = datasets['flipflop_trace'] * (1.0 / 255.0)
    elif 'rle_runlength' in datasets:
        trace = {
            'base': datasets.get('rle_base'),
            'shape': datasets.get('rle_shape'),
            'scale': datasets.get('rle_scale'),
            'weight': datasets.get('rle_weight'),
            'index': datasets.get('rle_index'),
            'runlength': datasets.get('rle_runlength'),
        }

    mod_probs = datasets.get('base_mod_probs')
    mod_alpha = None
    long_names = None
    if mod_probs:
        mod_probs = mod_probs * (1.0 / 255.0)
        mod_alpha = metadata.get('base_mod_alphabet')
        long_names = metadata.get('base_mod_long_names')

    barcode = None
    if 'barcode_front_id' in metadata:
        barcode = {
            'trim_front': metadata.get('barcode_trim_front'),
            'trim_rear': metadata.get('barcode_trim_rear'),
            'id': metadata.get('barcode_full_arrangement'),
            'normalized_id': metadata.get('barcode_arrangement'),
            'kit': metadata.get('barcode_kit'),
            'variant': metadata.get('barcode_variant'),
            'score': metadata.get('barcode_score'),
        }
        if metadata['barcode_front_id']:
            barcode['front'] = {
                'id': metadata.get('barcode_front_id'),
                'barcode_sequence': metadata.get('barcode_front_refseq'),
                'aligned_sequence': metadata.get('barcode_front_foundseq'),
                'score': metadata.get('barcode_front_score'),
                'begin': metadata.get('barcode_front_begin_index'),
            }
        if metadata['barcode_rear_id']:
            barcode['rear'] = {
                'id': metadata.get('barcode_rear_id'),
                'barcode_sequence': metadata.get('barcode_rear_refseq'),
                'aligned_sequence': metadata.get('barcode_rear_foundseq'),
                'score': metadata.get('barcode_rear_score'),
                'begin': metadata.get('barcode_rear_end_index'),
            }
        if metadata['barcode_mid_front_id']:
            barcode['mid_front'] = {
                'id': metadata.get('barcode_mid_front_id'),
                'score': metadata.get('barcode_mid_front_score'),
                'end': metadata.get('barcode_mid_front_end_index'),
            }
        if metadata['barcode_mid_rear_id']:
            barcode['mid_rear'] = {
                'id': metadata.get('barcode_mid_rear_id'),
                'score': metadata.get('barcode_mid_rear_score'),
                'end': metadata.get('barcode_mid_rear_end_index'),
            }

    scaling = {
        'median': metadata.get('median'),
        'med_abs_dev': metadata.get('med_abs_dev'),
        'pt_median': metadata.get('pt_median'),
        'ptsd': metadata.get('ptsd'),
        'adapter_max': metadata.get('adapter_max'),
        'pt_detect_success': metadata.get('pt_detect_success'),
    }

    complete = True

    return CalledReadData(seq, qual, events, seqlen, state_size,  model_type,
                      trimmed_samples, model_stride, qscore, state, move,
                      weight, trace, mod_alpha, mod_probs,
                      long_names, barcode, scaling, complete)


def set_file_identifier(buff):
    """
    https://github.com/google/flatbuffers/issues/4814
    """
    buff[4:8] = b'%04x' % PROTO_VERSION[0]
    return buff
            
