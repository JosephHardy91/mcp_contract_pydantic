import asyncio
import sys
import unittest
from typing import Any, List

from src.agent.mcp_client_adapter import MCPClientAdapter


class TestMCPCapabilityMatrix(unittest.IsolatedAsyncioTestCase):
    """
    Matrix tests running standard JSON-RPC calls through the new 
    MCPClientAdapter and MCPServerHelper subprocess setup.
    """

    async def asyncSetUp(self) -> None:
        # Define inline command string to run the MCPServerHelper for each domain
        self.python_exe = sys.executable

        # Spawners for Customer, Employee, and Opportunity MCP Servers
        self.customer_cmd = [
            "-c",
            "from src.mcps import customer_tools, MCPServerHelper; "
            "from src.agent.entities import Customer; "
            "MCPServerHelper('Customer', customer_tools, Customer).start()",
        ]
        self.employee_cmd = [
            "-c",
            "from src.mcps import employee_tools, MCPServerHelper; "
            "from src.agent.entities import Employee; "
            "MCPServerHelper('Employee', employee_tools, Employee).start()",
        ]
        self.opportunity_cmd = [
            "-c",
            "from src.mcps import opportunity_tools, MCPServerHelper; "
            "from src.agent.entities import Opportunity; "
            "MCPServerHelper('Opportunity', opportunity_tools, Opportunity).start()",
        ]

        # Instantiated adapters
        self.customer_adapter = MCPClientAdapter(self.python_exe, self.customer_cmd)
        self.employee_adapter = MCPClientAdapter(self.python_exe, self.employee_cmd)
        self.opportunity_adapter = MCPClientAdapter(self.python_exe, self.opportunity_cmd)

        # Start all adapters
        await asyncio.gather(
            self.customer_adapter.start(),
            self.employee_adapter.start(),
            self.opportunity_adapter.start(),
        )

    async def asyncTearDown(self) -> None:
        # Stop all adapters
        await asyncio.gather(
            self.customer_adapter.stop(),
            self.employee_adapter.stop(),
            self.opportunity_adapter.stop(),
        )

    async def test_tools_listing(self) -> None:
        """Matrix Test: Verify that all servers list their tools correctly according to naming contracts."""
        customer_tools = await self.customer_adapter.list_tools()
        employee_tools = await self.employee_adapter.list_tools()
        opportunity_tools = await self.opportunity_adapter.list_tools()

        # Check tool names for Customer
        customer_names = [t["name"] for t in customer_tools]
        self.assertIn("bootstrap_customer", customer_names)
        self.assertIn("search_customer", customer_names)

        # Check tool names for Employee
        employee_names = [t["name"] for t in employee_tools]
        self.assertIn("bootstrap_employee", employee_names)
        self.assertIn("search_employee", employee_names)

        # Check tool names for Opportunity
        opportunity_names = [t["name"] for t in opportunity_tools]
        self.assertIn("bootstrap_opportunity", opportunity_names)
        self.assertIn("search_opportunity", opportunity_names)

    async def test_resource_reading(self) -> None:
        """Matrix Test: Verify schema resources are served properly over JSON-RPC."""
        schema_json = await self.customer_adapter.read_resource("schema://Customer")
        self.assertIsNotNone(schema_json)
        self.assertIn("Customer", schema_json)
        self.assertIn("customer_name", schema_json)

    async def test_bootstrapper_fuzzy_seeding(self) -> None:
        """Matrix Test: Verify fuzzy bootstrapper tool calls work over standard MCP."""
        # Seeding Customer "Acme"
        cust_records = await self.customer_adapter.call_tool(
            "bootstrap_customer", {"customer_name": "Acme"}
        )
        self.assertTrue(len(cust_records) > 0)
        self.assertEqual(cust_records[0]["customer_name"], "Acme Corp")
        self.assertEqual(cust_records[0]["id"], "cust_501")

        # Seeding Employee "Sarah"
        emp_records = await self.employee_adapter.call_tool(
            "bootstrap_employee", {"employee_name": "Sarah"}
        )
        self.assertTrue(len(emp_records) > 0)
        self.assertEqual(emp_records[0]["employee_name"], "Sarah Connor")

    async def test_relational_traversal(self) -> None:
        """Matrix Test: Verify client-side dynamic parameters traverse relations properly."""
        # Find opportunities for customer id 'cust_501' (Acme Corp)
        opp_records = await self.opportunity_adapter.call_tool(
            "search_opportunity", {"customer_id": ["cust_501"]}
        )
        self.assertTrue(len(opp_records) > 0)
        self.assertEqual(opp_records[0]["customer_id"], "cust_501")
        self.assertEqual(opp_records[0]["id"], "opp_001")


if __name__ == "__main__":
    unittest.main()
