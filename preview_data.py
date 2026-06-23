import pandas as pd
import os

data_path = os.path.join(os.path.dirname(__file__), "data", "train.parquet")
df = pd.read_parquet(data_path)

print(f"Shape: {df.shape}")
print(f"\nColumns ({len(df.columns)}):")
for col in df.columns:
    print(f"  - {col} ({df[col].dtype})")

print(f"\nFirst 10 rows:\n")
print(df.head(10).to_string())
