import asyncio
import json
import sys
from typing import Any, Dict, List, Optional


class MCPClientAdapter:
    """
    A lightweight, production-grade Model Context Protocol (MCP) Client Adapter.
    Launches an MCP server subprocess and communicates via standard I/O (stdio) using JSON-RPC 2.0.
    """

    def __init__(self, command: str, args: Optional[List[str]] = None):
        self.command = command
        self.args = args or []
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Starts the MCP server subprocess and begins listening for responses."""
        print(f"🔌 Launching MCP Server: {self.command} {' '.join(self.args)}", file=sys.stderr)
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, # Suppress stderr to keep console clean
        )
        self._listener_task = asyncio.create_task(self._listen_stdout())

    async def _listen_stdout(self) -> None:
        """Asynchronously listens to the server's stdout and resolves pending JSON-RPC requests."""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break

                response = json.loads(line.decode("utf-8").strip())
                if "id" in response:
                    req_id = response["id"]
                    future = self._pending_requests.pop(req_id, None)
                    if future and not future.done():
                        if "error" in response:
                            future.set_exception(ValueError(response["error"]))
                        else:
                            future.set_result(response.get("result"))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Error in MCP client listener: {e}", file=sys.stderr)

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Sends a JSON-RPC request to the MCP server and awaits the result."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP Server process is not running.")

        self._request_id += 1
        req_id = self._request_id
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future

        request_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

        raw_payload = json.dumps(request_payload) + "\n"
        self.process.stdin.write(raw_payload.encode("utf-8"))
        await self.process.stdin.drain()

        return await future

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the server for its list of available tools."""
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Invokes an MCP tool on the server.
        Returns:
            A list of dictionary objects representing the returned records/entities.
        """
        result = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        
        # Standard MCP content block processing
        content_list = result.get("content", [])
        records = []
        for content in content_list:
            if content.get("type") == "text":
                try:
                    # Parse the text response which typically carries JSON records
                    data = json.loads(content["text"])
                    if isinstance(data, list):
                        records.extend(data)
                    else:
                        records.append(data)
                except json.JSONDecodeError:
                    pass
        return records

    async def read_resource(self, uri: str) -> str:
        """Reads a dynamic resource from the server (e.g. schema://Customer)."""
        result = await self._send_request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        if contents:
            return contents[0].get("text", "")
        return ""

    async def stop(self) -> None:
        """Stops the MCP server and clean up resources."""
        if self._listener_task:
            self._listener_task.cancel()
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                pass
            self.process = None
        print("🔌 MCP Server stopped.", file=sys.stderr)
