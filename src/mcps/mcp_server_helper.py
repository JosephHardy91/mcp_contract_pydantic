import json
import sys
from typing import Any, Dict, List


class MCPServerHelper:
    """
    A lightweight, dependency-free helper to wrap simulated Python tools 
    and serve them as a standard stdio JSON-RPC MCP Server.
    """

    def __init__(self, domain_name: str, tools_dict: Dict[str, Any], entity_class: Any):
        self.domain_name = domain_name.lower()
        self.tools_dict = tools_dict
        self.entity_class = entity_class

    def _get_tools_metadata(self) -> List[Dict[str, Any]]:
        """Compiles metadata of available tools matching standard MCP list format."""
        tools = []
        for name, tool in self.tools_dict.items():
            if getattr(tool, "is_bootstrapper", False):
                tools.append({
                    "name": f"bootstrap_{self.domain_name}",
                    "description": f"Fuzzy matching bootstrapper to seed {self.domain_name} records.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            field: {"type": "string"} 
                            for field in self.entity_class.model_fields 
                            if field != "id"
                        }
                    }
                })
            else:
                tools.append({
                    "name": f"search_{self.domain_name}",
                    "description": f"Strict relational search tool for {self.domain_name} records.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "array", "items": {"type": "string"}},
                            "owner_id": {"type": "array", "items": {"type": "string"}},
                            "id": {"type": "array", "items": {"type": "string"}},
                        }
                    }
                })
        return tools

    def _handle_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Routes a tools/call request to the corresponding Python tool search execution."""
        # Route to bootstrap
        if tool_name == f"bootstrap_{self.domain_name}":
            bootstrap_tool = self.tools_dict.get("Bootstrap")
            if bootstrap_tool:
                results = bootstrap_tool.search(arguments)
                return [r.model_dump() for r in results] if results else []

        # Route to search
        elif tool_name == f"search_{self.domain_name}":
            search_tool = self.tools_dict.get("Search")
            if search_tool:
                # Reconstruct entities from input arguments to pass to local RecordSearchTool
                # The search tool expects EntityBase objects containing the search IDs
                mock_entities = []
                for field, val_list in arguments.items():
                    if isinstance(val_list, list):
                        for val in val_list:
                            # Create a mock entity dict with the corresponding attribute
                            mock_entity_dict = {"id": val}
                            if field == "customer_id":
                                mock_entity_dict = {"customer_id": val, "id": val}
                            elif field == "owner_id":
                                mock_entity_dict = {"owner_id": val, "id": val}
                            
                            # Hydrate to a Pydantic object
                            from src.agent.entities import hydrate_entity
                            try:
                                mock_entities.append(hydrate_entity(mock_entity_dict))
                            except ValueError:
                                pass
                
                if mock_entities:
                    results = search_tool.search(mock_entities)
                    return [r.model_dump() for r in results] if results else []
        return []

    def start(self):
        """Starts the main stdio loop reading JSON-RPC lines from stdin and outputting responses."""
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                response: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}

                if method == "tools/list":
                    response["result"] = {"tools": self._get_tools_metadata()}

                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    records = self._handle_call_tool(tool_name, arguments)
                    response["result"] = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(records)
                            }
                        ]
                    }

                elif method == "resources/read":
                    uri = params.get("uri", "")
                    if uri == f"schema://{self.domain_name.capitalize()}":
                        response["result"] = {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/schema+json",
                                    "text": json.dumps(self.entity_class.model_json_schema())
                                }
                            ]
                        }
                    else:
                        response["error"] = {"code": -32602, "message": "Resource not found"}

                else:
                    response["error"] = {"code": -32601, "message": f"Method {method} not found"}

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                # Handle error parsing or execution failure safely
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
