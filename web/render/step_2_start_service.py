import os
import subprocess
import threading
import json
import re
import time
import sys
import shlex
from pathlib import Path
import shutil
import socket


RANK = int(os.environ.get("RANK", "0"))

def run_npm_install(project_path, commands, timeout=300):
    """
    Run npm install commands for each app, retrying with --force and then
    --legacy-peer-deps if the original command fails.  Errors are logged but
    never propagate, so the calling code keeps running.
    """
    def remove_npm_run_dev(command_line: str) -> str:
        parts = [part.strip() for part in command_line.split("&&")]
        filtered_parts = [part for part in parts if part != "npm run dev" and part != "npm run start" and part != "npm run server" and part != "npm start"]
        return " && ".join(filtered_parts) # npm install

    def _add_flag(cmd: str, flag: str) -> str:
        """
        Insert an extra flag (e.g. --force) right after every occurrence of
        `npm install` in the command string, unless it is already present.
        """
        pattern = r"(npm\s+install)(?![^&]*\b" + re.escape(flag) + r"\b)"
        replacement = rf"\1 {flag}"
        return re.sub(pattern, replacement, cmd)

    def get_project_cache_dir() -> str:
        cache_dir = os.path.join(project_path, "npm_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    cwd = Path(project_path)
    if os.path.exists(cwd / "node_modules"):
        shutil.rmtree(cwd / "node_modules") 

    cache_dir = get_project_cache_dir()

    for raw_cmd in commands["shell_actions"]:
        raw_cmd = remove_npm_run_dev(raw_cmd)
        base_cmd = f"npm install --cache {cache_dir}" + raw_cmd.replace("npm install", "").strip()
        # Build the three attempts
        attempts = [
            base_cmd,
            _add_flag(base_cmd, "--force"),
            _add_flag(base_cmd, "--legacy-peer-deps"),
        ]

        for idx, cmd in enumerate(attempts, start=1):
            try:
                # print(f"  ▶ Attempt {idx}: {cmd}")
                subprocess.run(cmd, shell=True, cwd=cwd, check=True, timeout=timeout) # cwd = project_path
                # print("  ✅ Success\n")
                break                       # success → next shell_action
            except subprocess.TimeoutExpired:  # timeout expired
                print(f"  ⏰ Attempt {cmd} timed out after {timeout} seconds")
                continue  
            except subprocess.CalledProcessError as e:
                # print(f"  ⚠️  Attempt {idx} failed (exit {e.returncode})")
                continue
        else:
            # all attempts failed
            # print(f"  ❌ Giving up on {raw_cmd}\n")
            raise

def update_vite_config_port(project_path: str):
    """
    Safely updates or creates the server.port configuration in Vite config file.
    Handles all cases including missing defineConfig and server fields.

    Args:
        project_path: Path to Vite project directory

    Raises:
        FileNotFoundError: If vite.config.ts doesn't exist
        ValueError: If the config file has unrecognizable structure
    """
    config_path = Path(project_path) / "vite.config.ts"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Vite config file not found at {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        port_config = "port: parseInt(process.env.PORT || '5173', 10)"
        modified = False

        # Case 1: No defineConfig found - create entire config structure
        if "defineConfig" not in content:
            new_content = f"""import {{ defineConfig }} from 'vite'

export default defineConfig({{
  server: {{
    {port_config}
  }}
}})
"""
            modified = True
        else:
            # Case 2: defineConfig exists but no server field
            if "server:" not in content:
                # Insert server config into defineConfig
                new_content = re.sub(
                    r'defineConfig\((\{[\s\S]*?\})\)',
                    f'defineConfig({{server: {{\n    {port_config}\n  }},\\1}})',
                    content
                )
                modified = True
            else:
                # Case 3: Server exists but no port
                if "port:" not in content:
                    new_content = re.sub(
                        r'server:\s*\{([\s\S]*?)\}',
                        f'server: {{\n    {port_config},\\1\n  }}',
                        content
                    )
                    modified = True
                else:
                    # Case 4: Port exists - overwrite it
                    new_content = re.sub(
                        r'port:\s*[^,\n]+',
                        port_config,
                        content
                    )
                    modified = True

        if modified:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            # print(f"Successfully updated {config_path}")
        else:
            print(f"No changes needed for {config_path}")

    except Exception as e:
        print(f"Error processing {config_path}: {e}")
        raise

# PM2 ecosystem configuration file generation
WRAPPER_FILENAME = "start-wrapper.cjs"
WRAPPER_TEMPLATE = """
const {{ spawn }} = require('child_process');

const child = spawn({command}, {args}, {{
  shell: true,
  stdio: 'inherit',
  windowsHide: true
}});

child.on('error', err => {{
  console.error('Failed to start child process:', err);
}});
"""

# generates a PM2 ecosystem configuration file for pm2 to start the Node.js application
def generate_ecosystem_config(project_path, commands, port):
    def parse_start_command(command_str):
        parts = shlex.split(command_str)
        command = json.dumps(parts[0])
        args = json.dumps(parts[1:])
        return command, args

    def create_wrapper_script(project_path, start_command):
        command, args = parse_start_command(start_command)
        script_content = WRAPPER_TEMPLATE.format(command=command, args=args)
        # replace("{command}", command).replace("{args}", args)
        wrapper_path = os.path.join(project_path, WRAPPER_FILENAME)
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(script_content.strip())
        # print(f"📝 Created wrapper in {wrapper_path}")

    apps_config = []
    create_wrapper_script(project_path, commands["last_start_action"])
    project_name = os.path.basename(os.path.normpath(project_path))
    apps_config.append({
        "name": project_name,
        "cwd": str(project_path), # cd path and find the start-wrapper.cjs file
        "script": "node",
        "args": WRAPPER_FILENAME, 
        "error_file": str(Path(project_path).resolve() / f"err.log"),
        "out_file": str(Path(project_path).resolve() / f"out.log"),
        # "log_file": str(Path(project_path).resolve() / f"combined.log"),
        "autorestart": False,
        "env": {
            "PORT": port,
            "NODE_ENV": "production"
        }
    })

    # write config to ecosystem.config.js which is a config file of PM2
    ecosystem_path = os.path.join(Path(project_path).parent, f"{project_name}_ecosystem.config.js")
    content = "module.exports = " + json.dumps({"apps": apps_config}, indent=2) + ";"
    with open(ecosystem_path, "w") as f:
        f.write(content)
    # print(f"✅ Generated {ecosystem_path}")
    return ecosystem_path, project_name


def start_pm2(project_path, commands, used_ports, port_lock):
    def run_command(cmd):
        kwargs = dict(shell=True)
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.run(cmd, **kwargs)
    # assign a free port to the project
    def find_free_port():
        base_port = 30000 + RANK * 5000  
        with port_lock:
            for offset in range(5000):
                port = base_port + offset
                if port in used_ports:
                    continue
                try:
                    with socket.socket() as s:
                        time.sleep(RANK * 0.1)  # wait for a while to avoid port conflict
                        s.bind(("", port))
                    used_ports.add(port)
                    return port
                except OSError:
                    continue
        raise RuntimeError("No free port in range!")
    port = find_free_port()

    ecosystem_path, project_name = generate_ecosystem_config(project_path, commands, port)
    # update vite.config.js to use the assigned port
    update_vite_config_port(project_path)
    
    # print(f"🚀 Starting {ecosystem_path} apps with PM2...")
    # delete existing running log
    out_log_file = os.path.join(project_path, f"out.log")
    err_log_file = os.path.join(project_path, f"err.log")
    if os.path.exists(out_log_file) and os.path.exists(err_log_file):
        os.remove(out_log_file)
        os.remove(err_log_file)
        # print(f"🗑️ Removed existing log file: {out_log_file} and {err_log_file}")
    
    run_command(f"pm2 delete {project_name} || true")
    run_command(f"pm2 start {ecosystem_path}") # pm2 start project_name_ecosystem.config.js
    return project_name


def detect_ports_from_pm2_logs(project_path, project_name):
    # print(f"🔍 Detecting ports from PM2 logs at {project_path}...")
    
    port_pattern = re.compile(r"http[s]?://(?:localhost|127\.0\.0\.1):(\d+)", re.IGNORECASE)
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')    

    DETECTION_TIMEOUT = 30  # 20 seconds
    start_time = time.time()
    last_port = None
    while time.time() - start_time < DETECTION_TIMEOUT:
        log_file = os.path.join(project_path, f"out.log")
        if not os.path.exists(log_file):
            continue

        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            content = ansi_escape.sub('', content).strip()
            match = port_pattern.findall(content) # search(content)
            if match:
                port = int(match[-1]) # int(match.group(1))
                # print(f"✅ {project_name} is running on port {port}")
                return port


def start_services(project_path, commands, used_ports, port_lock):
    # step 1: run npm install command
    run_npm_install(project_path, commands)
    
    # step 2: run npm start command with unique port detection
    project_name = start_pm2(project_path, commands, used_ports, port_lock)
    port = detect_ports_from_pm2_logs(project_path, project_name)

    output_path = os.path.join(project_path, "services.json")
    with open(output_path, "w") as f:
        json.dump({project_name: port}, f, indent=2)
    # print(f"📄 Saved service ports to {output_path}")

    return port, project_name
