import pandas as pd

# 1. Create a practical sample dataset 
# Imagine this is a daily log of users and their account statuses
data = {
    'Date': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
    'User': ['Alice', 'Alice', 'Alice', 'Bob', 'Bob'],
    'Status': ['Active', 'Active', 'Suspended', 'Active', 'Active']
}
df = pd.DataFrame(data)

print("=== 1. ORIGINAL DATAFRAME ===")
print(df)
print("\n")

# 2. Let's look at exactly what shift(1) does mathematically
# It takes the entire DataFrame and pushes it down by 1 row. 
# The top row gets filled with NaN (Not a Number/Null).
shifted_df = df.shift(1)
print("=== 2. WHAT df.shift(1) LOOKS LIKE ===")
print(shifted_df)
print("\n")

# 3. Vectorized comparison for the entire DataFrame
# df != df.shift(1) checks every single cell and asks:
# "Is this value DIFFERENT from the value that was here yesterday (the row above)?"
differences = df != df.shift(1)
print("=== 3. BOOLEAN DIFFERENCES (True means the value changed) ===")
print(differences)
print("\n")

# 4. PRACTICAL APPLICATION: Finding Status Changes
# In the real world, you use this to find the exact moment something broke or changed.
# We want to find where 'Status' changed, BUT we only care if it's the same 'User'.
# (We don't want it to flag as a "change" just because we switched from Alice to Bob)

status_changed = (df['Status'] != df.shift(1)['Status']) & (df['User'] == df.shift(1)['User'])

print("=== 4. REAL WORLD USE: Exactly when did a user's status change? ===")
# We use the boolean mask to filter the dataframe
print(df[status_changed])
