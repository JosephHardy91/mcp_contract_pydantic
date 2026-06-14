from src.mcps.cross_mcp_registry import compile_entity_mappings, handshakes
from .data import fake_employees
from src.mcps.mcp_template import RecordSearchTool, BootstrapperTool
from .entities import Employee

class EmployeeSearchTool(RecordSearchTool[Employee]):
    accepted_entities: list[str] = ["Employee", "Opportunity"]
    entity_field_mappings = compile_entity_mappings("Employee",handshakes)
    data_source = fake_employees

class EmployeeBootstrapTool(BootstrapperTool[Employee]):
    data_source = fake_employees


employee_tools = {"Search":EmployeeSearchTool(), "Bootstrap":EmployeeBootstrapTool()}