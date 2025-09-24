import os
import re
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple


def extract_web_actions(text: str) -> Tuple[List[str], str]:
    # Extract all shell actions
    shell_actions = re.findall(r'<webAction type="shell">(.*?)</webAction>', text, re.DOTALL)

    # Extract all start actions
    start_actions = re.findall(r'<webAction type="start">(.*?)</webAction>', text, re.DOTALL)

    # Get the last start action, if any
    last_start_action = start_actions[-1] if start_actions else ""

    return (shell_actions, last_start_action)

def extract_and_build_project(model_response: str, output_dir: str = "web_project"):
    """
    Extract frontend project from LLM response and build standardized file structure
    
    Args:
        model_response: Full response text from LLM
        output_dir: Output directory for project (default: web_project)
    """
    try:
        # Prepare output directory
        project_path = Path(output_dir)
        if project_path.exists():
            shutil.rmtree(project_path, ignore_errors=True)
        project_path.mkdir(parents=True)
        
        # Extract webArtifact content using regex
        artifact_match = re.search(r'<webArtifact[^>]*>(.*?)</webArtifact>', 
                                model_response, re.DOTALL)
        if not artifact_match:
            # raise ValueError("No webArtifact content found in response")
            return None
        
        artifact_content = artifact_match.group(1)
        
        # Create dependency install and server start scripts
        install_script = project_path / "install_dependencies.sh"
        start_script = project_path / "start_server.sh"
        # Initialize scripts with headers
        with open(install_script, "w", encoding="utf-8") as inst_f:
            inst_f.write("#!/bin/bash\n")
            inst_f.write("# Auto-generated dependency installation script\n")
            inst_f.write("set -e\n\n")
            inst_f.write('echo "Installing project dependencies..."\n')
            
        with open(start_script, "w", encoding="utf-8") as start_f:
            start_f.write("#!/bin/bash\n")
            start_f.write("# Auto-generated server start script\n")
            start_f.write("set -e\n\n")
            start_f.write('echo "Starting development server..."\n')
        
        # Track if package.json exists and its content
        package_json_content = None
        package_json_path = None
        
        # Extract all webAction elements using regex
        action_pattern = re.compile(
            r'<webAction\s+type="([^"]+)"(?:.*?filePath="([^"]+)")?.*?>(.*?)</webAction>',
            re.DOTALL
        )
        
        for match in action_pattern.finditer(artifact_content):
            action_type = match.group(1)
            file_path = match.group(2)
            action_text = match.group(3).strip()
            
            if action_type == "shell":
                # Add to install script
                with open(install_script, "a", encoding="utf-8") as inst_f:
                    inst_f.write(f"{action_text}\n")
                    
            elif action_type == "file" and file_path:
                # Create file
                full_path = project_path / file_path
                try:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                except FileExistsError:
                    pass
                except Exception as e:
                    raise
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(action_text)
                
                # Store package.json content for validation
                if file_path == "package.json":
                    package_json_content = action_text
                    package_json_path = full_path
                    
            elif action_type == "start":
                # Add to start script
                with open(start_script, "a", encoding="utf-8") as start_f:
                    start_f.write(f"{action_text}\n")
        
        # Validate package.json if exists
        if package_json_content:
            try:
                package_data = json.loads(package_json_content)
                
                # Check for missing keys
                required_keys = {"name", "version", "scripts", "dependencies", "devDependencies"} # package.json required keys
                missing_keys = required_keys - set(package_data.keys())
                if missing_keys:
                    # print(f"Warning: package.json missing required keys: {missing_keys}")
                    pass
                
                # Check core dependencies
                core_deps = {"react", "react-dom", "vite"} # core dependencies for a Vite React project
                dep_keys = set(package_data.get("dependencies", {}).keys())
                dev_dep_keys = set(package_data.get("devDependencies", {}).keys())
                all_deps = dep_keys | dev_dep_keys
                missing_core = core_deps - all_deps
                if missing_core:
                    # print(f"Warning: package.json missing core dependencies: {missing_core}")
                    pass
                    
                # Verify scripts section
                required_scripts = {"dev", "build", "preview"}
                script_keys = set(package_data.get("scripts", {}).keys())
                missing_scripts = required_scripts - script_keys
                if missing_scripts:
                    # print(f"Warning: package.json missing required scripts: {missing_scripts}")
                    pass
                    
            except json.JSONDecodeError:
                # print("Warning: Invalid JSON format in package.json")
                pass
        else:
            # print("Warning: No package.json found in project artifact")
            pass
        
        # Add execute permissions to scripts
        install_script.chmod(0o755)
        start_script.chmod(0o755)
        
        return project_path
    except Exception as e:
        print(f"Error during project extraction/build: {e}")
        return None

def print_project_structure(path: Path, prefix: str = "", is_last: bool = True):
    """Recursively print project directory structure"""
    # Current item display
    pointer = "└── " if is_last else "├── "
    print(f"{prefix}{pointer}{path.name}")
    
    # Handle directories recursively
    if path.is_dir():
        prefix += "    " if is_last else "│   "
        children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        count = len(children)
        
        for i, child in enumerate(children):
            is_last_child = (i == count - 1)
            print_project_structure(child, prefix, is_last_child)
