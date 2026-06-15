from pydantic import BaseModel, Field
from typing import Any, Literal

# =====================================================================
# 1. MCP RESOURCE CONTRACTS (URI SCHEMAS & ENTITY TYPE METADATA)
# =====================================================================

class EntityResourceMetadata(BaseModel):
    """
    Defines how a business entity maps to MCP Resources.
    In standard MCP, individual records are exposed via resource URIs.
    """
    entity_name: str = Field(
        ..., 
        description="The name of the entity, matching the Pydantic class (e.g., Customer)."
    )
    uri_prefix: str = Field(
        ..., 
        description="The URI prefix for resource routing (e.g., customer://)."
    )
    id_pattern: str = Field(
        ..., 
        description="Regex pattern representing valid IDs for this resource (e.g., ^cust_[a-zA-Z0-9_-]+$)."
    )
    schema_url: str = Field(
        ..., 
        description="The URI to fetch the JSON Schema for this entity (e.g., schema://Customer)."
    )


# =====================================================================
# 2. MCP TOOL CONTRACTS (STANDARDIZED API SIGNATURES)
# =====================================================================

class BootstrapToolContract(BaseModel):
    """
    Contract for the 'bootstrap_<entity>' MCP tool.
    Used during Phase 1 (Semantic Tick) for fuzzy name/field matching to seed inventory.
    """
    tool_name: str = Field(
        ..., 
        description="Standardized tool name. Format: 'bootstrap_<entity_name>' (e.g., bootstrap_customer)."
    )
    description: str = Field(
        ..., 
        description="Explanatory text for the LLM detailing what fields can be fuzzy-matched."
    )
    input_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema for inputs (maps to all fields on the entity as optional parameters)."
    )
    output_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema for outputs (returns list of matched hydrated entity objects)."
    )


class SearchToolContract(BaseModel):
    """
    Contract for the 'search_<entity>' MCP tool.
    Used during Phase 2 (Graph Tock) for strict traversal using primary/foreign key mappings.
    """
    tool_name: str = Field(
        ..., 
        description="Standardized tool name. Format: 'search_<entity_name>' (e.g., search_opportunity)."
    )
    description: str = Field(
        ..., 
        description="Explanatory text detailing what parent entities/IDs are accepted as input."
    )
    input_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema mapping supported foreign keys to lists of values (e.g. {customer_id: [cust_1, cust_2]})."
    )
    output_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema for outputs (returns matching hydrated records)."
    )


# =====================================================================
# 3. CROSS-MCP RELATIONSHIP CONTRACTS (HANDSHAKES)
# =====================================================================

class FieldMapping(BaseModel):
    """
    Maps a field from a source entity type to a parameter field on a target entity type.
    """
    source_entity: str = Field(..., description="The type of the source entity (e.g., Customer).")
    source_field: str = Field(..., description="The field name on the source entity (e.g., id).")
    target_param: str = Field(..., description="The field name on the target entity it maps to (e.g., customer_id).")


class CrossMCPHandshakeContract(BaseModel):
    """
    Contract describing linkages between two different MCP domains.
    Corresponds to the CrossMCPDeclaration in cross_mcp_registry.py.
    """
    handshake_id: str = Field(..., description="Unique ID for this handshake (e.g., Customer-Opportunity).")
    left_mcp: str = Field(..., description="The name of the first MCP server (e.g., CustomerMCP).")
    right_mcp: str = Field(..., description="The name of the second MCP server (e.g., OpportunityMCP).")
    left_entity: str = Field(..., description="The entity class on the left server (e.g., Customer).")
    right_entity: str = Field(..., description="The entity class on the right server (e.g., Opportunity).")
    left_key: str = Field(..., description="The join key on the left entity (e.g., id).")
    right_key: str = Field(..., description="The join key on the right entity (e.g., customer_id).")
    key_type: Literal["str", "int", "float"] = Field(..., description="The expected type of the join keys.")


# =====================================================================
# 4. DETERMINISTIC ANALYSIS CONTRACT
# =====================================================================

class AnalysisEngineContract(BaseModel):
    """
    Contract for invoking the deterministic analysis layer.
    Allows clients to send an AnalysisPlan over an MCP server to calculate verified results.
    """
    tool_name: str = Field("execute_analysis", description="The name of the analysis tool.")
    input_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema matching the Pydantic AnalysisPlan model (source_dataset, joins, filters, grouping, etc.)."
    )
    output_schema: dict[str, Any] = Field(
        ..., 
        description="JSON Schema matching the Pydantic AnalysisResult model (rows, evidence, summary_text)."
    )
