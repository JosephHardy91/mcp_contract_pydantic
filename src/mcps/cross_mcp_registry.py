from pydantic import PositiveFloat, BaseModel, model_validator
from .mcp_template import EntityBase

_VALID_ENTITIES: dict[str,type[EntityBase]] = {}
def register_entity(entity_name:str,entity:type[EntityBase]):
    _VALID_ENTITIES[entity_name]=entity

def get_valid_entities(entity_names:list[str])->dict[str,type[EntityBase]]:
    return {entity_name:_VALID_ENTITIES[entity_name] for entity_name in entity_names if entity_name in _VALID_ENTITIES}

class Opportunity(EntityBase):
    id: str
    opportunity_name: str
    owner_id: str
    customer_id: str
    amount: PositiveFloat

register_entity("Opportunity",Opportunity)

class Customer(EntityBase):
    id: str
    customer_name: str
    market: str

register_entity("Customer",Customer)

class Employee(EntityBase):
    id: str
    employee_name: str
    department: str

register_entity("Employee",Employee)

class CrossMCPDeclaration(BaseModel):
    mcps:list[str]
    entities: list[str]
    mcp_keys:list[str]
    mcp_key_types:type

    @model_validator(mode='after')
    def check_lengths_match(self) -> 'CrossMCPDeclaration':
        # 'self' is the fully populated model instance
        mcp_len, keys_len, entities_len = len(self.mcps), len(self.mcp_keys), len(self.entities)
        if mcp_len != keys_len or keys_len != entities_len:
            raise ValueError(
                f"Length mismatch: 'mcps' has {mcp_len} items, "
                f"'mcp_keys' has {keys_len} items, and "
                f"'entities' has {entities_len} items."
            )
        return self
    
    @model_validator(mode='after')
    def check_keys_exist_and_are_same_type(self) -> 'CrossMCPDeclaration':
        # Fetch the classes based on the 'entities' list, not the 'mcps' list
        valid_entity_classes = get_valid_entities(self.entities)

        # Zip all three arrays together to keep the relationships aligned
        for mcp, entity_name, mcp_key in zip(self.mcps, self.entities, self.mcp_keys):
            
            # 1. Existence check (Did the registry find this entity?)
            if entity_name not in valid_entity_classes:
                raise ValueError(f"Entity '{entity_name}' does not exist in the registry.")
            
            entity_class = valid_entity_classes[entity_name]
            
            # 2. Field check (Does the field exist on the Pydantic model?)
            if mcp_key not in entity_class.model_fields:
                raise ValueError(f"Field '{mcp_key}' does not exist in entity '{entity_name}'.")

            # 3. Type check (Enforce the mcp_key_types constraint)
            actual_type = entity_class.model_fields[mcp_key].annotation
            if actual_type != self.mcp_key_types:
                raise ValueError(
                    f"Type mismatch: '{entity_name}.{mcp_key}' is {actual_type}, "
                    f"expected {self.mcp_key_types}."
                )

        return self

# The Fixed Handshakes
handshakes = [
    CrossMCPDeclaration(
        mcps=["CustomerMCP", "OpportunityMCP"], 
        entities=["Customer", "Opportunity"], 
        mcp_keys=["id", "customer_id"], 
        mcp_key_types=str
    ),
    CrossMCPDeclaration(
        mcps=["EmployeeMCP", "OpportunityMCP"], 
        entities=["Employee", "Opportunity"], # Fixed this line!
        mcp_keys=["id", "owner_id"], 
        mcp_key_types=str
    )
]

def compile_entity_mappings(
    target_entity_name: str, 
    declarations: list[CrossMCPDeclaration]
) -> dict[str, dict[str, str]]:
    """
    Translates CrossMCPDeclarations into the nested mapping dictionary 
    required by the RecordSearchTool.
    """
    # Every tool natively knows how to search for its own primary entity
    mappings: dict[str, dict[str, str]] = {
        target_entity_name: {"id": "id"}
    }
    
    for dec in declarations:
        # Only process declarations that involve this specific MCP's data
        if target_entity_name in dec.entities:
            # 1. Find what the target database calls this field
            target_idx = dec.entities.index(target_entity_name)
            target_param = dec.mcp_keys[target_idx]
            
            # 2. Map every OTHER entity in the declaration to this target parameter
            for i, source_mcp in enumerate(dec.entities):
                if i != target_idx:
                    source_attr = dec.mcp_keys[i]
                    
                    if source_mcp not in mappings:
                        mappings[source_mcp] = {}
                        
                    # Example result: mappings["Customer"]["id"] = "customer_id"
                    mappings[source_mcp][source_attr] = target_param
                    
    return mappings