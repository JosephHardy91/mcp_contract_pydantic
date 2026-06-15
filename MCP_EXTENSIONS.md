# Specifying Logic for MCP Handshakes & Dynamic Schemas

This document outlines where and how we must write custom extension logic to address handshakes and dynamic schema generation within the standard MCP architecture.

---

## 1. Handshake & Relationship Resolution

Since MCP servers cannot communicate directly or share relational definitions, relationship resolution must be implemented in two primary locations:

### A. The Client Orchestrator (Orchestration Loop)
We need logic in the exploration loop (e.g., in [src/agent/run.py](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/agent/run.py)) to perform relationship mapping:
* **Action**: When a new record is added to the verified inventory, the client checks the handshake registry to see if the record's entity type can unlock relationships.
* **Logic**:
  ```python
  def resolve_relational_parameters(
      inventory: list[EntityBase], 
      handshakes: list[CrossMCPHandshakeContract]
  ) -> dict[str, dict[str, list[Any]]]:
      """
      Maps owned entity attributes to parameters for target MCP server tools.
      Returns: { "OpportunityMCP": { "customer_id": ["cust_501"] } }
      """
      pending_calls = {}
      for entity in inventory:
          for handshake in handshakes:
              # Match incoming entity
              if type(entity).__name__ == handshake.left_entity:
                  val = getattr(entity, handshake.left_key, None)
                  if val is not None:
                      server = handshake.right_mcp
                      param = handshake.right_key
                      pending_calls.setdefault(server, {}).setdefault(param, []).append(val)
      return pending_calls
  ```

### B. A Central Metadata MCP Server (Registry Pattern)
To keep the architecture decentralized:
* **Action**: Create a new `RegistryMCP` server.
* **Logic**: This server exposes the handshakes list via an MCP resource:
  * **Resource URI**: `registry://handshakes`
  * **Implementation**: The server returns the JSON-serialized list of `CrossMCPHandshakeContract` declarations. The client fetches this resource once during initialization.

---

## 2. Dynamic Schema Generation

Since MCP tool definitions are static, dynamic schema generation must be handled through resource endpoints and client-side Pydantic model rebuilding.

### A. The MCP Server (Schema Resource Exposure)
Each individual MCP server must expose its entity's JSON Schema dynamically:
* **Location**: Server resource handler.
* **Logic**:
  ```python
  @server.list_resources()
  async def handle_list_resources():
      return [
          Resource(
              uri="schema://Customer",
              name="Customer Entity Schema",
              mimeType="application/schema+json"
          )
      ]

  @server.read_resource()
  async def handle_read_resource(uri: str):
      if uri == "schema://Customer":
          # Generates standard JSON Schema dynamically from the Pydantic class
          schema_dict = Customer.model_json_schema()
          return json.dumps(schema_dict)
  ```

### B. The Client / Agent (Dynamic Pydantic Model Creation)
To update the LLM's understanding when schemas change:
* **Location**: Inside the agent's extraction initialization (e.g. in [src/agent/entity_extraction_agent.py](file:///home/joe/programming/_AI/mcp_contract_pydantic/src/agent/entity_extraction_agent.py)).
* **Logic**: The client fetches the schema from `schema://Customer`, parses the JSON schema, and dynamically recreates the Pydantic class at startup using `pydantic.create_model()`. This ensures the extraction agent stays synchronized without hardcoded schemas.
