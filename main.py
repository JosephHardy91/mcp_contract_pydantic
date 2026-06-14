tools:dict[str,dict] = {}
try:
    from src.mcps.opportunity import opportunity_tools, fake_opportunities
    tools["Opportunity"] = opportunity_tools
except Exception as e:
    print(e)
    opportunity_tools = []
    fake_opportunities = []

try:
    from src.mcps.employee import employee_tools, fake_employees
    tools["Employee"] = employee_tools
except Exception as e:
    print(e)
    employee_tools = []
    fake_employees = []

try:
    from src.mcps.customer import customer_tools, fake_customers
    tools["Customer"] = customer_tools
except Exception as e:
    print(e)
    customer_tools = []
    fake_customers = []

def run_matrix_tests():
    # Grab the first item from each dataset to act as our "extracted entities"
    test_subjects = {
        "Customer": fake_customers[0],       # Acme Corp (cust_501)
        "Opportunity": fake_opportunities[0],  # Acme Corp Q3 (opp_001, owned by usr_101)
        "Employee": fake_employees[0]        # Sarah Connor (usr_101)
    }

    print("==================================================")
    print("🚀 RUNNING CROSS-MCP CAPABILITY MATRIX")
    print("==================================================\n")

    for subject_name, subject_entity in test_subjects.items():
        print(f"--- EXTRACTED ENTITY: [{subject_name}] ID: {subject_entity.id} ---")
        
        for tool_domain, tool_dict in tools.items():
            for tool_name, tool_instance in tool_dict.items():
                try:
                    # Execute the search
                    results = tool_instance.search(subject_entity)
                    
                    # Format the output based on what came back
                    if not results:
                        status = "✅ NULL (Executed successfully, zero records found)"
                    else:
                        # Extract the IDs of the returned records for clean printing
                        found_ids = [getattr(r, 'id', 'UNKNOWN') for r in results]
                        status = f"✅ SUCCESS: Found {len(results)} {tool_name}(s) -> {found_ids}"
                        
                except ValueError as e:
                    # This catches the intentional routing failures (e.g., trying to pass Employee to CustomerTool)
                    status = f"🚫 BLOCKED: {e}"
                    
                print(f"  -> Testing {tool_domain} {tool_name} Tool: {status}")
                
            print("\n")



def main():
    run_matrix_tests()


if __name__ == "__main__":
    main()
