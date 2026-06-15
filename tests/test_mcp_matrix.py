import sys
import pytest
import pytest_asyncio
from src.agent.mcp_client_adapter import MCPClientAdapter

# Configure pytest-asyncio to treat async test functions as asyncio tests
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def customer_adapter():
    python_exe = sys.executable
    cmd = [
        "-c",
        "from src.mcps import customer_tools, MCPServerHelper; "
        "from src.agent.entities import Customer; "
        "MCPServerHelper('Customer', customer_tools, Customer).start()",
    ]
    adapter = MCPClientAdapter(python_exe, cmd)
    await adapter.start()
    yield adapter
    await adapter.stop()


@pytest_asyncio.fixture
async def employee_adapter():
    python_exe = sys.executable
    cmd = [
        "-c",
        "from src.mcps import employee_tools, MCPServerHelper; "
        "from src.agent.entities import Employee; "
        "MCPServerHelper('Employee', employee_tools, Employee).start()",
    ]
    adapter = MCPClientAdapter(python_exe, cmd)
    await adapter.start()
    yield adapter
    await adapter.stop()


@pytest_asyncio.fixture
async def opportunity_adapter():
    python_exe = sys.executable
    cmd = [
        "-c",
        "from src.mcps import opportunity_tools, MCPServerHelper; "
        "from src.agent.entities import Opportunity; "
        "MCPServerHelper('Opportunity', opportunity_tools, Opportunity).start()",
    ]
    adapter = MCPClientAdapter(python_exe, cmd)
    await adapter.start()
    yield adapter
    await adapter.stop()


async def test_tools_listing(customer_adapter, employee_adapter, opportunity_adapter) -> None:
    """Verify all servers list their tools correctly according to naming contracts."""
    customer_tools = await customer_adapter.list_tools()
    employee_tools = await employee_adapter.list_tools()
    opportunity_tools = await opportunity_adapter.list_tools()

    customer_names = [t["name"] for t in customer_tools]
    assert "bootstrap_customer" in customer_names
    assert "search_customer" in customer_names

    employee_names = [t["name"] for t in employee_tools]
    assert "bootstrap_employee" in employee_names
    assert "search_employee" in employee_names

    opportunity_names = [t["name"] for t in opportunity_tools]
    assert "bootstrap_opportunity" in opportunity_names
    assert "search_opportunity" in opportunity_names


async def test_resource_reading(customer_adapter) -> None:
    """Verify schema resources are served properly over JSON-RPC."""
    schema_json = await customer_adapter.read_resource("schema://Customer")
    assert schema_json is not None
    assert "Customer" in schema_json
    assert "customer_name" in schema_json


async def test_bootstrapper_fuzzy_seeding(customer_adapter, employee_adapter) -> None:
    """Verify fuzzy bootstrapper tool calls work over standard MCP."""
    cust_records = await customer_adapter.call_tool(
        "bootstrap_customer", {"customer_name": "Acme"}
    )
    assert len(cust_records) > 0
    assert cust_records[0]["customer_name"] == "Acme Corp"
    assert cust_records[0]["id"] == "cust_501"

    emp_records = await employee_adapter.call_tool(
        "bootstrap_employee", {"employee_name": "Sarah"}
    )
    assert len(emp_records) > 0
    assert emp_records[0]["employee_name"] == "Sarah Connor"


async def test_relational_traversal(opportunity_adapter) -> None:
    """Verify client-side dynamic parameters traverse relations properly."""
    opp_records = await opportunity_adapter.call_tool(
        "search_opportunity", {"customer_id": ["cust_501"]}
    )
    assert len(opp_records) > 0
    assert opp_records[0]["customer_id"] == "cust_501"
    assert opp_records[0]["id"] == "opp_001"
