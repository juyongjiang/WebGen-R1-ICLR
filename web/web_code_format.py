import re
import json
import asyncio
from typing import Dict, List, Tuple


def validate_code_format(model_response: str) -> float:
    """
    Validate if the LLM response strictly follows the required web project generation format

    Args:
        model_response: Full text response from the LLM

    Returns:
        1.0 if format is fully compliant, 0 otherwise
    """
    # Phase 1: Extract webArtifact block and attributes
    artifact_match = re.search(r'<webArtifact\s+([^>]*)>(.*?)</webArtifact>', model_response, re.DOTALL)
    if not artifact_match:
        return 0.0  # Missing required artifact block

    artifact_attrs = artifact_match.group(1)
    artifact_content = artifact_match.group(2)

    # Extract artifact attributes using regex
    id_match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', artifact_attrs)
    title_match = re.search(r'title\s*=\s*["\']([^"\']+)["\']', artifact_attrs)

    if not id_match or not title_match:
        return 0.0  # Missing required id/title attributes

    # Phase 2: Initialize validation flags
    validation_flags = {
        'package_json_exists': False,
        'package_json_valid': False,
        'vite_config_exists': False,
        'shell_install_exists': False,
        'start_command_exists': False,
        'page_component_exists': False,
        'required_files': []
    }

    # Phase 3: Process all webAction elements using regex
    action_pattern = re.compile(
        r'<webAction\s+type\s*=\s*["\']([^"\']+)["\']'  # type attribute
        r'(?:\s+filePath\s*=\s*["\']([^"\']+)["\'])?'   # optional filePath
        r'\s*>(.*?)</webAction>',                        # content
        re.DOTALL
    )

    for match in action_pattern.finditer(artifact_content):
        action_type = match.group(1)
        file_path = match.group(2) if match.group(2) else None
        action_text = match.group(3).strip()

        # Validate file actions
        if action_type == "file" and file_path:
            # Track all created files
            validation_flags['required_files'].append(file_path)

            # Check for package.json
            if file_path == "package.json":
                validation_flags['package_json_exists'] = True

                # Validate package.json content
                try:
                    package_data = json.loads(action_text)
                    required_keys = {"name", "version", "scripts", "dependencies", "devDependencies"}

                    # Check for required keys
                    if required_keys.issubset(package_data.keys()):
                        # Check for core dependencies
                        core_deps = {"react", "react-dom", "vite"}
                        all_deps = set(package_data.get("dependencies", {}).keys()) | \
                                   set(package_data.get("devDependencies", {}).keys())

                        if core_deps.issubset(all_deps):
                            # Check required scripts
                            required_scripts = {"dev", "build", "preview"}
                            if required_scripts.issubset(package_data.get("scripts", {}).keys()):
                                validation_flags['package_json_valid'] = True

                except json.JSONDecodeError:
                    pass  # Will remain invalid

            # Check for vite.config.ts
            elif file_path == "vite.config.ts":
                validation_flags['vite_config_exists'] = True
                # if "base: './'" not in action_text:
                #     return 0.0

            # Check for page components
            elif (file_path.startswith("src/pages/") or file_path.startswith("src/components/")) and file_path.endswith(".tsx"):
                validation_flags['page_component_exists'] = True
                # allow export default X
                if not re.search(r'export\s+default\s+', action_text):
                    return 0.0

        # Validate shell install command
        elif action_type == "shell":
            # if "npm install" in action_text:
            if re.search(r'\bnpm install\b', action_text):
                validation_flags['shell_install_exists'] = True

        # Validate start command
        elif action_type == "start":
            # if "npm run dev" in action_text or "npm run start" in action_text:
            if re.search(r'\bnpm run dev\b', action_text) or re.search(r'\bnpm run start\b', action_text):
                validation_flags['start_command_exists'] = True

    # Phase 4: Check required file structure (customized)
    required_structure = {
        "package.json": True,
        "vite.config.ts": True,
        "src/main.tsx": False,  # Not always required
        "src/App.tsx": False,   # Not always required
        "src/pages/": False # validation_flags['page_component_exists']
    }
    for file_path, required in required_structure.items():
        if required:
            # Check directory exists for paths ending with /
            if file_path.endswith("/"):
                if not any(fp.startswith(file_path) for fp in validation_flags['required_files']):
                    return 0.0
            # Check exact file match
            elif file_path not in validation_flags['required_files']:
                return 0.0

    # Phase 5: Final compliance check
    required_flags = [
        validation_flags['package_json_exists'],
        validation_flags['package_json_valid'],
        validation_flags['vite_config_exists'],
        validation_flags['shell_install_exists'],
        validation_flags['start_command_exists'],
        validation_flags['page_component_exists']
    ]

    # print(required_flags)
    # Return 1.0 only if ALL requirements are met
    return 1.0 if all(required_flags) else 0.0

async def async_validate_code_format(model_response: str) -> float:
    return await asyncio.to_thread(
        validate_code_format,
        model_response
    )
