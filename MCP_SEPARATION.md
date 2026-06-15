# Decoupling MCP Contracts from Client Orchestration

This document defines the separation of concerns between contract schemas and execution logic, showing how we keep the tick-tock loop and handshake routing compatible with standard MCP without bloating the contract.

---

## 1. The Separation of Concerns

To maintain a clean architecture, the contract and execution loops are decoupled:

```
+-------------------------------------------------------------+
|                     src/mcps/mcp_contract.py                |
|  - Data Schemas (Pydantic)                                   |
|  - Resource URIs & Tool Payload Definitions                 |
+-------------------------------------------------------------+
                              |
                              v (Conformed to by)
+-------------------------------------------------------------+
|                 src/agent/mcp_client_adapter.py             |
|  - Connects to MCP servers (JSON-RPC)                       |
|  - Resolves handshakes & maps keys dynamically              |
+-------------------------------------------------------------+
                              |
                              v (Drives)
+-------------------------------------------------------------+
|                      src/agent/run.py                       |
|  - Tick-Tock Exploration Loop                               |
|  - Orchestration & Agent State                              |
+-------------------------------------------------------------+
```

### A. The Contract File (`mcp_contract.py`)
* **Role**: **Pure Declarations**.
* **Content**: Pydantic models describing tool signatures (`SearchToolContract`, `BootstrapToolContract`), resource routing (`EntityResourceMetadata`), and metadata schemas.
* **Why**: It must contain **no operational logic**. This allows the contract to be shared easily between the client and different server repositories as a dependency without carrying runtime side-effects.

### B. The Client Core Code (`run.py` / `mcp_client_adapter.py`)
* **Role**: **Operational Execution**.
* **Content**: The client adapter connects to real MCP servers, runs the tick-tock exploration loop, reads resource/tool endpoints, and handles client-side key translation.
* **Why**: This logic changes based on the LLM client, runtime environment, and application needs, so it belongs in the client application codebase rather than the contract.

---

## 2. Implementing Compatibility with Real MCP

To make the codebase compatible with real MCP servers, we write an adapter class in the client agent code:

```python
class MCPClientAdapter:
    def __init__(self, server_command: str):
        self.server_command = server_command
        self.connection = None

    async def connect(self):
        # Establish a standard stdio JSON-RPC channel with the MCP Server
        pass

    async def call_bootstrap(self, entity_name: str, params: dict) -> list[dict]:
        # Invoke tools/call for 'bootstrap_<entity_name>'
        pass

    async def call_search(self, entity_name: str, params: dict) -> list[dict]:
        # Invoke tools/call for 'search_<entity_name>'
        pass
```

The orchestration loop in [src/agent/run.py](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/agent/run.py) then calls this adapter instead of invoking `.search()` on local Python tool instances.
