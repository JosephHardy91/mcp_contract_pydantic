from src.mcps.cross_mcp_registry import get_valid_entities

valid_entities_dict = get_valid_entities(["Opportunity","Customer","Employee"])
valid_entities = valid_entities_dict.items()
if "Opportunity" not in valid_entities_dict:
    raise ValueError("Missing required entity: Opportunity is not registered for opportuity_mcp")
Opportunity = valid_entities_dict["Opportunity"]

Customer = valid_entities_dict["Customer"] if "Customer" in valid_entities_dict else None
Employee = valid_entities_dict["Employee"] if "Employee" in valid_entities_dict else None

VALID_SEARCH_ENTITIES = Opportunity | Customer | Employee