from .entity_extraction_agent import extraction_agent, PromptExtraction
from .exploration_agent import make_agent as make_explorer_agent
from .entities import hydrate_entity, VALID_SEARCH_ENTITIES
from pydantic_ai import Tool, RunContext
from typing import Any
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart



# async def constrained_exploration_loop(user_prompt: str):
#     current_inventory = []
#     message_history: list[ModelMessage] = []
#     backend_matrix = tools

#     extraction_result = await extraction_agent.run(user_prompt)
#     extracted_data = extraction_result.output
    
#     # 2. Bootstrap the concrete IDs
#     current_inventory = bootstrap_inventory(extracted_data)
    
#     # 3. Inject the abstract concepts (like "year: 2016") into the global state
#     deps = GraphDependencies(
#         registry=import_tools(),
#         active_filters=extracted_data.global_context 
#     )
    
#     print(f"Starting exploration. Initial Inventory: {[type(e).__name__ for e in current_inventory]}")

#     # 2. The Orchestration Loop
#     for step in range(5): # Put a hard cap on hops to prevent infinite loops
        
#         # Determine what tools the agent is allowed to see right now
#         unlocked_backend_tools = get_unlocked_tools(current_inventory, backend_matrix)
        
#         # Translate them to Pydantic-AI tools (using the factory from the previous step)
#         active_pydantic_tools = build_agent_tools(unlocked_backend_tools)
        
#         print(f"\n--- Hop {step + 1} ---")
#         print(f"Unlocked Tools: {[t.name for t in active_pydantic_tools]}")

#         # Instantiate a fresh agent with ONLY the unlocked tools
#         step_agent = Agent(
#             'google:gemini-3-flash-preview',
#             deps_type=GraphDependencies,
#             tools=active_pydantic_tools,
#             system_prompt=(
#                 "You are traversing a data graph step-by-step. "
#                 "Review the data you have found. If you have enough information "
#                 "to answer the user's prompt, formulate your final answer. "
#                 "If not, use your available tools to search for more data."
#             )
#         )
        
#         # Execute the agent, passing the history forward
#         result = await step_agent.run(
#             user_prompt, 
#             deps=GraphDependencies(registry=backend_matrix, active_filters=extracted_data.global_context),
#             message_history=message_history
#         )
        
#         # Capture the history so the next instantiation remembers this step
#         message_history = result.new_messages()
        
#         # 3. Process the Result & Expand the Frontier
#         # If the agent didn't use a tool, it means it decided it was finished and gave a text response.
#         called_any_tools = any(
#             isinstance(part,ToolCallPart) 
#             for msg in result.new_messages() if isinstance(msg,ModelResponse) 
#             for part in msg.parts
#         )
#         if not called_any_tools:
#             print("\n✅ Agent reached a conclusion:")
#             print(result.output)
#             break
            
#         # If it DID use a tool, we need to parse the new entities out of the tool results
#         # and add them to our inventory for the next loop.
#         for msg in message_history:
#             if isinstance(msg, ModelRequest):
#                 for part in msg.parts:
#                     if isinstance(part,ToolReturnPart):
#                         if not isinstance(part.content,list):
#                             print(f"Skipping un-iterable tool return: {type:(part.content)}")
#                             continue
#                         # Assuming your tool returns a list of dictionaries that represent entities
#                         for raw_record in part.content:
#                             # You would run this through your Pydantic validators to hydrate them back into EntityBase objects
#                             new_entity = hydrate_entity(raw_record) 
                            
#                             if not any(getattr(e, "id", None) == getattr(new_entity, "id", None) for e in current_inventory):
#                                 current_inventory.append(new_entity)
#                                 print(f"🎉 Frontier Expanded! Acquired: {type(new_entity).__name__} ({getattr(new_entity, 'id', 'Unknown')})")

# We import the tools matrix you already built
from .mcp_interaction import import_tools, ToolBase, EntityBase
from .state import GraphDependencies
tools = import_tools()

def get_unlocked_tools(
    inventory: list[EntityBase], 
    backend_matrix: dict[str, dict[str, ToolBase]]
) -> dict[str, dict[str, ToolBase]]:
    """Filters the matrix to only return tools the agent has the keys for, preserving structure."""
    unlocked_matrix: dict[str, dict[str, ToolBase]] = {}
    
    # What entities do we currently possess? (e.g., {"Customer"})
    owned_entity_types = {type(entity).__name__ for entity in inventory}
    
    for domain, tools in backend_matrix.items():
        for tool_name, tool_instance in tools.items():

            is_boot = getattr(tool_instance, "is_bootstrapper", False)
            accepted = getattr(tool_instance, "accepted_entities", [])
            
            can_unlock = any(req in owned_entity_types for req in accepted)
            
            if not is_boot and can_unlock:
                # Rebuild the nested dictionary structure for the unlocked tool
                if domain not in unlocked_matrix:
                    unlocked_matrix[domain] = {}
                    
                unlocked_matrix[domain][tool_name] = tool_instance
                
    return unlocked_matrix

def make_tool_wrapper(backend_instance: ToolBase):
    """
    Wraps the tool execution to handle the conversion between 
    JSON (from LLM) and Pydantic Objects (for your tool logic).
    """
    def wrapper(ctx: RunContext[GraphDependencies]) -> list[dict[str, Any]]:
        print(f"TOOL INVOKED: {backend_instance.__class__.__name__}")
        accepted_entities = set(getattr(backend_instance, "accepted_entities", []))
        data_source = getattr(backend_instance, "data_source", [])
        target_entity_type = type(data_source[0]).__name__ if data_source else None

        hydrated_entities = [
            entity
            for entity in ctx.deps.current_inventory
            if type(entity).__name__ in accepted_entities and type(entity).__name__ != target_entity_type
        ]

        if not hydrated_entities:
            hydrated_entities = [
                entity
                for entity in ctx.deps.current_inventory
                if type(entity).__name__ in accepted_entities
            ]

        if not hydrated_entities:
            return []
        
        # 2. EXECUTION: Pass the real objects to your search method
        results = backend_instance.search(hydrated_entities)
        
        # 3. SERIALIZATION: Convert back to dicts for the LLM
        return [r.model_dump() for r in results] if results else []
    
    return wrapper

def build_agent_tools(backend_matrix: dict[str, dict[str, ToolBase]]) -> list[Tool]:
    """Flattens your nested dictionary into Pydantic-AI Tools."""
    agent_tools = []
    
    # Iterate over Domain -> Tool Name -> Tool Instance
    for domain, domain_tools in backend_matrix.items():
        for tool_name, instance in domain_tools.items():
            
            # 1. Create the isolated execution wrapper
            execution_func = make_tool_wrapper(instance)
            
            # 2. Format a safe name for the LLM (e.g., "Customer Record Search" -> "customer_record_search")
            safe_llm_name = f"{domain}_{tool_name}".replace(" ", "_").lower()
            
            # 3. Pull the description (fallback if you haven't added 'description' to ToolBase yet)
            desc = getattr(instance, "description", f"Executes the {tool_name} operation for {domain}.")
            desc = f"{desc} This tool automatically uses relevant verified entities from the current inventory."
            
            pydantic_tool = Tool(
                execution_func,
                name=safe_llm_name,
                description=desc
            )
            
            agent_tools.append(pydantic_tool)
            
    return agent_tools

def bootstrap_inventory(
    extraction: PromptExtraction, 
    backend_matrix: dict[str, dict[str, Any]] # Or dict[str, dict[str, ToolBase]]
) -> list[Any]: # Returns list[EntityBase]
    """
    Takes the fuzzy JSON from the Semantic Tick, finds the correct Bootstrapper tool 
    for each domain, and returns the strict, hydrated Pydantic models.
    """
    new_inventory = []
    
    for fuzzy_entity in extraction.entities:
        # We use getattr in case the dynamic schema generation behaved unexpectedly
        domain = getattr(fuzzy_entity, "domain", "Unknown")
        
        if domain == "Unknown":
            continue
            
        # The dynamic entity inherited this method from BaseSemanticEntity
        search_params = fuzzy_entity.to_bootstrapper_dict()
        
        # If the LLM guessed the domain but failed to extract any actual parameters, skip
        if not search_params:
            continue
            
        # Locate the specific Bootstrapper tool for this domain in the matrix
        domain_tools = backend_matrix.get(domain, {})
        bootstrapper = next(
            (tool for tool in domain_tools.values() if getattr(tool, "is_bootstrapper", False)), 
            None
        )
        
        if bootstrapper:
            print(f"🔍 [Bootstrap] Searching {domain} with {search_params}...")
            
            # Execute the fuzzy search (e.g., using your RapidFuzz/math.isclose logic)
            concrete_records = bootstrapper.search(search_params)
            
            if concrete_records:
                new_inventory.extend(concrete_records)
                print(f"   ✅ Hydrated {len(concrete_records)} {domain} records.")
            else:
                print(f"   ❌ No matches found in database.")
        else:
            print(f"⚠️ Warning: No bootstrapper configured for '{domain}'.")
            
    return new_inventory


def bootstrap_full_inventory(backend_matrix: dict[str, dict[str, Any]]) -> list[Any]:
    """Seeds exploration with full domain snapshots when no fuzzy entity was extracted."""
    seeded_inventory = []

    print("🔍 [Bootstrap] No seed entities extracted; hydrating full domain snapshots...")
    for domain, domain_tools in backend_matrix.items():
        bootstrapper = next(
            (tool for tool in domain_tools.values() if getattr(tool, "is_bootstrapper", False)),
            None,
        )

        if bootstrapper:
            concrete_records = list(getattr(bootstrapper, "data_source", []))
            if concrete_records:
                seeded_inventory.extend(concrete_records)
                print(f"   ✅ Seeded {len(concrete_records)} {domain} records.")

    return seeded_inventory

async def tick_tock_exploration_loop(user_prompt: str):
    inventory: list[EntityBase] = []
    chat_history: list[ModelMessage] = []
    global_filters:dict[str,Any] = {}
    backend_matrix = import_tools()
    
    print(f"🚀 Starting Tick-Tock Exploration for: '{user_prompt}'")

    for step in range(5):
        print(f"\n--- 🔄 LOOP STEP {step + 1} ---")

        # ==========================================
        # PHASE 1: EXTRACT (The Semantic Tick)
        # ==========================================
        # Tell the semantic agent what we already have so it only looks for NEW things
        inventory_summary = [
            f"{type(e).__name__}(id={getattr(e, 'id', 'Unknown')})" 
            for e in inventory
        ]

        
        extract_prompt = (
            f"USER PROMPT: {user_prompt}\n"
            f"CURRENT VERIFIED INVENTORY: {inventory_summary}\n"
            "Extract any pending fuzzy entities."
        )
        
        print("🧠 [Tick] Extracting fuzzy intent...")
        extraction_result = await extraction_agent.run(extract_prompt)
        global_filters.update(extraction_result.output.global_context)
        
        # Hydrate the fuzzy JSON into strict Pydantic models using your RapidFuzz bootstrappers
        new_records = bootstrap_inventory(extraction_result.output, backend_matrix)
        if not inventory and not new_records:
            new_records = bootstrap_full_inventory(backend_matrix)
        
        # Add newly discovered records to the inventory
        for record in new_records:
            if not any(getattr(e, "id", None) == getattr(record, "id", None) for e in inventory):
                inventory.append(record)
                print(f"   ✅ Added {type(record).__name__} to inventory.")

        print([
            f"{type(e).__name__}(id={getattr(e, 'id', 'Unknown')})" 
            for e in inventory
        ])

        # ==========================================
        # PHASE 2: EXPLORE (The Graph Tock)
        # ==========================================
        # Unlock strict tools based ONLY on the current inventory
        unlocked_backend = get_unlocked_tools(inventory, backend_matrix)
        active_tools = build_agent_tools(unlocked_backend) # No bootstrapper wrappers needed here anymore!
        
        # Package the state
        deps = GraphDependencies(registry=backend_matrix, current_inventory=inventory, active_filters=global_filters)
        
        print(f"🗺️ [Tock] Exploring graph with tools: {[t.name for t in active_tools]}...")
        
        # Run the Explorer Agent, passing the chat history forward so it remembers previous tocks
        explorer_agent = make_explorer_agent(active_tools)
        @explorer_agent.system_prompt
        def get_explorer_system_prompt(ctx: RunContext[GraphDependencies])->str:
            inv_str = "\n".join(
                f"- {e}"
                for e in ctx.deps.current_inventory
            )
            print(inv_str)
            return (
                "You are the Exploration Phase. You traverse a strict data graph.\n"
                f"YOUR CURRENT INVENTORY:\n{inv_str}\n\n"
                """Inventory entities are VERIFIED facts already discovered.

                A tool should only be called if it can produce a NEW entity type
                or NEW relationships not already present in the inventory.

                Before calling a tool, ask:
                1. What new information could this tool discover?
                2. Is that information already represented in inventory?

                If no new entities or relationships would be produced,
                do not call the tool."""
            )
        
        explore_result = await explorer_agent.run(
            user_prompt, 
            deps=deps,
            message_history=chat_history
        )

                
        # Update the chat history for the next loop
        chat_history.extend(explore_result.new_messages())
        
        # ==========================================
        # PHASE 3: EVALUATE 
        # ==========================================
        executed_tool_returns: list[ToolReturnPart] = [
            part
            for msg in explore_result.new_messages()
            if isinstance(msg, ModelRequest)
            for part in msg.parts
            if isinstance(part, ToolReturnPart)
        ]

        print(bool(executed_tool_returns))
        
        if not executed_tool_returns:
            print("\n🎉 AGENT REACHED A CONCLUSION:")
            print(explore_result.output)
            break
            
        # If tools WERE used, we update the inventory with the new graph relationships it found
        for part in executed_tool_returns:
            # part.content holds the list[dict] returned by our wrapper
            if isinstance(part.content, list):
                for raw_record in part.content:
                    new_entity = hydrate_entity(raw_record) 
                    if not any(getattr(e, "id", None) == getattr(new_entity, "id", None) for e in inventory):
                        inventory.append(new_entity)

