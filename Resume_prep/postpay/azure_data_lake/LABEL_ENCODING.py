from sklearn.preprocessing import LabelEncoder

# Initialize Encoder
le = LabelEncoder()

# Fit and Transform 'device_type'
# This converts: "iPhone" -> 1, "Android" -> 0, "Windows" -> 2
df['device_type_encoded'] = le.fit_transform(df['device_type'].astype(str))

# Check the mapping
print("Mapping:", dict(zip(le.classes_, le.transform(le.classes_))))

# View result
print(df[['device_type', 'device_type_encoded']].head())
