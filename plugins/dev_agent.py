import subprocess
import sys
import json
import re
import time
from pathlib import Path

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR         = get_base_dir()
API_CONFIG_PATH  = BASE_DIR / "config" / "api_keys.json"
PROJECTS_DIR     = Path.home() / "Desktop" / "JarvisProjects"
MAX_FIX_ATTEMPTS = 5
MODEL_PLANNER    = "gemini-2.5-flash"
MODEL_WRITER     = "gemini-2.5-flash"

PLUGIN = {
    "name": "dev_agent",
    "description": "Spawns a specialized developer agent for complex codebase tasks. It can autonomously write, test, and fix entire projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description": {
                "type": "STRING",
                "description": "The detailed description of the project to build."
            },
            "language": {
                "type": "STRING",
                "description": "The programming language to use (e.g. python, javascript)."
            },
            "project_name": {
                "type": "STRING",
                "description": "The name of the project folder to create."
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Timeout in seconds for running tests."
            }
        },
        "required": ["description"]
    }
}

def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        import os
        return os.environ.get("GEMINI_API_KEY", "")

def _get_model(model_name: str):
    from google import genai
    _c = genai.Client(api_key=_get_api_key())
    class _W:
        def generate_content(self, contents):
            return _c.models.generate_content(model=model_name, contents=contents)
    return _W()

def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()

def _is_rate_limit(error: Exception) -> bool:
    msg = str(error).lower()
    return "429" in msg or "quota" in msg or "resource_exhausted" in msg

def _parse_traceback(output: str, project_files: list[str]) -> tuple[str | None, int | None]:
    pattern = re.compile(r'File ["\']([^"\']+\.py)["\'],\s+line\s+(\d+)', re.IGNORECASE)
    matches = pattern.findall(output)
    for raw_path, line_str in reversed(matches):
        raw_name = Path(raw_path).name
        for pf in project_files:
            if Path(pf).name == raw_name or pf == raw_path or raw_path.endswith(pf):
                return pf, int(line_str)
    return None, None

def _classify_error(output: str) -> str:
    low = output.lower()
    if any(x in low for x in ("no module named", "modulenotfounderror", "importerror")):
        return "dependency_error"
    if "syntaxerror" in low or "invalid syntax" in low:
        return "syntax_error"
    if "cannot import" in low or "importerror" in low:
        return "import_error"
    if any(x in low for x in (
        "traceback", "exception", "error:", "nameerror", "typeerror",
        "attributeerror", "valueerror", "keyerror", "indexerror",
        "zerodivisionerror", "filenotfounderror", "permissionerror",
    )):
        return "runtime_error"
    return "none"

def _has_error(output: str, run_command: str) -> bool:
    low = output.lower()
    if "timed out" in low:
        return False
    if not output.strip():
        return False
    return _classify_error(output) != "none"

class RateLimitError(Exception):
    pass

def _plan_project(description: str, language: str) -> dict:
    model = _get_model(MODEL_PLANNER)
    prompt = f"""You are a senior software architect. Create a minimal, complete file plan for this project.

Language: {language}
Description: {description}

Return ONLY valid JSON — no markdown, no explanation:
{{
  "project_name": "snake_case_name",
  "entry_point": "main.py",
  "files": [
    {{
      "path": "main.py",
      "description": "Entry point — what it does and which modules it imports",
      "imports": ["utils.helpers", "core.engine"]
    }},
    {{
      "path": "utils/helpers.py",
      "description": "Helper utilities — what functions it exposes",
      "imports": []
    }}
  ],
  "run_command": "python main.py",
  "dependencies": ["requests"]
}}

Critical rules:
1. List files in DEPENDENCY ORDER — files with no imports come first, entry point comes last.
2. The "imports" field must list every other project module this file imports (dot-notation).
3. Keep it minimal — only files truly needed.
4. Entry point must be in the files list.
5. Use relative paths only.
6. Standard library modules (os, sys, json, etc.) do NOT go in "dependencies".

JSON:"""
    try:
        response = model.generate_content(prompt)
        raw = _strip_fences(response.text)
        return json.loads(raw)
    except Exception as e:
        if _is_rate_limit(e):
            raise RateLimitError(str(e))
        raise

def _write_file(file_info: dict, project_description: str, all_files: list[dict], language: str, project_dir: Path, already_written: dict[str, str]) -> str:
    model = _get_model(MODEL_WRITER)
    file_path = file_info["path"]
    file_desc = file_info.get("description", "")
    file_imports = file_info.get("imports", [])

    file_list = "\n".join(f"  [{i+1}] {f['path']}: {f.get('description', '')}" for i, f in enumerate(all_files))
    dependency_context = ""
    for dep_dotted in file_imports:
        dep_path = dep_dotted.replace(".", "/") + ".py"
        if dep_path in already_written:
            code_snippet = already_written[dep_path][:2000]
            dependency_context += f"\n\n--- {dep_path} (you must import from this) ---\n{code_snippet}"

    lang_rules = ""
    if language.lower() == "python":
        lang_rules = """
Python-specific rules:
- Use type hints. Add docstrings.
- Use if __name__ == "__main__": guard in the entry point.
- For relative imports within the project, use: from utils.helpers import foo
- Do NOT use implicit relative imports. Create __init__.py where needed."""

    prompt = f"""You are a senior {language} developer.
Project goal: {project_description}

Project structure:
{file_list}

{f"Dependencies context:{dependency_context}" if dependency_context else ""}

Write code for: {file_path}
Purpose: {file_desc}

{lang_rules}

Rules:
- Output ONLY raw code. Absolutely no explanation, no markdown.
- Write COMPLETE, RUNNABLE code — no placeholders, no "pass" stubs.
- Every import must be from standard library, dependencies, or project files.

Code for {file_path}:"""

    try:
        response = model.generate_content(prompt)
        code = _strip_fences(response.text)
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding="utf-8")
        return code
    except Exception as e:
        if _is_rate_limit(e):
            raise RateLimitError(str(e))
        raise

def _install_dependencies(dependencies: list[str], project_dir: Path) -> str:
    if not dependencies: return "No external dependencies."
    to_install = []
    for dep in dependencies:
        pkg_name = re.split(r"[>=<!]", dep)[0].strip()
        if subprocess.run([sys.executable, "-m", "pip", "show", pkg_name], capture_output=True).returncode != 0:
            to_install.append(dep)
    if not to_install: return "All dependencies installed."
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install"] + to_install, capture_output=True, text=True, timeout=120, cwd=str(project_dir))
        return f"Installed: {', '.join(to_install)}" if result.returncode == 0 else f"Install warning: {result.stderr[:200]}"
    except Exception as e:
        return f"Install error: {e}"

def _open_vscode(project_dir: Path):
    candidates = ["code", rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd", r"C:\Program Files\Microsoft VS Code\bin\code.cmd"]
    for cmd in candidates:
        try:
            subprocess.Popen([cmd, str(project_dir)], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    return False

def _run_project(run_command: str, project_dir: Path, timeout: int = 30) -> str:
    try:
        parts = run_command.split()
        if parts[0].lower() == "python": parts[0] = sys.executable
        res = subprocess.run(parts, capture_output=True, text=True, timeout=timeout, cwd=str(project_dir))
        combined = []
        if res.stdout: combined.append(f"STDOUT:\n{res.stdout.strip()}")
        if res.stderr: combined.append(f"STDERR:\n{res.stderr.strip()}")
        return "\n\n".join(combined) if combined else "Ran with no output."
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s — long-running app."
    except Exception as e:
        return f"Run error: {e}"

def _try_auto_install(error_output: str, project_dir: Path) -> bool:
    match = re.search(r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]", error_output, re.IGNORECASE)
    if not match: return False
    pkg = match.group(1).replace("_", "-").split(".")[0]
    try:
        return subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, timeout=60, cwd=str(project_dir)).returncode == 0
    except: return False

def _fix_files(error_output: str, project_description: str, all_files: list[dict], file_codes: dict[str, str], language: str, project_dir: Path, entry_point: str) -> dict[str, str]:
    model = _get_model(MODEL_PLANNER)
    error_file, error_line = _parse_traceback(error_output, list(file_codes.keys()))
    error_type = _classify_error(error_output)
    
    files_to_fix = []
    if error_file:
        files_to_fix.append(error_file)
        if error_type == "import_error":
            for fi in all_files:
                if error_file.replace("/", ".").replace(".py", "") in fi.get("imports", []):
                    if fi["path"] not in files_to_fix: files_to_fix.append(fi["path"])
    else:
        files_to_fix.append(entry_point)

    updated_codes = {}
    for fix_path in files_to_fix:
        other_ctx = "".join(f"\n--- {fp} ---\n{c[:1500]}\n" for fp, c in file_codes.items() if fp != fix_path)
        prompt = f"""You are an expert debugger. Fix this file.
Project: {project_description}
Other files (read-only):{other_ctx[:3500]}
File to fix: {fix_path}
Error type: {error_type}
Error output:
{error_output[:2500]}
Current code:
{file_codes.get(fix_path, "")}

Rules:
- Output ONLY the complete fixed code. No explanation.
- Fix all errors. Do not remove working features.
Fixed code:"""
        try:
            response = model.generate_content(prompt)
            fixed = _strip_fences(response.text)
            (project_dir / fix_path).write_text(fixed, encoding="utf-8")
            updated_codes[fix_path] = fixed
        except Exception:
            pass
    return updated_codes

def run(parameters: dict, player=None) -> str:
    description = parameters.get("description", "").strip()
    language = parameters.get("language", "python").strip()
    project_name = parameters.get("project_name", "").strip()
    timeout = int(parameters.get("timeout", 30))

    if not description:
        return "Please describe the project you want me to build."

    def log(msg: str):
        print(f"[DevAgent] {msg}")
        if player: player.write_log(f"[DevAgent] {msg}")

    log("Planning project structure...")
    try: plan = _plan_project(description, language)
    except Exception as e: return f"Planning failed: {e}"

    proj_name = project_name or plan.get("project_name", "jarvis_project")
    proj_name = re.sub(r"[^\w\-]", "_", proj_name)
    project_dir = PROJECTS_DIR / proj_name
    project_dir.mkdir(parents=True, exist_ok=True)

    files = plan.get("files", [])
    entry_point = plan.get("entry_point", "main.py")
    run_command = plan.get("run_command", f"python {entry_point}")
    deps = plan.get("dependencies", [])

    log(f"Project: {proj_name} | Files: {len(files)} | Entry: {entry_point}")
    file_codes = {}

    for fi in sorted(files, key=lambda x: len(x.get("imports", []))):
        path = fi.get("path", "")
        if not path: continue
        log(f"Writing {path}...")
        try: file_codes[path] = _write_file(fi, description, files, language, project_dir, file_codes)
        except Exception as e: log(f"Failed to write {path}: {e}")

    if not file_codes: return "Could not write any project files."
    if deps: log(_install_dependencies(deps, project_dir))
    _open_vscode(project_dir)

    last_output = ""
    auto_installs = 0
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        log(f"Running project (attempt {attempt}/{MAX_FIX_ATTEMPTS})...")
        last_output = _run_project(run_command, project_dir, timeout)
        if not _has_error(last_output, run_command):
            return f"Project '{proj_name}' is working! Built in {attempt} attempts. Saved to: {project_dir}\n\nOutput:\n{last_output[:200]}"
        
        if attempt == MAX_FIX_ATTEMPTS: break
        err_type = _classify_error(last_output)
        if err_type == "dependency_error" and auto_installs < 3:
            if _try_auto_install(last_output, project_dir):
                auto_installs += 1; log("Missing dependency installed, retrying..."); continue
        
        log(f"Fixing errors ({err_type})...")
        try: file_codes.update(_fix_files(last_output, description, files, file_codes, language, project_dir, entry_point))
        except Exception as e: log(f"Fix step failed: {e}")

    return f"I couldn't fully fix '{proj_name}'. Open it in VSCode manually at {project_dir}.\n\nLast error:\n{last_output[:400]}"
