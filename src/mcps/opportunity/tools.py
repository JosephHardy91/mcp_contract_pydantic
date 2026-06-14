from src.mcps.cross_mcp_registry import compile_entity_mappings, handshakes
from .data import fake_opportunities
from src.mcps.mcp_template import RecordSearchTool, BootstrapperTool
from .entities import Opportunity

class OpportunitySearchTool(RecordSearchTool[Opportunity]):
    accepted_entities: list[str] = ["Customer", "Employee", "Opportunity"]
    entity_field_mappings = compile_entity_mappings("Opportunity",handshakes)
    data_source = fake_opportunities

class OpportunityBootstrapTool(BootstrapperTool[Opportunity]):
    data_source = fake_opportunities


opportunity_tools = {"Search":OpportunitySearchTool(), "Bootstrap":OpportunityBootstrapTool()}