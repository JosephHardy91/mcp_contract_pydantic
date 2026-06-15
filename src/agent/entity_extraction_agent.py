from typing import Any, Optional, Union, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent

from .entities import valid_entities_dict
from .mcp_interaction import EntityBase

load_dotenv()


class BaseSemanticEntity(BaseModel):
    def to_bootstrapper_dict(self) -> dict[str, Any]:
        """Strips out empty values and metadata before passing to the Bootstrapper."""
        data = self.model_dump(exclude={"domain"})
        return {k: v for k, v in data.items() if v is not None}


def build_extraction_union(registry: dict[str, type[EntityBase]]) -> Any:
    """Dynamically builds a Union of isolated domain models for strict LLM routing."""
    dynamic_models: list[type[BaseSemanticEntity]] = []

    for domain, entity_class in registry.items():
        extracted_fields: dict[str, tuple[Any, Field]] = {}

        for field_name, field_info in entity_class.model_fields.items():
            if field_name in ["id", "created_at", "updated_at"]:
                continue

            field_type = field_info.annotation
            field_desc = field_info.description or f"Applies to {domain}"
            extracted_fields[field_name] = (
                Optional[field_type],
                Field(default=None, description=field_desc),
            )

        extracted_fields["domain"] = (
            Literal[domain],  # type: ignore[valid-type]
            Field(
                default=domain,
                description=f"Must be exactly '{domain}' for this entity type.",
            ),
        )

        model_name = f"{domain}SemanticEntity"
        dynamic_model = create_model(
            model_name,
            __base__=BaseSemanticEntity,
            **extracted_fields,
        )
        dynamic_models.append(dynamic_model)

    return Union[tuple(dynamic_models)]  # type: ignore[misc]


SemanticEntityUnion = build_extraction_union(valid_entities_dict)


class PromptExtraction(BaseModel):
    entities: list[SemanticEntityUnion]  # type: ignore[valid-type]
    global_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Extract temporal, geographic, or qualitative boundaries.",
    )


EXTRACTION_PROMPT = (
    "You are the Extraction Phase of a data pipeline. "
    "Review the user's prompt and the current pipeline inventory. "
    "Extract ANY fuzzy metadata, names, or constraints that have NOT been resolved yet. "
    "If the inventory already contains the entity the user is asking for, do not extract it again."
)


extraction_agent = Agent(
    "google:gemini-3-flash-preview",
    output_type=PromptExtraction,
    system_prompt=EXTRACTION_PROMPT,
)
