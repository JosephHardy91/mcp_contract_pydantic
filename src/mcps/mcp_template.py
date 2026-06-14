from pydantic import BaseModel, model_validator
from typing import Any, Generic, TypeVar
from rapidfuzz import fuzz
import math

class EntityBase(BaseModel):
    ...

T_Input = TypeVar('T_Input')
T_Output = TypeVar('T_Output',bound=EntityBase)

class ToolBase(Generic[T_Input, T_Output]):
    accepted_entities: list[str]
    is_bootstrapper: bool = False
    def collect_valid_params(self, source_entities: T_Input) -> dict[str, list[Any]]:
        ...

    def search(self,source_entities: T_Input)->list[T_Output] | None:
        ...

class BootstrapperTool(ToolBase[dict[str,Any],T_Output]):
    is_bootstrapper = True
    data_source: list[T_Output]

    STRING_THRESHOLD = 75.0 
    
    # How far off a number can be. 0.10 means a 10% tolerance (e.g., 90 to 110 matches 100).
    NUMERIC_TOLERANCE = 0.10 
    
    def search(self, source_entities: dict[str, Any]) -> list[T_Output] | None:
        if not source_entities:
            return []
            
        results = []
        
        for record in self.data_source:
            is_match = True
            
            for key, expected_val in source_entities.items():
                record_val = getattr(record, key, None)
                
                # If the record lacks the field, drop it
                if record_val is None:
                    is_match = False
                    break
                    
                # 1. Fuzzy String Match
                if isinstance(expected_val, str) and isinstance(record_val, str):
                    # partial_ratio is perfect here because it matches substrings 
                    # (e.g., "Acme" matches "Acme Corporation" with a score of 100)
                    score = fuzz.partial_ratio(expected_val.lower(), record_val.lower())
                    
                    if score < self.STRING_THRESHOLD:
                        is_match = False
                        break
                        
                # 2. Fuzzy Numeric Match
                elif isinstance(expected_val, (int, float)) and isinstance(record_val, (int, float)):
                    # rel_tol dynamically calculates the acceptable range based on the expected value's size
                    if not math.isclose(expected_val, record_val, rel_tol=self.NUMERIC_TOLERANCE):
                        is_match = False
                        break
                        
                # 3. Strict Fallback (Booleans, Lists, etc.)
                else:
                    if expected_val != record_val:
                        is_match = False
                        break
                        
            if is_match:
                results.append(record)
                
        return results

class RecordSearchTool(ToolBase[EntityBase | list[EntityBase], T_Output]):
    accepted_entities: list[str] = ["Customer", "Employee", "Opportunity"]
    entity_field_mappings:dict[str,dict[str,str]]
    data_source: list[T_Output]

    def collect_valid_params(self, source_entities: EntityBase | list[EntityBase]) -> dict[str, list[Any]]:
        # 1. Normalize input so we are always working with a list
        if not isinstance(source_entities, list):
            source_entities = [source_entities]

        combined_params: dict[str, list[Any]] = {}

        # 2. Extract and group parameters
        for entity in source_entities:
            entity_type = type(entity).__name__
            if entity_type not in self.entity_field_mappings:
                raise ValueError(f"Tool cannot process entity type: {entity_type}")
            
            # Grab the mapping dictionary for this specific entity
            mapping = self.entity_field_mappings[entity_type]
            print(f"DEBUG: Mapping for {entity_type}: {mapping}")

            # Iterate through the mapping and extract the values
            for entity_attr, query_param in mapping.items():
                # Extract the value from the entity (e.g., entity.id)
                val = getattr(entity, entity_attr, None)

                # 2. Print exactly what we are checking
                print(f"DEBUG: Checking attribute '{entity_attr}' on {entity_type} -> Found: '{val}'")
                
                # If a value exists, append it to the query parameters
                if val is not None:
                    if query_param not in combined_params:
                        combined_params[query_param] = []
                    combined_params[query_param].append(val)
        return combined_params
        
    def search(self,source_entities: EntityBase | list[EntityBase])->list[T_Output] | None:
        if source_entities is None:
            raise ValueError("Execution failed: 'source_entity' is required but was None")
        if not isinstance(source_entities,list):
            source_entities = [source_entities]
        # --- DEBUG ---
        print(f"DEBUG: Search received {len(source_entities)} entities.")
        for i, e in enumerate(source_entities):
            print(f"DEBUG: Entity {i} type: {type(e)}")
            print(f"DEBUG: Entity {i} attributes: {getattr(e, '__dict__', 'NO DICT')}")
        # -------------
        query_params:dict[str,list[Any]] = self.collect_valid_params(source_entities)
        if not query_params:
            raise ValueError(f"Execution failed: Could not extract any valid search parameters from the provided entities.")
        and_results = list(filter(lambda opp:all(getattr(opp,k,None) in valid_values for k,valid_values in query_params.items()),self.data_source))
        if and_results:
            return and_results
        if len(query_params)>1:
            or_results = list(filter(lambda opp:any(getattr(opp,k,None) in valid_values for k,valid_values in query_params.items()),self.data_source))
            return or_results
        return []

