"""MongoDB persistence backend for CrewAI Flows.

Implements CrewAI's ``FlowPersistence`` on MongoDB. One document per flow, keyed
by ``flow_uuid`` — each save upserts the latest state, so ``load_state`` returns
the most recent. Optionally prunes a message list via a ``MessageReducer``.

Note: current CrewAI defines ``FlowPersistence`` as a Pydantic ``BaseModel``, so
configuration is declared as pydantic fields and runtime objects (the Mongo
client, the reducer) are held as private attributes.
"""

import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr
from pymongo import MongoClient

from crewai.flow.persistence.base import FlowPersistence


class MongoDBFlowPersistence(FlowPersistence):
    """MongoDB-backed persistence for CrewAI Flows."""

    persistence_type: str = Field(default="MongoDBFlowPersistence")
    connection_string: str = "mongodb://127.0.0.1:27017/"
    database_name: str = "crewai_flows"
    collection_name: str = "flow_states"
    messages_key: str = "messages"

    _reducer: Any = PrivateAttr(default=None)
    _client: Any = PrivateAttr(default=None)
    _collection: Any = PrivateAttr(default=None)

    def __init__(
        self,
        *,
        connection_string: str = "mongodb://127.0.0.1:27017/",
        database_name: str = "crewai_flows",
        collection_name: str = "flow_states",
        client: Optional[MongoClient] = None,
        reducer: Any = None,
        messages_key: str = "messages",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            connection_string=connection_string,
            database_name=database_name,
            collection_name=collection_name,
            messages_key=messages_key,
            **kwargs,
        )
        self._reducer = reducer
        self._client = client
        self.init_db()

    def init_db(self) -> None:
        self._client = self._client or MongoClient(self.connection_string)
        self._collection = self._client[self.database_name][self.collection_name]
        self._collection.create_index("flow_uuid", unique=True)

    def save_state(
        self,
        flow_uuid: str,
        method_name: str,
        state_data: Union[Dict[str, Any], BaseModel],
    ) -> None:
        if isinstance(state_data, BaseModel):
            d: Dict[str, Any] = state_data.model_dump()
        else:
            d = dict(state_data)

        if self._reducer is not None and self.messages_key in d:
            result = self._reducer.reduce(existing=d[self.messages_key], new=[])
            d[self.messages_key] = result.surviving

        doc = {
            "flow_uuid": flow_uuid,
            "data": d,
            "method_name": method_name,
            "saved_at": datetime.datetime.now(datetime.timezone.utc),
        }
        self._collection.replace_one({"flow_uuid": flow_uuid}, doc, upsert=True)

    def load_state(self, flow_uuid: str) -> Optional[Dict[str, Any]]:
        doc = self._collection.find_one({"flow_uuid": flow_uuid})
        if doc is None:
            return None
        return doc["data"]
