from pydantic import BaseModel, Field
from typing import Any
from pydantic_ai import Agent
from .entities import valid_entities_dict
from .mcp_interaction import EntityBase
from pydantic import BaseModel, Field, create_model
from typing import Any, Optional
from dotenv import load_dotenv
load_dotenv()
# 1. The Base Class (Contains the utility logic, but no fields)
class BaseSemanticEntity(BaseModel):
    def to_bootstrapper_dict(self) -> dict[str, Any]:
        """Strips out empty values and metadata before passing to the Bootstrapper."""
        data = self.model_dump(exclude={"domain"})
        return {k: v for k, v in data.items() if v is not None}

# 2. The Metaprogramming Factory
def build_extraction_schema(registry: dict[str, type[EntityBase]]) -> type[BaseSemanticEntity]:
    """Dynamically reads your database schemas to build an LLM extraction model."""
    extracted_fields = {}
    
    # Iterate through Customer, Employee, Opportunity, etc.
    for domain, EntityClass in registry.items():
        # Read the actual fields from the Pydantic model
        for field_name, field_info in EntityClass.model_fields.items():
            
            # Skip system fields the LLM should never try to extract from a user prompt
            if field_name in ["id", "created_at", "updated_at"]:
                continue
                
            # Extract the actual Python type (e.g., str, float)
            field_type = field_info.annotation
            
            # Give the LLM a description if one exists on the base model, otherwise default
            field_desc = field_info.description or f"Applies to {domain}"
            
            # Add it to our dynamic dictionary, forcing it to be Optional
            extracted_fields[field_name] = (
                Optional[field_type], 
                Field(default=None, description=field_desc)
            )

    # Inject the Domain router field dynamically based on your loaded domains
    domain_desc = f"The domain of the entity. Must be one of: {', '.join(registry.keys())} or Unknown."
    extracted_fields["domain"] = (str, Field(default="Unknown", description=domain_desc))

    # 3. Compile the new Pydantic class in memory!
    return create_model(
        'DynamicSemanticEntity',
        __base__=BaseSemanticEntity,
        **extracted_fields
    )

# Build the unified semantic entity class at runtime
DynamicSemanticEntity = build_extraction_schema(valid_entities_dict)

# Build the overall Prompt wrapper
class PromptExtraction(BaseModel):
    # We use the dynamically generated class here!
    entities: list[DynamicSemanticEntity] # type: ignore
    
    global_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Extract temporal, geographic, or qualitative boundaries."
    )

EXTRACTION_PROMPT = (
        "You are the Extraction Phase of a data pipeline. "
        "Review the user's prompt and the current pipeline inventory. "
        "Extract ANY fuzzy metadata, names, or constraints that have NOT been resolved yet. "
        "If the inventory already contains the entity the user is asking for, do not extract it again."
    )

extraction_agent = Agent(
    'google:gemini-3-flash-preview',
    output_type=PromptExtraction,
    system_prompt=EXTRACTION_PROMPT
)