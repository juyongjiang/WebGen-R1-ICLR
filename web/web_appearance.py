import os
import re
import json
import time
import asyncio
import subprocess
import threading
import shutil
from pathlib import Path

import uuid
import tempfile

from .web_code_format import validate_code_format
from .render.step_1_response_parsing import extract_and_build_project, extract_web_actions
from .render.step_2_start_service import start_services
from .render.step_3_get_screenshots import capture_scroll_screenshots
from .render.step_4_vlm_grading import get_score_result, first_grade_int
from .render.utils import load_json, save_json, load_json_or_jsonl


project_root = os.environ.get("PROJECT_ROOT", "./projects")
os.makedirs(project_root, exist_ok=True) 
rollout_file = os.environ.get("ROLLOUT_FILE", "./web_rollout.jsonl")

RANK = int(os.environ.get("RANK", "0"))
def rollout_to_jsonl(problem_id: str, instruction: str, model_response: str, file_path: str=rollout_file):  
    if RANK == 3:
        entry = {
            "problem_id": problem_id,
            "instruction": instruction,
            "model_response": model_response
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def clear_web_project(project_path):
    try:
        # Validate input
        if not project_path:
            return 0    
        # Convert to Path object and resolve absolute path
        project_path = Path(project_path).resolve()
        # Get project name safely
        project_name = project_path.name
        # Stop pm2 service (ignore failures)
        subprocess.run(
            f"pm2 delete {project_name} || true",
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Remove project directory if exists
        if project_path.exists():
            shutil.rmtree(project_path, ignore_errors=True)
        # Remove ecosystem config file if exists
        ecosystem_file = project_path.parent / f"{project_name}_ecosystem.config.js"
        if ecosystem_file.exists():
            ecosystem_file.unlink(missing_ok=True)
        return 1
    except Exception:
        # Return 0 for any exception
        return 0

port_lock = threading.Lock()
used_ports = set()
def grade_web_appearance(model_response: str, problem_id: str, instruction: str) -> float:
    # save rollout for analysis
    rollout_to_jsonl(str(problem_id), instruction, model_response)

    # step 0: web format checking
    try:
        if not validate_code_format(model_response):
            print(f"Invalid code format for problem ID {problem_id}. Skipping...")
            return 0.0
    except Exception as e:
        print(f"Error occurred while processing problem ID {problem_id}: {str(e)}")
        return 0.0
    
    # unique ID for the project
    unique_id = f"rank{RANK}_pid{os.getpid()}_{problem_id}_{uuid.uuid4()}" 
    project_path = tempfile.mkdtemp(prefix=unique_id, dir=project_root)
    try:
        # step 1: response parsing and project extraction
        extract_and_build_project(model_response, output_dir=project_path)

        # step 2: get install and start commands, if not provided, npm install and npm run dev will be used by default
        shell_actions, last_start_action = extract_web_actions(model_response)
        commands = {"shell_actions": shell_actions, "last_start_action": last_start_action}
        if commands["shell_actions"] is None or len(commands["shell_actions"]) == 0:
            commands["shell_actions"] = ["npm install"]
        if commands["last_start_action"] is None or len(commands["last_start_action"]) == 0:
            commands["last_start_action"] = "npm run dev"
        
        # step 3: run the project and take screenshots
        port, project_name = start_services(project_path, commands, used_ports, port_lock)

        # step 4: capture screenshots by port
        shot_path = capture_scroll_screenshots(
            url = f"http://localhost:{port}/",
            out_dir = os.path.join(project_path, "shots"),
            user_data_dir = os.path.join(project_path, "chrome_data"),
            max_shots = 1,
            pause = 0.8, # 0.4
            viewport_height = 768
        )

        # step 5: evaluate the appearance
        image_paths = [os.path.join(shot_path, f) for f in os.listdir(shot_path) if f.endswith(".png")]
        output = get_score_result(image_paths, instruction)
        grade_score = first_grade_int(output)
        result_path = os.path.join(project_path, "shots", "appearance_result.json")
        save_json([
            {"instruction": instruction}, 
            {"vlm_output": output}, 
            {"grade_score": grade_score}
        ], result_path)

        return grade_score # / 5.0
    except Exception as e:
        print(f"Error occurred while processing problem ID {problem_id}: {str(e)}")
        return 0.0
    finally:
        clear_web_project(project_path)
        if 'port' in locals():
            with port_lock:
                used_ports.discard(port)

async def async_grade_web_appearance(model_response: str, problem_id: str, instruction: str) -> float:
    return await asyncio.to_thread(
        grade_web_appearance,
        model_response,
        problem_id,
        instruction
    )

    