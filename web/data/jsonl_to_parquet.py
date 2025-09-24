from datasets import Dataset
import pandas as pd
from pathlib import Path


def jsonl_to_sharded_parquet(jsonl_path: str, output_dir: str, chunksize: int, tag: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for i, chunk in enumerate(pd.read_json(jsonl_path, lines=True, chunksize=chunksize)):
        shard_path = f"{output_dir}/{tag}-{i:05d}-of-{len(chunk):05d}.parquet"
        Dataset.from_pandas(chunk).to_parquet(shard_path)


jsonl_to_sharded_parquet(
    jsonl_path="train.jsonl",
    output_dir="./parquet",  
    chunksize=500_000, 
    tag="train"
)

jsonl_to_sharded_parquet(
    jsonl_path="test.jsonl",
    output_dir="./parquet",  
    chunksize=500_000,  
    tag="test"
)