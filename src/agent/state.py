from dataclasses import dataclass, field
from src.mcps import ToolBase
from typing import Any


@dataclass
class GraphDependencies:
    registry: dict[str, dict[str,ToolBase]]
    active_filters: dict[str, Any] = field(default_factory=dict)
    current_inventory: list[Any] = field(default_factory=list)