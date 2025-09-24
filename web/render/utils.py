import os
import json
from pathlib import Path


def load_json(file_path):
    """Load JSON file and return data, with enhanced error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # print(f"Error: Invalid JSON format - {file_path}: {e}")
        return None
    except Exception as e:
        # print(f"Error: Failed to read file - {file_path}: {e}")
        return None

def save_json(data, out_file):
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_json_or_jsonl(file_path):
    file_path = Path(file_path)
    if file_path.suffix not in {'.json', '.jsonl'}:
        raise ValueError("File must be .json or .jsonl format")

    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix == '.json':
            # Standard JSON file (entire file is one JSON array/object)
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]  # If JSON is single object, convert to list
        else:  # .jsonl
            # JSONL file (one JSON object per line)
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    data.append(json.loads(line))
    return data