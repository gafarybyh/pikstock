"""routes_static.py — mount aset, index SPA, fallback 404 ke SPA."""

from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .context import GENERATE, WEB, app

app.mount("/generate", StaticFiles(directory=str(GENERATE)), name="generate")
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.exception_handler(404)
async def not_found(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "not found"}, status_code=404)
    return FileResponse(WEB / "index.html")
