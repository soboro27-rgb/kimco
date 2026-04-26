from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from pathlib import Path
from database import engine
import models
from routers import auth_router, main_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kim&co × Claude 리포트 플랫폼")
app.add_middleware(SessionMiddleware, secret_key="kimco-secret-2024")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth_router.router)
app.include_router(main_router.router)


@app.get("/")
def root(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")
