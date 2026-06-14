from .mcp_interaction import get_valid_entities
from typing import Union
from pydantic import ValidationError
valid_entities_dict = get_valid_entities(["Opportunity","Customer","Employee"])
Customer = valid_entities_dict["Customer"] if "Customer" in valid_entities_dict else None
Opportunity = valid_entities_dict["Opportunity"] if "Opportunity" in valid_entities_dict else None
Employee = valid_entities_dict["Employee"] if "Employee" in valid_entities_dict else None

VALID_SEARCH_ENTITIES = Union[Opportunity,Customer, Employee]

def hydrate_entity(raw_record: dict) -> VALID_SEARCH_ENTITIES: # type: ignore
    """
    Attempts to cast a raw dictionary into the correct Pydantic entity class 
    by testing it against the known schemas.
    """
    for entity_name, EntityClass in valid_entities_dict.items():
        try:
            # Try to build the Pydantic model. 
            # If the dict is a Customer, trying to build an Opportunity will throw a ValidationError 
            # because it's missing the 'amount' and 'opportunity_name' fields.
            return EntityClass(**raw_record)
        except ValidationError:
            # Schema didn't match, move on to test the next entity class
            continue
            
    # If we loop through all known entities and none fit, we have a rogue payload
    raise ValueError(f"Could not hydrate record into any known entity type: {raw_record}")