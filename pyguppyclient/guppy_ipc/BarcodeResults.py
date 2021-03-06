# automatically generated by the FlatBuffers compiler, do not modify

# namespace: guppy_ipc

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class BarcodeResults(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsBarcodeResults(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = BarcodeResults()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def BarcodeResultsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x30\x30\x30\x32", size_prefixed=size_prefixed)

    # BarcodeResults
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # BarcodeResults
    def Id(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.String(o + self._tab.Pos)
        return None

    # BarcodeResults
    def BarcodeSequence(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.String(o + self._tab.Pos)
        return None

    # BarcodeResults
    def AlignedSequence(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            return self._tab.String(o + self._tab.Pos)
        return None

    # BarcodeResults
    def Score(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(10))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Float32Flags, o + self._tab.Pos)
        return 0.0

    # BarcodeResults
    def Begin(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(12))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Int32Flags, o + self._tab.Pos)
        return 0

def BarcodeResultsStart(builder): builder.StartObject(5)
def BarcodeResultsAddId(builder, id): builder.PrependUOffsetTRelativeSlot(0, flatbuffers.number_types.UOffsetTFlags.py_type(id), 0)
def BarcodeResultsAddBarcodeSequence(builder, barcodeSequence): builder.PrependUOffsetTRelativeSlot(1, flatbuffers.number_types.UOffsetTFlags.py_type(barcodeSequence), 0)
def BarcodeResultsAddAlignedSequence(builder, alignedSequence): builder.PrependUOffsetTRelativeSlot(2, flatbuffers.number_types.UOffsetTFlags.py_type(alignedSequence), 0)
def BarcodeResultsAddScore(builder, score): builder.PrependFloat32Slot(3, score, 0.0)
def BarcodeResultsAddBegin(builder, begin): builder.PrependInt32Slot(4, begin, 0)
def BarcodeResultsEnd(builder): return builder.EndObject()
