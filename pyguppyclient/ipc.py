import os

from flatbuffers import Builder

from pyguppyclient.decode import PROTO_VERSION, set_file_identifier

from pyguppyclient.guppy_ipc.Content import Content
import pyguppyclient.guppy_ipc.MessageData as MessageData
import pyguppyclient.guppy_ipc.ServerStats as ServerStats

import pyguppyclient.guppy_ipc.SimpleReplyData as SimpleReplyData
import pyguppyclient.guppy_ipc.SimpleRequestData as SimpleRequestData
import pyguppyclient.guppy_ipc.ConfigData as ConfigData

from pyguppyclient.guppy_ipc.SimpleReplyType import SimpleReplyType
from pyguppyclient.guppy_ipc.SimpleRequestType import SimpleRequestType
from pyguppyclient.guppy_ipc.ProtocolVersion import CreateProtocolVersion


def lookup(c):
    return {getattr(c, a): a for a in dir(c) if not a.startswith('_')}


replylookup = lookup(SimpleReplyType)
requestlookup = lookup(SimpleRequestType)
contentlookup = lookup(Content)


def simple_request(request_type, client_id=0, text=None, data=None):

    builder = Builder(50)

    if text is not None:
        text = builder.CreateString(text)

    # Create Simple Request Data
    SimpleRequestData.SimpleRequestDataStart(builder)
    SimpleRequestData.SimpleRequestDataAddType(
        builder,
        request_type
    )

    if text is not None:
        SimpleRequestData.SimpleRequestDataAddText(
            builder,
            text
        )

    if data is not None:
        SimpleRequestData.SimpleRequestDataAddData(
            builder,
            data,
        )

    contentOffset = SimpleRequestData.SimpleRequestDataEnd(builder)

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
        Content.SimpleRequestData
    )

    MessageData.MessageDataAddContent(
        builder,
        contentOffset
    )

    end = MessageData.MessageDataEnd(builder)
    builder.Finish(end)

    if os.environ.get("DEBUG_TRANSPORT"):
        print('->', "SimpleRequestData", "%-23s" % requestlookup[request_type], data, text, sep='\t')

    return set_file_identifier(builder.Output())


def simple_response(buff):
    req = MessageData.MessageData.GetRootAsMessageData(buff, 0)

    if req.Version().MajorVersion() != PROTO_VERSION[0]:
        raise Exception("Server IPC major version {} does not match "
                        "pyguppyclient IPC major version {} -- cannot decode "
                        "message.".format(req.Version().MajorVersion(),
                                          PROTO_VERSION[0]))

    if req.ContentType() == Content.SimpleReplyData:
        cls = SimpleReplyData.SimpleReplyData()
        cls.Init(req.Content().Bytes, req.Content().Pos)
        name = replylookup[cls.Type()]
        if os.environ.get("DEBUG_TRANSPORT"):
            print('<-', "SimpleReplyData  ", "%-23s" % name, cls.Data(), cls.Text(), sep='\t')

        if cls.Type() == SimpleReplyType.INVALID_CONFIG:
            raise ValueError("Invalid Config")
        if cls.Type() == SimpleReplyType.BAD_REQUEST:
            raise Exception("Bad request:", cls.Text())
        if cls.Type() == SimpleReplyType.BAD_REPLY:
            raise Exception(cls.Text().decode())
        if cls.Type() == SimpleReplyType.NONE_PENDING:
            return

    elif req.ContentType() == Content.SimpleRequestData:
        cls = SimpleRequestData.SimpleRequestData()
        cls.Init(req.Content().Bytes, req.Content().Pos)
        name = requestlookup[cls.Type()]
        if os.environ.get("DEBUG_TRANSPORT"):
            print('<-', "SimpleRequestData", "%-23s" % name, cls.Data(), cls.Text(), sep='\t')

    elif req.ContentType() == Content.ConfigData:
        cls = ConfigData.ConfigData()
        cls.Init(req.Content().Bytes, req.Content().Pos)
        name = "ConfigData"
        if os.environ.get("DEBUG_TRANSPORT"):
            print('<-', name, "\tCONFIG", sep="\t")

    elif req.ContentType() == Content.ServerStats:
        cls = ServerStats.ServerStats()
        cls.Init(req.Content().Bytes, req.Content().Pos)
        name = "ServerStats"
        if os.environ.get("DEBUG_TRANSPORT"):
            print('<-', name, "\tSTATS", sep="\t")

    elif req.ContentType() == Content.ReadBlockData:
        cls = called_read_block(req)
        name = "ReadBlockData"
        if os.environ.get("DEBUG_TRANSPORT"):
            print('<-', name, "\tPASS_READ", sep="\t")
    else:
        raise Exception("Unhandled Response %s" % req.ContentType())

    return cls
