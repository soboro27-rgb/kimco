from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import bcrypt
from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return templates.TemplateResponse("login.html", {"request": request, "error": "아이디 또는 비밀번호가 틀렸습니다."})
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["name"] = user.name
    request.session["role"] = user.role
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")
