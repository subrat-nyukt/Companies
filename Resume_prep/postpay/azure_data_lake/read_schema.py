import pandas as pd

try:
    # Attempt to read the excel file
    x = pd.read_excel('API_PROD_SCHEMA_DETAILS_UPDATED.xlsx')
    
    # Print basic info
    print("Columns:", x.columns.tolist())
    
    # Try to group by table_name if it exists
    if 'table_name' in x.columns:
        print("\nTables found:")
        tables = x['table_name'].unique()
        target_tables = ['instalment_plans', 'orders', 'customers', 'merchants_merchant']
        
        # Check if table names in excel have schema prefix or not
        # Let's print unique table names first to check format
        print("First 20 tables:", list(tables[:20]))

        for t in target_tables:
            # simple match
            matches = [x for x in tables if t in x]
            for m in matches:
                print(f"\nTable: {m}")
                cols = x[x['table_name'] == m]['column_name'].tolist() # Guessing column name is 'column_name'
                print(cols)
    else:
        print("\nColumns found:", x.columns.tolist())
except Exception as e:
    print(f"Error reading file: {e}")
