# Analysis Spec

## Goal

Add a deterministic analysis layer that can answer analytical questions from verified records without relying on the LLM for arithmetic, ranking, or winner selection.

The current agent loop already does two useful things:

1. Extract fuzzy intent and seed entities.
2. Traverse the data graph and hydrate verified records into inventory.

This spec adds a third phase:

3. Run deterministic record transforms over the verified inventory and produce a structured, provable result.

## Design Principles

1. The LLM may help with extraction, routing, and wording, but not with numerical conclusions.
2. All analytical answers must be reproducible from inventory plus an explicit transform plan.
3. Every answer must carry evidence: source records, join path, aggregation formula, and intermediate result rows.
4. If required data is missing, the analysis layer should refuse to answer rather than guess.

## Scope

This layer is for questions such as:

1. Who is our top salesperson?
2. Which market has the most pipeline?
3. How many customers have no opportunities?
4. What is the average deal size by department?
5. Which rep has the largest pipeline?

This layer is not intended to replace graph traversal. It runs after inventory discovery.

## Existing Inputs

The analysis layer should consume:

1. The verified inventory assembled in [src/agent/run.py](/home/joe/programming/_AI/mcp_contract_pydantic/src/agent/run.py).
2. The entity schemas registered in [src/mcps/cross_mcp_registry.py](/home/joe/programming/_AI/mcp_contract_pydantic/src/mcps/cross_mcp_registry.py).
3. Cross-entity relationships encoded via field mappings and handshake declarations.

The inventory may contain a mix of:

1. `Customer`
2. `Employee`
3. `Opportunity`

All of these are already hydrated Pydantic entities.

## Core Analytical Model

Most analytical questions can be represented as:

1. Select a source dataset.
2. Traverse relationships with joins.
3. Filter rows.
4. Derive computed columns.
5. Group rows by dimension.
6. Aggregate measures.
7. Sort, rank, compare, or limit.
8. Return rows plus evidence.

## Required Feature Set

The minimum operator set should cover most business analytics scenarios.

### 1. Dataset

Choose a starting collection such as `Employee`, `Customer`, or `Opportunity`.

### 2. Join

Traverse relationships using explicit keys.

Examples:

1. `Employee.id -> Opportunity.owner_id`
2. `Customer.id -> Opportunity.customer_id`

### 3. Filter

Support a small set of deterministic predicates:

1. `eq`
2. `neq`
3. `in`
4. `contains`
5. `gt`
6. `gte`
7. `lt`
8. `lte`
9. `between`
10. `is_null`
11. `not_null`

### 4. Project

Select which fields should be retained in the working table.

### 5. Derive

Create computed columns such as:

1. `is_large_deal = amount > 50000`
2. `pipeline_band`
3. time buckets once date fields exist

### 6. Group By

Support grouping by one or more dimensions.

Examples:

1. employee
2. department
3. market
4. customer

### 7. Aggregate

The MVP aggregation set should be:

1. `count`
2. `sum`
3. `avg`
4. `min`
5. `max`
6. `distinct_count`

### 8. Sort

Sort by a field or aggregate result.

### 9. Limit

Return top `N` or bottom `N` rows.

### 10. Compare

Support head-to-head or period comparisons after aggregation.

### 11. Explain

Return evidence showing why the result is correct.

## Conceptual Types

There are two important field roles:

### Dimensions

Fields used for grouping or filtering.

Examples:

1. `employee_name`
2. `department`
3. `market`

### Measures

Fields used for aggregation.

Examples:

1. `Opportunity.amount`
2. `count(Opportunity.id)`
3. `distinct_count(Customer.id)`

Most analytical questions can be reduced to: measure by dimension, with filters, optionally ranked.

## Proposed Models

### AnalysisIntent

This is the LLM-facing semantic contract. It captures what kind of analysis is being requested.

```python
from typing import Any, Literal
from pydantic import BaseModel, Field


class FilterSpec(BaseModel):
    field: str
    op: Literal[
        "eq",
        "neq",
        "in",
        "contains",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "is_null",
        "not_null",
    ]
    value: Any | None = None


class AnalysisIntent(BaseModel):
    operation: Literal["lookup", "aggregate", "ranking", "comparison", "distribution"]
    metric_field: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    filters: list[FilterSpec] = Field(default_factory=list)
    limit: int | None = None
    notes: str | None = None
```

### AnalysisPlan

This is the deterministic execution contract produced from `AnalysisIntent`.

```python
from typing import Literal
from pydantic import BaseModel, Field


class JoinSpec(BaseModel):
    left_dataset: str
    right_dataset: str
    left_key: str
    right_key: str
    join_type: Literal["inner", "left", "anti"] = "inner"


class AggregateSpec(BaseModel):
    func: Literal["count", "sum", "avg", "min", "max", "distinct_count"]
    field: str
    alias: str


class SortSpec(BaseModel):
    field: str
    direction: Literal["asc", "desc"]


class AnalysisPlan(BaseModel):
    source_dataset: str
    joins: list[JoinSpec] = Field(default_factory=list)
    filters: list[FilterSpec] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    aggregates: list[AggregateSpec] = Field(default_factory=list)
    sort: list[SortSpec] = Field(default_factory=list)
    limit: int | None = None
```

### AnalysisResult

This is the answer contract emitted by the deterministic engine.

```python
from typing import Any
from pydantic import BaseModel, Field


class AnalysisEvidence(BaseModel):
    source_record_ids: dict[str, list[str]] = Field(default_factory=dict)
    joins_used: list[str] = Field(default_factory=list)
    filters_used: list[str] = Field(default_factory=list)
    aggregations_used: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    operation: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    evidence: AnalysisEvidence
    summary_text: str | None = None
```

## Execution Architecture

### Phase 1: Extraction

The extraction layer should identify not just entities, but analytical intent.

Examples:

1. `top salesperson` -> ranking
2. `largest market by pipeline` -> ranking
3. `average deal size by department` -> aggregate

### Phase 2: Discovery

The existing graph traversal loop builds a verified inventory of records relevant to the question.

### Phase 3: Deterministic Analysis

After discovery is complete, the system should:

1. Inspect the inventory.
2. Build an `AnalysisPlan`.
3. Execute it over verified records.
4. Return `AnalysisResult`.
5. Optionally allow the LLM to verbalize the result without changing its content.

## Worked Example: Top Salesperson

Question:

`who's our top salesperson`

Intent:

1. operation = `ranking`
2. metric = `Opportunity.amount`
3. dimension = `Employee`
4. filter = `Employee.department == "Sales"`
5. limit = `1`

Plan:

```python
AnalysisPlan(
    source_dataset="Employee",
    joins=[
        JoinSpec(
            left_dataset="Employee",
            right_dataset="Opportunity",
            left_key="id",
            right_key="owner_id",
            join_type="inner",
        )
    ],
    filters=[
        FilterSpec(field="department", op="eq", value="Sales")
    ],
    group_by=["id", "employee_name"],
    aggregates=[
        AggregateSpec(func="sum", field="amount", alias="total_pipeline")
    ],
    sort=[
        SortSpec(field="total_pipeline", direction="desc")
    ],
    limit=1,
)
```

Expected intermediate ranking table:

```python
[
    {
        "id": "usr_104",
        "employee_name": "Miles Dyson",
        "total_pipeline": 348500.0,
    },
    {
        "id": "usr_102",
        "employee_name": "Hank Scorpio",
        "total_pipeline": 120500.5,
    },
]
```

Expected result payload:

```python
AnalysisResult(
    operation="ranking",
    rows=[
        {
            "id": "usr_104",
            "employee_name": "Miles Dyson",
            "total_pipeline": 348500.0,
        }
    ],
    evidence=AnalysisEvidence(
        source_record_ids={
            "Employee": ["usr_104", "usr_102"],
            "Opportunity": ["opp_002", "opp_005", "opp_006", "opp_009"],
        },
        joins_used=["Employee.id -> Opportunity.owner_id"],
        filters_used=["Employee.department == 'Sales'"],
        aggregations_used=["sum(Opportunity.amount) by Employee.id"],
    ),
)
```

## Deterministic Guarantees

To make answers defensible, the engine must:

1. Use only verified inventory records.
2. Use explicit join keys.
3. Produce stable aggregate calculations.
4. Preserve source record IDs for every result row.
5. Refuse to answer if an analysis requires data that is not present.
6. Provide a sentence-based readout of what the query will do, in plain language so the LLM can validate its intent is being met by its spec.
7. Use a deterministic class populated from an accepted (and compatible - read, implements the necessary API to execute analysis specs) data source, so that the agent is not trying to do 8 calls to pull in 25 records per page for 200 records as a 'sample' - the llm should declare intent, double check what its spec will do then completely hand off execution to a deterministic service with an interface completed to handle the analysis spec and translate that to the data source's underlying data operation api.

## Failure Modes

The engine should explicitly detect and handle:

1. Missing required dataset in inventory.
2. Join path not available.
3. Metric field not present on the joined dataset.
4. Ambiguous mapping from natural language to analysis intent.
5. Empty result set after filters.

## Implementation Targets

Suggested new modules:

1. `/src/agent/analysis_models.py`
2. `/src/agent/analysis_engine.py`
3. `/src/agent/analysis_planner.py`

Suggested responsibility split:

1. `entity_extraction_agent.py`: extract `AnalysisIntent` plus unresolved entity hints.
2. `run.py`: orchestrate extract, discover, analyze, then render.
3. `analysis_planner.py`: map `AnalysisIntent` to `AnalysisPlan`.
4. `analysis_engine.py`: execute joins, filters, groupings, aggregates, sort, and limit.
5. optional final narrator: convert `AnalysisResult` into user-facing prose.

## MVP Recommendation

Implement the smallest vertical slice first.

### MVP Question Class

Ranking over joined entities using summed numeric measures.

This covers:

1. top salesperson
2. top customer by pipeline
3. biggest market by pipeline

### MVP Operators

1. `inner join`
2. `eq filter`
3. `group_by`
4. `sum`
5. `sort`
6. `limit`

### MVP Deliverable

Given verified `Employee` and `Opportunity` inventory, deterministically return the top salesperson plus supporting evidence rows.

## Non-Goals

The first version does not need:

1. full SQL support
2. arbitrary expression parsing
3. complex time intelligence
4. probabilistic answers
5. LLM-driven arithmetic

## Summary

The analysis layer should act like a small deterministic query engine over verified Pydantic entities. The LLM can translate natural language into analytical intent, but the system should compute the answer through explicit joins, filters, grouping, aggregation, sorting, and evidence capture.
