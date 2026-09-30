import pandas as pd

input_file = r"data\raw\chicago_scooter_trips.csv"
output_file = r"data\chicago_scooter_sample.csv"

chunks = []

for chunk in pd.read_csv(input_file, chunksize=100_000):
    # First inspect available columns
    print(chunk.columns.tolist())
    
    # Keep only the first chunk for now
    chunks.append(chunk)
    break

sample = pd.concat(chunks, ignore_index=True)
sample.to_csv(output_file, index=False)

print(f"Saved {len(sample):,} rows to {output_file}")