from src.mcps.cross_mcp_registry import compile_entity_mappings,handshakes
from .data import fake_customers
from src.mcps.mcp_template import RecordSearchTool, BootstrapperTool
from .entities import Customer

class CustomerSearchTool(RecordSearchTool[Customer]):
    accepted_entities: list[str] = ["Customer", "Opportunity"]
    entity_field_mappings = compile_entity_mappings("Customer",handshakes)
    data_source = fake_customers

class CustomerBootstrapTool(BootstrapperTool[Customer]):
    data_source = fake_customers



customer_tools = {"Search":CustomerSearchTool(), "Bootstrap":CustomerBootstrapTool()}