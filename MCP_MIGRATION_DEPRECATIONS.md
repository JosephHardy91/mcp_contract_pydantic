# MCP Migration & Deprecation Analysis

This document outlines how migrating to the official Model Context Protocol (MCP) standard impacts the existing code, specifying which functionalities are deprecated, relocated to the server, or retained.

---

## 1. Deprecated & Relocated Functionalities

These components move from the local client runtime to the server or are replaced entirely by standard protocol conventions.

### A. Local Tool Execution (`BootstrapperTool` and `RecordSearchTool`)
* **Current**: In [src/mcps/mcp_template.py](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/mcps/mcp_template.py), the `BootstrapperTool` and `RecordSearchTool` perform fuzzy matching and relational database filtering locally on the client.
* **Migration**: **Deprecated**. These execution routines (and the in-memory lists `fake_customers`, etc.) are relocated to the server side. The server implements search/bootstrap actions and exposes them via JSON-RPC.

### B. In-Process Tool Factory (`build_agent_tools` & `get_unlocked_tools`)
* **Current**: In [src/agent/run.py](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/agent/run.py), `build_agent_tools` flattens local class dictionaries, while `get_unlocked_tools` filters them based on active inventory.
* **Migration**: **Deprecated**. The client discovers available tools dynamically by querying the MCP connection's `tools/list` endpoint. Tool wrapping is handled generically by the MCP client wrapper.

### C. Static Entity Schema Declarations
* **Current**: Entity models (`Customer`, `Employee`, `Opportunity`) are hardcoded python models imported directly by the agent modules.
* **Migration**: **Deprecated** for client-side static compilation. The client dynamically fetches the JSON Schema from the MCP servers (`schema://<entity_name>`) and compiles the validator union at runtime.

---

## 2. Retained & Adapted Functionalities

These elements remain on the client side but are adapted to consume MCP messages instead of Python objects.

### A. Cross-MCP Handshake Compilation (`compile_entity_mappings`)
* **Current**: [compile_entity_mappings](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/mcps/cross_mcp_registry.py#L96) maps Pydantic classes into attribute links.
* **Migration**: **Retained and Adapted**. The client still needs relationship mapping, but it maps keys using JSON payloads returned by tools rather than Pydantic objects.

### B. The Orchestration Loop (`tick_tock_exploration_loop`)
* **Current**: [tick_tock_exploration_loop](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/agent/run.py#L256) coordinates Semantic Ticks, Graph Tocks, and Evaluations.
* **Migration**: **Retained**. The orchestrator remains the central client loop, but its tool calls are routed over standard JSON-RPC channels.

### C. Deterministic Analysis Engine
* **Current**: The plan for analysis transforms verified inventory.
* **Migration**: **Retained**. The deterministic analysis engine continues to run client-side over the resolved inventory, completely decoupled from data retrieval.
