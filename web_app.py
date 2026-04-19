import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from main.main import build_arg_parser, run as run_pipeline
from main.utils.progress import ProgressTracker

app = FastAPI(title="Support agent progress")
progress = ProgressTracker()
_run_task: Optional[asyncio.Task] = None
_run_lock = asyncio.Lock()

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/progress")
async def api_progress() -> dict:
    return await progress.snapshot()


@app.post("/api/run")
async def api_run() -> JSONResponse:
    global _run_task
    async with _run_lock:
        if _run_task and not _run_task.done():
            return JSONResponse({"ok": False, "message": "A run is already in progress."}, status_code=409)
        args = build_arg_parser().parse_args([])

        async def _job() -> None:
            await run_pipeline(args, progress=progress)

        _run_task = asyncio.create_task(_job())
    return JSONResponse({"ok": True})


@app.get("/api/run/status")
async def run_status() -> dict:
    if _run_task is None:
        return {"has_task": False, "done": True}
    return {"has_task": True, "done": _run_task.done()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
