"""Serve the single-page GigShield UI from the project root."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["frontend"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_HTML = _PROJECT_ROOT / "gigshield_phase2.html"


@router.get("/")
def index():
    """Main website — enhanced UI with portal select and multilingual chatbot."""
    if not INDEX_HTML.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Missing {INDEX_HTML.name} in project root.")
    return FileResponse(INDEX_HTML, media_type="text/html")
