"""
Solomon Bridge API Server
Allows GPT to safely read, edit, and commit Solomon's files via REST API
"""

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import time
import subprocess
import re
from pathlib import Path
import difflib

# Configuration
BEARER_TOKEN = "pala"
SOLOMON_ROOT = Path("S:/Solomon")
BRANCH_NAME = "mirror"
VENV_PATH = SOLOMON_ROOT / ".venv"
STATE_FILE = SOLOMON_ROOT / "state.json"
PORT = 8500

# Security
security = HTTPBearer()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Solomon Bridge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8600", "http://localhost:8600"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
 )


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify bearer token"""
    if credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials


def is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed scope"""
    try:
        resolved = path.resolve()
        return resolved.is_relative_to(SOLOMON_ROOT.resolve())
    except:
        return False


def log_audit(actor: str, action: str, target: str, ok: bool):
    """Append audit entry to state.json"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        else:
            state = {}
        
        if 'audit_log' not in state:
            state['audit_log'] = []
        
        state['audit_log'].append({
            "time": int(time.time()),
            "actor": actor,
            "action": action,
            "target": target,
            "ok": ok
        })
        
        # Keep last 100 entries
        state['audit_log'] = state['audit_log'][-100:]
        
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Audit log error: {e}")


# Request/Response Models

class ReadRequest(BaseModel):
    path: str


class SearchRequest(BaseModel):
    query: str
    include: List[str] = ["**/*.py"]
    exclude: List[str] = ["**/.venv/**", "**/__pycache__/**"]
    regex: bool = False


class ApplyPatchRequest(BaseModel):
    diff: str
    dry_run: bool = True


class RunRequest(BaseModel):
    cmd: str
    timeout_sec: int = 120
    cwd: str = "S:/Solomon"


class CommitPushRequest(BaseModel):
    message: str
    branch: str = "mirror"


class StateUpdateRequest(BaseModel):
    patch: Dict[str, Any]


# Endpoints

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "time": int(time.time()),
        "version": "1.0.0"
    }


@app.post("/fs/read")
async def fs_read(request: ReadRequest, token: str = Depends(verify_token)):
    """Read file contents and metadata"""
    try:
        # Resolve path
        if request.path.startswith("S:/") or request.path.startswith("S:\\"):
            file_path = Path(request.path)
        else:
            file_path = SOLOMON_ROOT / request.path
        
        # Security check
        if not is_path_allowed(file_path):
            raise HTTPException(status_code=403, detail="Path outside allowed scope")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Read file
        content = file_path.read_text(encoding='utf-8')
        stat = file_path.stat()
        
        log_audit("gpt", "read", str(file_path), True)
        
        return {
            "ok": True,
            "path": str(file_path),
            "content": content,
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "encoding": "utf-8"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log_audit("gpt", "read", request.path, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fs/search")
async def fs_search(request: SearchRequest, token: str = Depends(verify_token)):
    """Search for text in files"""
    try:
        results = []
        
        # Convert glob patterns to regex if needed
        if request.regex:
            pattern = re.compile(request.query)
        else:
            pattern = re.compile(re.escape(request.query))
        
        # Search files
        for include_pattern in request.include:
            for file_path in SOLOMON_ROOT.glob(include_pattern):
                # Check exclusions
                excluded = False
                for exclude_pattern in request.exclude:
                    if file_path.match(exclude_pattern):
                        excluded = True
                        break
                
                if excluded or not file_path.is_file():
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    matches = []
                    
                    for i, line in enumerate(content.split('\n'), 1):
                        if pattern.search(line):
                            matches.append({
                                "line": i,
                                "text": line.strip()
                            })
                    
                    if matches:
                        results.append({
                            "path": str(file_path.relative_to(SOLOMON_ROOT)),
                            "matches": matches[:10]  # Limit to 10 matches per file
                        })
                
                except:
                    continue
        
        log_audit("gpt", "search", request.query, True)
        
        return {
            "ok": True,
            "query": request.query,
            "results": results[:50]  # Limit to 50 files
        }
    
    except Exception as e:
        log_audit("gpt", "search", request.query, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ops/apply_patch")
async def ops_apply_patch(request: ApplyPatchRequest, token: str = Depends(verify_token)):
    """Apply unified diff patch"""
    try:
        # Parse diff to extract file path
        lines = request.diff.split('\n')
        target_file = None
        
        for line in lines:
            if line.startswith('---') or line.startswith('+++'):
                parts = line.split()
                if len(parts) >= 2:
                    path_str = parts[1].replace('a/', '').replace('b/', '')
                    if path_str != '/dev/null':
                        target_file = SOLOMON_ROOT / path_str
                        break
        
        if not target_file:
            raise HTTPException(status_code=400, detail="Could not extract file path from diff")
        
        # Security check
        if not is_path_allowed(target_file):
            raise HTTPException(status_code=403, detail="Path outside allowed scope")
        
        if request.dry_run:
            # Dry run - just validate
            log_audit("gpt", "apply_patch_dry_run", str(target_file), True)
            return {
                "ok": True,
                "dry_run": True,
                "target": str(target_file),
                "preview": "Patch would be applied (dry run mode)"
            }
        else:
            # Apply patch
            # Write diff to temp file
            diff_file = SOLOMON_ROOT / ".temp_patch.diff"
            diff_file.write_text(request.diff, encoding='utf-8')
            
            # Apply using git apply
            result = subprocess.run(
                ["git", "apply", str(diff_file)],
                cwd=str(SOLOMON_ROOT),
                capture_output=True,
                text=True
            )
            
            diff_file.unlink()  # Clean up
            
            if result.returncode != 0:
                log_audit("gpt", "apply_patch", str(target_file), False)
                raise HTTPException(status_code=400, detail=f"Patch failed: {result.stderr}")
            
            log_audit("gpt", "apply_patch", str(target_file), True)
            
            return {
                "ok": True,
                "dry_run": False,
                "target": str(target_file),
                "applied": True
            }
    
    except HTTPException:
        raise
    except Exception as e:
        log_audit("gpt", "apply_patch", "unknown", False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ops/run")
async def ops_run(request: RunRequest, token: str = Depends(verify_token)):
    """Run allowed commands"""
    # Allowlist of safe commands
    ALLOWED_COMMANDS = [
        "pytest", "python", "git status", "git log", "git diff",
        "dir", "ls", "cat", "type"
    ]
    
    # Check if command is allowed
    cmd_base = request.cmd.split()[0]
    if not any(request.cmd.startswith(allowed) for allowed in ALLOWED_COMMANDS):
        raise HTTPException(status_code=403, detail=f"Command not allowed: {cmd_base}")
    
    try:
        # Verify cwd is within scope
        cwd_path = Path(request.cwd)
        if not is_path_allowed(cwd_path):
            raise HTTPException(status_code=403, detail="Working directory outside allowed scope")
        
        # Run command
        result = subprocess.run(
            request.cmd,
            shell=True,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=request.timeout_sec
        )
        
        log_audit("gpt", "run", request.cmd, result.returncode == 0)
        
        return {
            "ok": True,
            "cmd": request.cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except subprocess.TimeoutExpired:
        log_audit("gpt", "run", request.cmd, False)
        raise HTTPException(status_code=408, detail="Command timeout")
    except Exception as e:
        log_audit("gpt", "run", request.cmd, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/commit_push")
async def git_commit_push(request: CommitPushRequest, token: str = Depends(verify_token)):
    """Commit and push changes to git"""
    try:
        # Add all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(SOLOMON_ROOT),
            check=True
        )
        
        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", request.message],
            cwd=str(SOLOMON_ROOT),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            raise HTTPException(status_code=400, detail=f"Commit failed: {result.stderr}")
        
        # Push
        subprocess.run(
            ["git", "push", "origin", request.branch],
            cwd=str(SOLOMON_ROOT),
            check=True,
            capture_output=True,
            text=True
        )
        
        log_audit("gpt", "commit_push", request.message, True)
        
        return {
            "ok": True,
            "message": request.message,
            "branch": request.branch,
            "committed": True,
            "pushed": True
        }
    
    except subprocess.CalledProcessError as e:
        log_audit("gpt", "commit_push", request.message, False)
        raise HTTPException(status_code=500, detail=f"Git operation failed: {e.stderr if hasattr(e, 'stderr') else str(e)}")
    except Exception as e:
        log_audit("gpt", "commit_push", request.message, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state/get")
async def state_get(token: str = Depends(verify_token)):
    """Get full state.json contents"""
    try:
        if not STATE_FILE.exists():
            return {"ok": True, "state": {}}
        
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        return {
            "ok": True,
            "state": state
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/state/update")
async def state_update(request: StateUpdateRequest, token: str = Depends(verify_token)):
    """Update state.json with shallow merge"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        else:
            state = {}
        
        # Shallow merge
        state.update(request.patch)
        
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        
        log_audit("gpt", "state_update", "state.json", True)
        
        return {
            "ok": True,
            "updated": True
        }
    
    except Exception as e:
        log_audit("gpt", "state_update", "state.json", False)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")


