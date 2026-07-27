"""
E2E tests for MongoDBFlowPersistence against a real MongoDB.

Requires a reachable MongoDB (MONGO_URI, default mongodb://127.0.0.1:27017/).
"""
import os
import uuid

import pytest
from pydantic import BaseModel

from crewai_persistence_mongodb import MongoDBFlowPersistence
from agentstate_reducer import MessageReducer
from agentstate_reducer.models import ReducerConfig

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/")
DB = os.environ.get("CREWAI_MONGO_DB", "crewai_flows_test")


def make(**kwargs):
    return MongoDBFlowPersistence(connection_string=MONGO_URI, database_name=DB, **kwargs)


def build_messages(n_pairs):
    msgs = []
    for i in range(n_pairs):
        msgs.append({"role": "human", "content": f"msg {i}"})
        msgs.append({"role": "ai", "content": f"reply {i}"})
    return msgs


def test_save_and_load_dict_state():
    p = make()
    fid = str(uuid.uuid4())
    p.save_state(fid, "my_step", {"id": fid, "user": "kamal", "step": 3, "nested": {"a": 1}})
    loaded = p.load_state(fid)
    assert loaded["user"] == "kamal"
    assert loaded["step"] == 3
    assert loaded["nested"] == {"a": 1}


def test_save_and_load_pydantic_state():
    class MyState(BaseModel):
        id: str
        counter: int
        label: str

    p = make()
    fid = str(uuid.uuid4())
    p.save_state(fid, "step", MyState(id=fid, counter=7, label="hello"))
    loaded = p.load_state(fid)
    assert loaded["counter"] == 7
    assert loaded["label"] == "hello"


def test_load_missing_returns_none():
    assert make().load_state(str(uuid.uuid4())) is None


def test_latest_save_wins():
    p = make()
    fid = str(uuid.uuid4())
    p.save_state(fid, "s1", {"id": fid, "v": 1})
    p.save_state(fid, "s2", {"id": fid, "v": 2})
    assert p.load_state(fid)["v"] == 2


def test_no_reducer_keeps_all_messages():
    p = make()
    fid = str(uuid.uuid4())
    msgs = build_messages(10)
    p.save_state(fid, "chat", {"id": fid, "messages": msgs})
    assert p.load_state(fid)["messages"] == msgs


def test_reducer_caps_messages():
    reducer = MessageReducer(config=ReducerConfig(min_messages=4, max_messages=6))
    p = make(reducer=reducer, messages_key="messages")
    fid = str(uuid.uuid4())
    p.save_state(fid, "chat", {"id": fid, "messages": build_messages(10)})
    assert len(p.load_state(fid)["messages"]) <= 5


def test_reducer_preserves_recent_tail():
    reducer = MessageReducer(config=ReducerConfig(min_messages=4, max_messages=6))
    p = make(reducer=reducer, messages_key="messages")
    fid = str(uuid.uuid4())
    msgs = build_messages(10)
    p.save_state(fid, "chat", {"id": fid, "messages": msgs})
    surviving = p.load_state(fid)["messages"]
    assert surviving[0] == msgs[0]
    assert surviving[-1] == {"role": "ai", "content": "reply 9"}
