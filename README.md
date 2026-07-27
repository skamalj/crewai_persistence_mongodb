# crewai-persistence-mongodb

MongoDB persistence backend for [CrewAI Flows](https://docs.crewai.com/concepts/flows). Persists flow state across runs, with optional built-in message pruning via [agentstate-reducer](https://pypi.org/project/agentstate-reducer/). Implements CrewAI's `FlowPersistence` interface.

## Installation

```bash
pip install crewai-persistence-mongodb
pip install "crewai-persistence-mongodb[reducer]"   # with message pruning
```

**Requires Python 3.10–3.13** and a reachable MongoDB (local, Atlas, self-hosted).

## Usage

```python
from crewai.flow.flow import Flow, start
from crewai.flow.persistence import persist
from crewai_persistence_mongodb import MongoDBFlowPersistence

backend = MongoDBFlowPersistence(connection_string="mongodb://127.0.0.1:27017/")

@persist(backend)
class MyFlow(Flow[MyState]):
    @start()
    def begin(self):
        self.state.counter += 1
```

With message pruning:

```python
from agentstate_reducer import MessageReducer
backend = MongoDBFlowPersistence(
    connection_string="mongodb://127.0.0.1:27017/",
    reducer=MessageReducer(min_messages=10, max_messages=20),
    messages_key="messages",
)
```

## API

### `MongoDBFlowPersistence(*, connection_string="mongodb://127.0.0.1:27017/", database_name="crewai_flows", collection_name="flow_states", client=None, reducer=None, messages_key="messages")`

| Parameter | Description |
|---|---|
| `connection_string` | MongoDB URI (local / Atlas `mongodb+srv://…`) |
| `database_name` / `collection_name` | where flow states live |
| `client` | optional pre-built `pymongo.MongoClient` |
| `reducer` | optional `MessageReducer` to prune `messages_key` before save |
| `messages_key` | state field holding the message list (default `"messages"`) |

## Data model

One document per flow, keyed by `flow_uuid` (unique index); the flow state is stored in a `data` field, with `method_name` and `saved_at` alongside. Each save upserts, so `load_state` returns the latest.

## License

MIT
