import pandas as pd
import random
import string
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def add_terminals():
    print("Adding Terminal Data...")
    try:
        branches_df = pd.read_csv('merchant_branches.csv')
    except FileNotFoundError:
        print("Run 04_generate_advanced_data.py first.")
        return
        
    terminals = []
    # 1. Create the Payment Terminals
    for _, branch in branches_df.iterrows():
        # Each branch has 1 to 3 payment points (e.g., 3 cash registers, or 3 QR codes pinned to tables)
        num_terminals = random.randint(1, 3)
        for t in range(num_terminals):
            # Generate a random 8-character QR code suffix
            qr_code = "QR_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            # Generate a dummy phone number for mobile money wallet
            wallet_phone = f"+234-{random.randint(700, 999)}-{random.randint(1000, 9999)}"
            
            terminals.append({
                'terminal_id': f"{branch['branch_id']}_T{t+1}",
                'branch_id': branch['branch_id'],
                'qr_code_id': qr_code,
                'merchant_wallet_number': wallet_phone,
                'terminal_status': 'ACTIVE'
            })
            
    terminals_df = pd.DataFrame(terminals)
    terminals_df.to_csv('payment_terminals.csv', index=False)
    print(f"Generated {len(terminals_df)} Payment Terminals in 'payment_terminals.csv'.")
    
    # 2. Update Transactions
    print("Updating Transactions to use Terminals...")
    txns_df = pd.read_csv('advanced_transactions.csv')
    
    # Assign a random terminal to each transaction based on the branch where the transaction occurred
    def assign_terminal(branch_id):
        branch_terminals = terminals_df[terminals_df['branch_id'] == branch_id]['terminal_id'].tolist()
        return random.choice(branch_terminals) if branch_terminals else None
        
    txns_df['terminal_id'] = txns_df['branch_id'].apply(assign_terminal)
    
    # Reorder columns to put terminal_id early in the CSV
    cols = txns_df.columns.tolist()
    cols.insert(2, cols.pop(cols.index('terminal_id')))
    txns_df = txns_df[cols]
    
    txns_df.to_csv('advanced_transactions.csv', index=False)
    print("Transactions updated! If you look at advanced_transactions.csv, it now shows exactly WHICH terminal processed the transaction.")

if __name__ == "__main__":
    add_terminals()
