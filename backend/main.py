"""
Atelier backend. FastAPI serving:
- Static frontend (index.html, app.js, style.css)
- REST endpoints to list, create, start engagements and download deliverables
- WebSocket for live log streaming during a run
- Background worker that spawns `claude -p ...` subprocesses with CCR routing

Single-user, localhost only. No auth.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

load_dotenv()

# Determine mode: 'api' (with CCR routing) or 'pro' (Claude Code OAuth via `claude login`)
_api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
PLACEHOLDER_KEYS = {"", "sk-ant-votre-cle-ici", "your-key-here"}
MODE = "api" if _api_key and _api_key not in PLACEHOLDER_KEYS else "pro"

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace"
BACKLOG = WORKSPACE / "backlog"
ENGAGEMENTS = WORKSPACE / "engagements"
FRONTEND = ROOT / "frontend"
TEMPLATES_DIR = ROOT / "templates" / "missions"

STAGES_ORDER = ["backlog", "framing", "hunting", "analyzing", "synthesizing", "producing", "done", "error"]
STAGE_LABELS = {
    "backlog": "En attente de lancement",
    "framing": "Cadrage et plan de travail",
    "hunting": "Collecte des données",
    "analyzing": "Analyse quantitative",
    "synthesizing": "Rédaction de la synthèse",
    "producing": "Production des livrables",
    "done": "Terminée",
    "error": "Erreur, à relancer",
}
ALLOWED_UPLOAD_EXT = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".pptx", ".ppt", ".json", ".xml", ".html",
}
MAX_UPLOAD_MB = 25

app = FastAPI(title="Atelier", version="2.0.0")


# ----- Event bus (in-memory, single-process) ----------------------------------


class Bus:
    def __init__(self) -> None:
        self.subscribers: dict[str, list[asyncio.Queue]] = {}

    async def publish(self, slug: str, event: dict) -> None:
        for q in list(self.subscribers.get(slug, [])):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe(self, slug: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self.subscribers.setdefault(slug, []).append(q)
        return q

    def unsubscribe(self, slug: str, q: asyncio.Queue) -> None:
        if slug in self.subscribers:
            try:
                self.subscribers[slug].remove(q)
            except ValueError:
                pass


bus = Bus()

# Track running engagements to prevent double-start
_running: set[str] = set()

# Map slug -> active asyncio.subprocess process (for stop endpoint)
_processes: dict[str, asyncio.subprocess.Process] = {}

# CCR subprocess handle (populated at startup in api mode when ccr is available)
_ccr_proc: Optional[subprocess.Popen] = None


# ----- CCR management (API mode only) ----------------------------------------


def _start_ccr_if_needed() -> None:
    """In API mode: mirror .ccr/config.json to the home dir and spawn `ccr start`."""
    global _ccr_proc
    if MODE != "api":
        return
    if shutil.which("ccr") is None:
        print(
            "[atelier] WARNING: ANTHROPIC_API_KEY is set but `ccr` CLI is not installed. "
            "Install it with: npm install -g @musistudio/claude-code-router. "
            "Falling back to direct Anthropic API calls (no model routing)."
        )
        return
    try:
        home_ccr = Path.home() / ".claude-code-router"
        home_ccr.mkdir(parents=True, exist_ok=True)
        src_cfg = ROOT / ".ccr" / "config.json"
        if src_cfg.exists():
            shutil.copy(str(src_cfg), str(home_ccr / "config.json"))
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        _ccr_proc = subprocess.Popen(
            ["ccr", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
            creationflags=creationflags,
        )
        print(f"[atelier] CCR started (pid={_ccr_proc.pid}, port 3456)")
    except Exception as e:
        print(f"[atelier] CCR start failed: {type(e).__name__}: {e}")


def _stop_ccr() -> None:
    global _ccr_proc
    if _ccr_proc is None:
        return
    try:
        _ccr_proc.terminate()
        try:
            _ccr_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _ccr_proc.kill()
    except Exception:
        pass
    _ccr_proc = None


def _ensure_folder_trusted() -> None:
    """Mark this project folder as trusted in ~/.claude.json so Claude Code
    accepts the permissions declared in .claude/settings.json. Avoids forcing
    the user through the interactive trust dialog."""
    claude_json = Path.home() / ".claude.json"
    # Build the exact key Claude Code uses: forward-slash absolute path.
    folder_key = str(ROOT).replace("\\", "/")
    try:
        data: dict = {}
        if claude_json.exists():
            try:
                data = json.loads(claude_json.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
            except json.JSONDecodeError:
                data = {}
        projects = data.setdefault("projects", {})
        if not isinstance(projects, dict):
            projects = {}
            data["projects"] = projects
        entry = projects.setdefault(folder_key, {})
        if not isinstance(entry, dict):
            entry = {}
            projects[folder_key] = entry
        if not entry.get("hasTrustDialogAccepted"):
            entry["hasTrustDialogAccepted"] = True
            claude_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[atelier] Marked folder as trusted in {claude_json}")
    except Exception as e:
        print(f"[atelier] Could not auto-trust folder: {type(e).__name__}: {e}")
        print(f"[atelier] You may need to run `claude` once in the folder and accept the trust dialog.")


@app.on_event("startup")
async def _on_startup() -> None:
    ensure_dirs()
    _ensure_folder_trusted()
    print(f"[atelier] Mode: {MODE}")
    if MODE == "api":
        _start_ccr_if_needed()
    else:
        print("[atelier] Using Claude Code OAuth (Claude Pro). Run `claude login` once if not done.")


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    _stop_ccr()


# ----- Models ----------------------------------------------------------------


class NewEngagement(BaseModel):
    title: str = Field(..., min_length=4, max_length=200)
    brief: str = Field(..., min_length=20, max_length=20000)
    deliverables: list[str] = Field(default_factory=lambda: ["deck", "report"])
    mission_type: str = Field(default="market_study")
    speed_mode: str = Field(default="standard")  # express | standard | deep
    form_data: dict = Field(default_factory=dict)


class RevisionRequest(BaseModel):
    instructions: str = Field(..., min_length=5, max_length=4000)


# ----- Mission templates -----------------------------------------------------


def load_mission_templates() -> list[dict]:
    """Load all YAML mission templates. Safe to call repeatedly; cheap."""
    if yaml is None or not TEMPLATES_DIR.exists():
        return [_fallback_market_study_template()]
    templates: list[dict] = []
    for f in sorted(TEMPLATES_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("id"):
                templates.append(data)
        except Exception as e:
            print(f"[atelier] Skipping template {f.name}: {e}")
    if not templates:
        templates.append(_fallback_market_study_template())
    return templates


def _fallback_market_study_template() -> dict:
    return {
        "id": "market_study",
        "name": "Étude de marché",
        "short": "Cartographier un marché, dimensionner, projeter.",
        "icon": "chart",
        "color": "navy",
        "default_deliverables": ["deck", "report", "exec_summary"],
        "agents": ["framer", "hunter", "analyst", "synthesizer", "producer"],
    }


def get_template(mission_id: str) -> dict:
    for t in load_mission_templates():
        if t.get("id") == mission_id:
            return t
    return _fallback_market_study_template()


# ----- Helpers ---------------------------------------------------------------


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:60] or "untitled"


def ensure_dirs() -> None:
    for d in [BACKLOG, ENGAGEMENTS, WORKSPACE / "decisions", WORKSPACE / "templates"]:
        d.mkdir(parents=True, exist_ok=True)


def extract_title(path: Path) -> str:
    if not path.exists():
        return "(untitled)"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
    except Exception:
        pass
    return path.stem


def detect_stage(folder: Path) -> str:
    """Infer current stage from which files exist in the engagement folder."""
    checks = [
        (folder / "06_deliverables", "done"),
        (folder / "05_synthesis.md", "producing"),
        (folder / "04_models", "synthesizing"),
        (folder / "03_charts", "synthesizing"),
        (folder / "02_data", "analyzing"),
        (folder / "01_workplan.md", "hunting"),
        (folder / "00_brief.md", "framing"),
    ]
    for path, stage in checks:
        if path.exists():
            if stage == "done":
                try:
                    if any(path.iterdir()):
                        return "done"
                except Exception:
                    pass
            else:
                return stage
    return "pending"


def list_deliverables(folder: Path) -> list[dict]:
    deliv_dir = folder / "06_deliverables"
    if not deliv_dir.exists():
        return []
    out: list[dict] = []
    for f in sorted(deliv_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            out.append({"name": f.name, "size": f.stat().st_size})
    return out


def read_engagement(slug: str) -> Optional[dict]:
    folder = ENGAGEMENTS / slug
    if not folder.exists() or not folder.is_dir():
        return None
    brief_path = folder / "00_brief.md"
    stage = detect_stage(folder)

    meta_path = folder / "_meta.json"
    meta: dict = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    attachments_dir = folder / "_attachments"
    attachments: list[dict] = []
    if attachments_dir.exists():
        for f in sorted(attachments_dir.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                attachments.append({"name": f.name, "size": f.stat().st_size})

    mission_type = meta.get("mission_type", "market_study")
    template = get_template(mission_type)

    return {
        "slug": slug,
        "title": extract_title(brief_path),
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, stage),
        "running": slug in _running,
        "created_at": datetime.fromtimestamp(folder.stat().st_ctime, timezone.utc).isoformat(),
        "deliverables": list_deliverables(folder),
        "attachments": attachments,
        "mission_type": mission_type,
        "mission_name": template.get("name", mission_type),
        "mission_icon": template.get("icon", "chart"),
        "mission_color": template.get("color", "navy"),
        "form_data": meta.get("form_data", {}),
    }


def now_hhmmss() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ----- REST endpoints --------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    """Report backend readiness: Claude Code presence, mode (pro OAuth or api+CCR), CCR status."""
    claude_ok = shutil.which("claude") is not None
    ccr_ok = shutil.which("ccr") is not None
    return {
        "status": "ok",
        "claude_cli_installed": claude_ok,
        "mode": MODE,
        "ccr_installed": ccr_ok,
        "ccr_running": _ccr_proc is not None and _ccr_proc.poll() is None,
    }


@app.get("/api/missions")
async def list_missions() -> dict:
    """Return the catalog of mission templates available on this install."""
    return {"missions": load_mission_templates()}


@app.get("/api/engagements")
async def list_engagements() -> dict:
    ensure_dirs()
    engagements: list[dict] = []
    for folder in sorted(ENGAGEMENTS.iterdir(), reverse=True):
        if folder.is_dir() and folder.name != ".gitkeep":
            e = read_engagement(folder.name)
            if e:
                engagements.append(e)
    backlog: list[dict] = []
    for f in sorted(BACKLOG.glob("*.md")):
        slug = f.stem
        # If a folder already exists for this slug, we can read mission metadata
        meta_mission_name = "Étude"
        meta_mission_type = "market_study"
        meta_folder = ENGAGEMENTS / slug
        if meta_folder.exists():
            meta_path = meta_folder / "_meta.json"
            if meta_path.exists():
                try:
                    md = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta_mission_type = md.get("mission_type", meta_mission_type)
                    meta_mission_name = md.get("mission_name", meta_mission_name)
                except Exception:
                    pass
        backlog.append(
            {
                "slug": slug,
                "title": extract_title(f),
                "stage": "backlog",
                "stage_label": STAGE_LABELS["backlog"],
                "running": False,
                "mission_type": meta_mission_type,
                "mission_name": meta_mission_name,
            }
        )
    return {"engagements": engagements, "backlog": backlog}


@app.post("/api/engagements", status_code=201)
async def create_engagement(payload: NewEngagement) -> dict:
    ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")
    slug = f"{today}_{slugify(payload.title)}"
    brief_file = BACKLOG / f"{slug}.md"
    if brief_file.exists() or (ENGAGEMENTS / slug).exists():
        raise HTTPException(409, "An engagement with this slug already exists")

    template = get_template(payload.mission_type)

    form_block = ""
    if payload.form_data:
        form_block = "\n## Paramètres de mission\n\n"
        for k, v in payload.form_data.items():
            if v:
                form_block += f"- **{k}**: {v}\n"

    # Enrich brief with speed_mode constraints from template
    speed_block = ""
    sm = (template.get("speed_modes") or {}).get(payload.speed_mode)
    if sm:
        constraints = ", ".join(f"{k}={v}" for k, v in sm.items())
        speed_block = f"\n**Speed mode**: `{payload.speed_mode}` ({constraints})\n"

    body = f"""# {payload.title}

**Mission type**: {template.get("name", payload.mission_type)}  (`{payload.mission_type}`)
**Deliverables requested**: {", ".join(payload.deliverables)}
{speed_block}{form_block}
## Brief

{payload.brief}
"""
    brief_file.write_text(body, encoding="utf-8")
    # Preallocate engagement folder so uploads can land before start
    engagement_folder = ENGAGEMENTS / slug
    engagement_folder.mkdir(parents=True, exist_ok=True)
    (engagement_folder / "_attachments").mkdir(exist_ok=True)
    # Save mission metadata for the UI
    meta = {
        "slug": slug,
        "mission_type": payload.mission_type,
        "mission_name": template.get("name", payload.mission_type),
        "deliverables": payload.deliverables,
        "speed_mode": payload.speed_mode,
        "form_data": payload.form_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (engagement_folder / "_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"slug": slug, "stage": "backlog", "mission": template}


@app.post("/api/engagements/{slug}/attachments", status_code=201)
async def upload_attachments(slug: str, files: list[UploadFile] = File(...)) -> dict:
    """Accept one or more file uploads for an engagement, stored under _attachments/."""
    engagement_folder = ENGAGEMENTS / slug
    if not engagement_folder.exists():
        raise HTTPException(404, "Engagement folder not found. Create the engagement first.")
    attachments_dir = engagement_folder / "_attachments"
    attachments_dir.mkdir(exist_ok=True)
    saved: list[dict] = []
    rejected: list[dict] = []
    for upload in files:
        safe_name = Path(upload.filename or "upload.bin").name
        ext = Path(safe_name).suffix.lower()
        if ext not in ALLOWED_UPLOAD_EXT:
            rejected.append({"name": safe_name, "reason": f"extension {ext} non autorisée"})
            continue
        target = attachments_dir / safe_name
        counter = 1
        while target.exists():
            target = attachments_dir / f"{Path(safe_name).stem}_{counter}{ext}"
            counter += 1
        try:
            content = await upload.read()
            if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
                rejected.append({"name": safe_name, "reason": f"fichier > {MAX_UPLOAD_MB} MB"})
                continue
            target.write_bytes(content)
            saved.append({"name": target.name, "size": len(content)})
        except Exception as e:
            rejected.append({"name": safe_name, "reason": f"{type(e).__name__}: {e}"})
    return {"saved": saved, "rejected": rejected}


@app.get("/api/engagements/{slug}/attachments")
async def list_attachments(slug: str) -> dict:
    engagement_folder = ENGAGEMENTS / slug
    if not engagement_folder.exists():
        raise HTTPException(404, "Engagement not found")
    attachments_dir = engagement_folder / "_attachments"
    if not attachments_dir.exists():
        return {"attachments": []}
    files: list[dict] = []
    for f in sorted(attachments_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            files.append({"name": f.name, "size": f.stat().st_size})
    return {"attachments": files}


@app.delete("/api/engagements/{slug}/attachments/{filename}")
async def delete_attachment(slug: str, filename: str) -> dict:
    engagement_folder = ENGAGEMENTS / slug
    safe_name = Path(filename).name
    path = engagement_folder / "_attachments" / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Attachment not found")
    try:
        path.unlink()
    except Exception as e:
        raise HTTPException(500, f"Could not delete: {e}")
    return {"deleted": safe_name}


@app.post("/api/engagements/{slug}/start")
async def start_engagement(slug: str) -> dict:
    brief_file = BACKLOG / f"{slug}.md"
    engagement_folder = ENGAGEMENTS / slug

    if slug in _running:
        raise HTTPException(409, "Engagement already running")

    if brief_file.exists():
        engagement_folder.mkdir(parents=True, exist_ok=True)
        target = engagement_folder / "00_brief.md"
        if not target.exists():
            shutil.copy(str(brief_file), str(target))
        try:
            brief_file.unlink()
        except Exception:
            pass
    elif not engagement_folder.exists():
        raise HTTPException(404, "No brief found for this slug (not in backlog, not in engagements)")

    asyncio.create_task(_run_engagement(slug))
    return {"slug": slug, "status": "running"}


@app.post("/api/engagements/{slug}/stop")
async def stop_engagement(slug: str) -> dict:
    """Terminate the running Chief process for this engagement.
    Deliverables already written to disk remain. The user can relaunch and
    the Chief resumes from where it stopped (reads the existing files)."""
    if slug not in _running:
        raise HTTPException(409, "Engagement is not running")
    proc = _processes.get(slug)
    if proc is None:
        _running.discard(slug)
        return {"slug": slug, "status": "stopped", "note": "process already gone"}
    try:
        # On Windows, terminate the shell wrapper; the child claude.cmd will exit too.
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception as e:
        return {"slug": slug, "status": "stop_error", "error": str(e)}
    await bus.publish(slug, {"type": "warn", "msg": "Étude arrêtée par l'utilisateur", "ts": datetime.now().strftime("%H:%M:%S")})
    return {"slug": slug, "status": "stopped"}


@app.post("/api/engagements/{slug}/revise")
async def request_revision(slug: str, payload: RevisionRequest) -> dict:
    """User requests a revision of a completed engagement. Writes a revision
    file that the Chief will pick up on next start."""
    engagement_folder = ENGAGEMENTS / slug
    if not engagement_folder.exists():
        raise HTTPException(404, "Engagement not found")
    if slug in _running:
        raise HTTPException(409, "Engagement is already running. Wait for completion before revising.")
    revision_path = engagement_folder / "_revision_request.md"
    ts = datetime.now(timezone.utc).isoformat()
    body = f"""# Demande de révision

**Date**: {ts}

## Instructions

{payload.instructions}

## Consigne au Chief

Analysez le livrable produit et appliquez les révisions demandées ci-dessus.
Dispatchez les rerolls appropriés (writer, synthesizer, producer selon ce qui est demandé),
puis repassez partner_review pour validation finale.
"""
    revision_path.write_text(body, encoding="utf-8")
    # Trigger a run
    asyncio.create_task(_run_engagement(slug))
    return {"slug": slug, "status": "revising"}


@app.get("/api/engagements/{slug}")
async def get_engagement(slug: str) -> dict:
    e = read_engagement(slug)
    if e is None:
        bl = BACKLOG / f"{slug}.md"
        if bl.exists():
            return {
                "slug": slug,
                "title": extract_title(bl),
                "stage": "backlog",
                "running": False,
                "deliverables": [],
                "log": "",
            }
        raise HTTPException(404, "Engagement not found")
    log_path = ENGAGEMENTS / slug / "_log.md"
    e["log"] = (
        log_path.read_text(encoding="utf-8", errors="replace")[-20000:] if log_path.exists() else ""
    )
    return e


@app.get("/api/engagements/{slug}/file/{filename}")
async def download_deliverable(slug: str, filename: str):
    safe_name = Path(filename).name  # strip any path components
    path = ENGAGEMENTS / slug / "06_deliverables" / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path), filename=safe_name)


# ----- WebSocket -------------------------------------------------------------


@app.websocket("/ws/engagements/{slug}")
async def stream_engagement(ws: WebSocket, slug: str) -> None:
    await ws.accept()
    q = bus.subscribe(slug)
    try:
        await ws.send_json({"type": "connected", "slug": slug, "ts": now_hhmmss()})
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bus.unsubscribe(slug, q)


# ----- Agent runner ----------------------------------------------------------


async def _run_engagement(slug: str) -> None:
    """Spawn `claude -p ...` for the Chief orchestrator. Stream output via bus."""
    _running.add(slug)
    folder = ENGAGEMENTS / slug
    log_path = folder / "_log.md"
    log_path.touch()

    # Shared mutable counters so the heartbeat task can report real activity.
    stats = {"lines": 0, "tool_calls": 0, "last_activity": datetime.now()}

    async def emit(kind: str, msg: str, extra: Optional[dict] = None) -> None:
        event = {"type": kind, "msg": msg, "ts": now_hhmmss()}
        if extra:
            event.update(extra)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{event['ts']}] {kind}: {msg}\n")
        await bus.publish(slug, event)

    await emit("info", f"Chief started on engagement '{slug}'")
    await emit("info", "Spawning Claude Code CLI (first response can take 10-30s)...")

    # Build a context-rich prompt: read mission type and route to right agents
    meta_file = folder / "_meta.json"
    revision_file = folder / "_revision_request.md"
    mission_hint = ""
    speed_hint = ""
    if meta_file.exists():
        try:
            md = json.loads(meta_file.read_text(encoding="utf-8"))
            mt = md.get("mission_type", "market_study")
            sm = md.get("speed_mode", "standard")
            mission_hint = (
                f"\nMission type: `{mt}`. Read `templates/missions/{mt}.yaml` first to confirm "
                f"the agent sequence and scope constraints for this mission."
            )
            speed_hint = (
                f"\nSpeed mode: `{sm}`. Apply the corresponding scope caps from the template "
                f"(max_hypotheses, max_datapoints, max_slides, etc.). Transmit these caps to each subagent in its prompt."
            )
        except Exception:
            pass

    revision_hint = ""
    if revision_file.exists():
        revision_hint = (
            "\n\n**REVISION MODE**: a `_revision_request.md` file is present. Read it first. "
            "Identify which outputs need to change, dispatch targeted rerolls (not the full pipeline), "
            "then re-run partner_review for final approval."
        )

    prompt = f"""You are the Chief orchestrator for Atelier.

Engagement at `workspace/engagements/{slug}/00_brief.md`.{mission_hint}{speed_hint}{revision_hint}

Follow the workflow in CLAUDE.md: delegate SYNCHRONOUSLY to each agent in the sequence
defined by the mission template. Validate each stage output before dispatching the next.
Always finish with partner_review. If partner_review requests rerolls, execute them and loop.

Log all your decisions to `workspace/decisions/`.

Start now."""

    # Resolve the full path to the `claude` binary. On Windows the npm global shim
    # is `claude.cmd`, and asyncio.create_subprocess_exec will NOT auto-resolve
    # extensions the way the shell does. We also fall back to running via the
    # shell on Windows, so .cmd/.ps1 shims execute correctly.
    claude_path = shutil.which("claude")
    if claude_path is None:
        await emit(
            "error",
            "'claude' CLI not found in PATH. Install with: npm install -g @anthropic-ai/claude-code",
        )
        _running.discard(slug)
        return

    # Pick the model via standard Claude Code CLI aliases: 'sonnet' or 'opus'
    # or 'haiku'. The ATELIER_MODEL env var lets the user override from .env.
    # Default is 'sonnet' to save Pro quota compared to Opus 5.5.
    model_alias = os.environ.get("ATELIER_MODEL", "sonnet").strip() or "sonnet"
    cli_args = [
        "-p",
        prompt,
        "--model",
        model_alias,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "acceptEdits",
    ]

    env = os.environ.copy()
    # Route via CCR only when API mode is active AND CCR is actually running.
    # In Pro mode, let Claude Code hit the Pro OAuth backend directly.
    if MODE == "api" and _ccr_proc is not None:
        env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:3456"
    # Keep stream line-buffered for live log, no color codes.
    env["NODE_NO_READLINE"] = "1"
    env["FORCE_COLOR"] = "0"
    env["NO_COLOR"] = "1"
    env["CI"] = "1"
    # CRITICAL: wait indefinitely for background subagent tasks instead of
    # killing them after the default 10 minutes. Without this, long-running
    # steps like the Hunter get cut mid-work. We also instruct the Chief in
    # CLAUDE.md to prefer synchronous dispatch, but this is the belt-and-braces.
    env["CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS"] = "0"

    # Also write raw CLI output verbatim to a debug file, as ground truth.
    raw_log = folder / "_raw_claude.log"
    await emit("info", f"Raw CLI output will be written to {raw_log.name} for debugging")

    try:
        if os.name == "nt":
            # Windows: invoke cmd.exe /c <claude.cmd> directly via create_subprocess_exec.
            # Avoiding create_subprocess_shell dodges a double-cmd layer that
            # sometimes blocks stdout flushing.
            proc = await asyncio.create_subprocess_exec(
                "cmd.exe",
                "/c",
                claude_path,
                *cli_args,
                cwd=str(ROOT),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                claude_path,
                *cli_args,
                cwd=str(ROOT),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
    except FileNotFoundError:
        await emit(
            "error",
            f"Could not spawn '{claude_path}'. Try reinstalling: npm install -g @anthropic-ai/claude-code",
        )
        _running.discard(slug)
        return
    except Exception as e:
        await emit("error", f"Failed to spawn claude: {type(e).__name__}: {e}")
        _running.discard(slug)
        return

    await emit("info", f"Spawned pid={proc.pid}. Tailing _log.md for Chief activity (stdout is unreliable on Windows cmd shims)...")
    _processes[slug] = proc

    # STRATEGY: On Windows, Node.js stdout from .cmd shims is often fully
    # buffered and only released at process exit, which defeats live streaming.
    # Instead, we treat the engagement's own _log.md as source of truth: the
    # Chief writes there (CLAUDE.md instructs it to), and we tail new lines.
    # We also still drain stdout to the raw log so we have a fallback for debug.

    assert proc.stdout is not None

    # Task 1: drain stdout silently into raw file (so pipe doesn't fill up and block Claude)
    async def _drain_stdout() -> None:
        try:
            with raw_log.open("ab") as raw_fp:
                raw_fp.write(f"\n===== RUN {datetime.now().isoformat()} =====\n".encode("utf-8"))
                raw_fp.flush()
                async for raw in proc.stdout:
                    raw_fp.write(raw)
                    raw_fp.flush()
                    text = raw.decode("utf-8", errors="replace").rstrip()
                    if text:
                        stats["lines"] += 1
                        stats["last_activity"] = datetime.now()
        except Exception:
            pass

    # Task 2: tail _log.md for new lines written by the Chief itself
    async def _tail_log() -> None:
        try:
            offset = log_path.stat().st_size if log_path.exists() else 0
        except Exception:
            offset = 0
        last_seen_lines = 0
        while True:
            await asyncio.sleep(1.5)
            if proc.returncode is not None:
                # One final read to catch tail-end entries
                try:
                    if log_path.exists():
                        with log_path.open("r", encoding="utf-8", errors="replace") as f:
                            f.seek(offset)
                            new = f.read()
                            offset = f.tell()
                            for line in new.splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                await _emit_chief_line(line)
                                stats["tool_calls"] += 1
                except Exception:
                    pass
                return
            try:
                if not log_path.exists():
                    continue
                size = log_path.stat().st_size
                if size <= offset:
                    continue
                with log_path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(offset)
                    new = f.read()
                    offset = f.tell()
                for line in new.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    await _emit_chief_line(line)
                    stats["last_activity"] = datetime.now()
            except Exception:
                pass

    async def _emit_chief_line(raw_line: str) -> None:
        # Lines appended by _log.md by both us and the Chief look like
        # "[hh:mm:ss] kind: message". We only forward Chief lines (not our own,
        # to avoid echo). Our emit() writes with our ts; the Chief typically
        # writes with its own format which doesn't start with "[hh:mm:ss] <kind>:"
        # followed by one of our kinds. So we forward anything we haven't just
        # produced in the last 2s.
        event = {"type": "chief_log", "msg": raw_line, "ts": now_hhmmss()}
        await bus.publish(slug, event)

    # Task 3: heartbeat
    async def _heartbeat() -> None:
        while True:
            await asyncio.sleep(20)
            if proc.returncode is not None:
                return
            idle = (datetime.now() - stats["last_activity"]).total_seconds()
            if idle >= 20:
                await emit(
                    "info",
                    f"Chief still running (pid {proc.pid}) - no activity in {int(idle)}s. This is normal during long tool calls.",
                )

    drain_task = asyncio.create_task(_drain_stdout())
    tail_task = asyncio.create_task(_tail_log())
    hb_task = asyncio.create_task(_heartbeat())

    try:
        rc = await proc.wait()
        # Give the tail task a moment to catch final writes
        await asyncio.sleep(2)
        tail_task.cancel()
        hb_task.cancel()
        drain_task.cancel()

        # Scan the engagement folder to report actual deliverables produced vs expected.
        produced: list[str] = []
        missing: list[str] = []
        checks = [
            ("01_workplan.md", folder / "01_workplan.md"),
            ("02_data/sources.json", folder / "02_data" / "sources.json"),
            ("03_charts/", folder / "03_charts"),
            ("05_synthesis.md", folder / "05_synthesis.md"),
            ("06_deliverables/", folder / "06_deliverables"),
        ]
        for label, path in checks:
            if path.exists():
                if path.is_dir():
                    try:
                        if any(path.iterdir()):
                            produced.append(label)
                        else:
                            missing.append(label + " (empty)")
                    except Exception:
                        missing.append(label)
                else:
                    produced.append(label)
            else:
                missing.append(label)

        summary = f"produced: {', '.join(produced) if produced else 'nothing'}"
        if missing:
            summary += f" | missing: {', '.join(missing)}"

        if rc == 0 and not missing:
            await emit("done", f"Chief finished successfully. {summary}", {"code": rc})
        elif rc == 0 and missing:
            await emit(
                "warn",
                f"Chief exited rc=0 but workflow INCOMPLETE. {summary}. "
                f"Click Lancer again: Chief will resume from where it stopped.",
                {"code": rc},
            )
        else:
            await emit("error", f"Chief exited rc={rc}. {summary}. See {raw_log.name} for details.", {"code": rc})
    except Exception as e:
        for t in (drain_task, tail_task, hb_task):
            t.cancel()
        await emit("error", f"Runner error: {type(e).__name__}: {e}")
    finally:
        _running.discard(slug)
        _processes.pop(slug, None)


def _win_quote(arg: str) -> str:
    """Quote an argument for Windows cmd.exe. Wraps in double quotes and escapes
    inner double quotes by doubling them."""
    if not arg:
        return '""'
    if any(c in arg for c in ' \t"\n'):
        return '"' + arg.replace('"', '""') + '"'
    return arg


def _format_stream_line(line: str) -> tuple[str, bool]:
    """Best-effort pretty format of claude CLI stream-json lines.
    Returns (formatted_message, is_tool_call)."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return (line[:500], False)

    t = data.get("type", "?")

    if t == "assistant":
        content = (data.get("message") or {}).get("content", [])
        parts: list[str] = []
        is_tool = False
        for block in content:
            btype = block.get("type")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text[:400])
            elif btype == "tool_use":
                is_tool = True
                name = block.get("name", "?")
                inp = block.get("input") or {}
                # Highlight sub-agent calls specially
                if name == "Task":
                    agent = inp.get("subagent_type") or inp.get("agent_type") or "?"
                    desc = inp.get("description", "")[:80]
                    parts.append(f"-> DELEGATES to {agent}: {desc}")
                else:
                    args = ""
                    if "file_path" in inp:
                        args = f" {inp['file_path']}"
                    elif "command" in inp:
                        args = f" {str(inp['command'])[:80]}"
                    elif "query" in inp:
                        args = f" query='{str(inp['query'])[:60]}'"
                    elif "url" in inp:
                        args = f" {inp['url']}"
                    elif "pattern" in inp:
                        args = f" pattern='{inp['pattern']}'"
                    parts.append(f"tool: {name}{args}")
        msg = " | ".join(parts) if parts else "(thinking)"
        return (f"[chief] {msg}", is_tool)

    if t == "user":
        content = (data.get("message") or {}).get("content", [])
        for block in content:
            if block.get("type") == "tool_result":
                payload = block.get("content", "")
                if isinstance(payload, list):
                    payload = " ".join(str(p.get("text", p)) for p in payload)
                is_error = block.get("is_error", False)
                prefix = "[result-error]" if is_error else "[result]"
                return (f"{prefix} {str(payload)[:300]}", False)
        return ("[user turn]", False)

    if t == "system":
        sub = data.get("subtype", "")
        session_id = data.get("session_id", "")[:8]
        tools = data.get("tools", [])
        tool_count = len(tools) if isinstance(tools, list) else 0
        if sub == "init":
            return (f"[system] session={session_id} with {tool_count} tools available", False)
        return (f"[system] {sub}", False)

    if t == "result":
        duration = data.get("duration_ms", 0) / 1000.0
        cost = data.get("total_cost_usd", 0)
        turns = data.get("num_turns", 0)
        return (f"[end] {turns} turns, {duration:.1f}s, ${cost:.4f}", False)

    return (f"[{t}]", False)


# ----- Static frontend -------------------------------------------------------


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(FRONTEND / "index.html"))


@app.get("/app.js")
async def app_js() -> FileResponse:
    return FileResponse(str(FRONTEND / "app.js"), media_type="application/javascript")


@app.get("/style.css")
async def style_css() -> FileResponse:
    return FileResponse(str(FRONTEND / "style.css"), media_type="text/css")


# ----- Entry point -----------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    ensure_dirs()
    uvicorn.run(app, host="127.0.0.1", port=7777)
