# Architectural Weaknesses & MCP Spec Limitations

This document analyzes the weaknesses of the proposed MCP contract, focusing on dependencies on the agent/client and compatibility with the official Model Context Protocol (MCP) specification.

---

## 1. Core Agent & Client Dependencies

The proposed approach is not fully decentralized or self-governing; it places a heavy cognitive and operational load on the agent/client orchestrator.

### A. Dependency on Agent for Semantic Mapping (Semantic Tick)
* **Weakness**: Seeding the discovery loop relies entirely on the agent's LLM to extract natural language concepts into exact schema fields (e.g., extracting "Acme" to `Customer.customer_name`). 
* **Impact**: If the LLM misidentifies fields or extracts them under incorrect domains, the fuzzy bootstrapper tool receives garbage parameters and fails to locate the seed entity, stalling the entire loop.

### B. Dependency on Client for Relationship Joins (Handshakes)
* **Weakness**: MCP servers are completely isolated and stateless. The logic to join a `Customer` to an `Opportunity` (mapping `Customer.id` to `customer_id`) is defined in the client-side `CrossMCPHandshakeContract` registry.
* **Impact**: The servers themselves do not know how they relate to other servers. If the client's handshake mapping is misconfigured or if the agent fails to perform the cross-reference mapping, graph traversal breaks.

### C. Dependency on Client for Tool State Management (Dynamic Unlocking)
* **Weakness**: The permission gating ("tool unlocking") is managed entirely on the client side. The agent decides what tools are available based on the contents of the `current_inventory`.
* **Impact**: The servers do not enforce dependencies. Any client could theoretically query `search_opportunity` with random IDs without having a verified `Customer` in inventory. Security and graph integrity rely completely on client compliance.

---

## 2. Limitations Relative to the Official MCP Spec

Several features of our contract are not native to the standard Model Context Protocol (MCP) and require custom meta-protocol logic built on top of the client.

### A. Lack of Cross-Server Relationship Declarations
* **MCP Limitation**: The official MCP specification provides no mechanism for servers to declare linkages, foreign keys, or joins with other servers.
* **Our Workaround**: We must define custom metadata resource URIs (e.g., `schema://handshakes`) or maintain a local client-side configuration registry. This is an ad-hoc wrapper on top of standard MCP.

### B. Analytical Query Processing (Joins, Aggregates, and Filters)
* **MCP Limitation**: MCP is designed for data-retrieval (Resources) and discrete actions (Tools). It does not specify or support relational database operations (e.g., inner joins, grouping, aggregations) across multiple data sources.
* **Our Workaround**: Phase 3 (Deterministic Analysis) must run entirely on the client-side, consuming raw records returned by MCP servers and running a custom local query engine. MCP does not provide query execution primitives.

### C. Dynamic Schema Validation
* **MCP Limitation**: MCP tool definitions have static JSON schemas declared at connection handshake time. A server cannot dynamically alter its tool schema or parameter requirements based on the agent's current state or inventory.
* **Our Workaround**: Tool schemas must remain generic (e.g., accepting lists of IDs), and the client must handle type validation and routing dynamically.
