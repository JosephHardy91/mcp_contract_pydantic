from src.mcps.cross_mcp_registry import get_valid_entities

valid_entities_dict = get_valid_entities(["Opportunity","Customer","Employee"])
valid_entities = valid_entities_dict.items()
if "Employee" not in valid_entities_dict:
    raise ValueError("Missing required entity: Opportunity is not registered for opportuity_mcp")
Employee = valid_entities_dict["Employee"]

Customer = valid_entities_dict["Customer"] if "Customer" in valid_entities_dict else None
Opportunity = valid_entities_dict["Opportunity"] if "Opportunity" in valid_entities_dict else None

VALID_SEARCH_ENTITIES = Opportunity | Customer | Employee