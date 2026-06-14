from src.mcps import EntityBase, ToolBase
from src.mcps import get_valid_entities

def import_tools()->dict[str,dict]:
    tools:dict[str,dict] = {}
    try:
        from src.mcps import opportunity_tools
        tools["Opportunity"] = opportunity_tools
    except Exception as e:
        print(e)

    try:
        from src.mcps import employee_tools
        tools["Employee"] = employee_tools
    except Exception as e:
        print(e)

    try:
        from src.mcps import customer_tools
        tools["Customer"] = customer_tools
    except Exception as e:
        print(e)
    
    return tools