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

## Long-term memory via `on_prune` (agentstate-reducer >= 0.4.0)

Messages pruned from the flow state are exactly the ones leaving the model's view. The persistence layer forwards a **memory namespace** to the reducer, and any `on_prune` hook receives `(pruned_messages, namespace)` — so pruned turns can flow straight into CrewAI's unified `Memory` (or any store), with no package coupling:

```python
from agentstate_reducer import MessageReducer, ReducerConfig, Background
from crewai.memory import Memory

memory = Memory(storage=...)                       # e.g. crewai-memory-dynamodb

def remember(pruned, namespace):
    text = "\n".join(m["content"] for m in pruned)
    memory.remember_many(memory.extract_memories(text), scope=namespace)   # LLM calls -> run off-path

reducer = MessageReducer(config=ReducerConfig(max_messages=20, on_prune=[Background(remember)]))

class SupportState(BaseModel):
    id: str = ""
    memory_namespace: str = "/user/kamal"          # long-term scope: the USER, not the flow
    messages: list = []

@persist(MongoDBFlowPersistence(..., reducer=reducer))
class SupportFlow(Flow[SupportState]):
    ...
```

The persistence layer reads `memory_namespace` (or whatever `ReducerConfig.namespace_key` names) from the flow state on every `save_state` and passes it through untouched. If the state never sets it, the namespace falls back to `"/flow/<flow_uuid>"`. Each pruned message reaches the hooks once.
