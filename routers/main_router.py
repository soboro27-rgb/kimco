from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
from claude_service import generate_report
import pdfplumber
import docx
import io

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PROMPTS = {
    "tax": {
        "label": "세무 (Tax Return)",
        "prompt": "당신은 미국 공인회계사(CPA)입니다. 아래 고객 자료를 바탕으로 세무 분석 리포트를 작성해주세요. 주요 세무 이슈, 절세 포인트, 주의사항을 포함해주세요.\n\n[고객 자료]\n{input_data}"
    },
    "financial": {
        "label": "재무분석 (Financial Analysis)",
        "prompt": "당신은 미국 공인회계사(CPA)입니다. 아래 재무 자료를 분석하여 재무상태, 수익성, 유동성, 주요 리스크를 포함한 재무분석 리포트를 작성해주세요.\n\n[고객 자료]\n{input_data}"
    },
    "consulting": {
        "label": "비즈니스 컨설팅 (Consulting)",
        "prompt": "당신은 미국 공인회계사(CPA)이자 비즈니스 컨설턴트입니다. 아래 내용을 바탕으로 비즈니스 개선 방안과 전략적 제언을 포함한 컨설팅 리포트를 작성해주세요.\n\n[고객 자료]\n{input_data}"
    },
    "custom": {
        "label": "복합·기타 (Custom)",
        "prompt": "당신은 미국 공인회계사(CPA)입니다. 아래 고객 요청 사항을 검토하고 전문적인 분석과 제언을 포함한 리포트를 작성해주세요.\n\n[고객 자료]\n{input_data}"
    }
}


async def extract_text_from_file(file: UploadFile) -> str:
    content = await file.read()
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    return ""


def require_login(request: Request):
    return bool(request.session.get("user_id"))


def is_superadmin(request: Request):
    return request.session.get("role") == "superadmin"


# ── 대시보드 ──────────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login")

    if is_superadmin(request):
        reports = db.query(models.Report).order_by(models.Report.created_at.desc()).all()
        clients = db.query(models.Client).all()
        admins = db.query(models.User).filter(models.User.role == "admin").all()
        pending = [r for r in reports if r.status == "submitted"]
    else:
        uid = request.session["user_id"]
        reports = db.query(models.Report).filter(models.Report.user_id == uid).order_by(models.Report.created_at.desc()).all()
        clients = db.query(models.Client).filter(models.Client.user_id == uid).all()
        admins = []
        pending = []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "reports": reports,
        "clients": clients,
        "admins": admins,
        "pending": pending,
        "prompts": PROMPTS
    })


# ── 리포트 생성 ───────────────────────────────────────────
@router.get("/report/new", response_class=HTMLResponse)
def new_report_page(request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login")
    uid = request.session["user_id"]
    if is_superadmin(request):
        clients = db.query(models.Client).all()
    else:
        clients = db.query(models.Client).filter(models.Client.user_id == uid).all()
    return templates.TemplateResponse("new_report.html", {
        "request": request,
        "clients": clients,
        "prompts": PROMPTS
    })


@router.post("/report/new")
async def create_report(
    request: Request,
    client_id: int = Form(...),
    report_type: str = Form(...),
    input_data: str = Form(""),
    order_prompts: Optional[List[str]] = Form(None),
    upload_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if not require_login(request):
        return RedirectResponse("/login")

    file_text = ""
    if upload_file and upload_file.filename:
        file_text = await extract_text_from_file(upload_file)

    combined_data = input_data.strip()
    if file_text.strip():
        combined_data += ("\n\n" if combined_data else "") + f"[업로드 파일: {upload_file.filename}]\n{file_text}"

    prompt_template = PROMPTS[report_type]["prompt"]
    full_prompt = prompt_template.replace("{input_data}", combined_data)

    if order_prompts:
        extra = "\n".join([p.strip() for p in order_prompts if p.strip()])
        if extra:
            full_prompt += f"\n\n[추가 지시사항]\n{extra}"

    result = await generate_report(full_prompt, api_key=request.session.get("claude_api_key"))

    report = models.Report(
        client_id=client_id,
        user_id=request.session["user_id"],
        report_type=report_type,
        input_data=combined_data,
        prompt_used=full_prompt,
        result=result,
        status="draft"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return RedirectResponse(f"/report/{report.id}", status_code=302)


# ── 리포트 상세 ───────────────────────────────────────────
@router.get("/report/{report_id}", response_class=HTMLResponse)
def view_report(report_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login")
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        return RedirectResponse("/dashboard")
    if not is_superadmin(request) and report.user_id != request.session["user_id"]:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("view_report.html", {
        "request": request,
        "report": report,
        "prompts": PROMPTS
    })


# ── 승인 요청 (관리자 → 통합관리자) ──────────────────────
@router.post("/report/{report_id}/submit")
def submit_report(report_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login")
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if report and report.user_id == request.session["user_id"] and report.status == "draft":
        report.status = "submitted"
        db.commit()
    return RedirectResponse(f"/report/{report_id}", status_code=302)


# ── 승인 (통합관리자) ─────────────────────────────────────
@router.post("/report/{report_id}/approve")
def approve_report(report_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_superadmin(request):
        return RedirectResponse("/dashboard")
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if report:
        report.status = "approved"
        report.reject_reason = None
        db.commit()
    return RedirectResponse(f"/report/{report_id}", status_code=302)


# ── 반려 (통합관리자) ─────────────────────────────────────
@router.post("/report/{report_id}/reject")
def reject_report(
    report_id: int,
    request: Request,
    reject_reason: str = Form(""),
    db: Session = Depends(get_db)
):
    if not is_superadmin(request):
        return RedirectResponse("/dashboard")
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if report:
        report.status = "rejected"
        report.reject_reason = reject_reason
        db.commit()
    return RedirectResponse(f"/report/{report_id}", status_code=302)


# ── Claude API 키 설정 ────────────────────────────────────
@router.post("/settings/api-key")
async def save_api_key(request: Request, api_key: str = Form(...)):
    if not require_login(request):
        return RedirectResponse("/login")
    stripped = api_key.strip()
    if stripped:
        request.session["claude_api_key"] = stripped
    return RedirectResponse("/dashboard", status_code=302)


@router.post("/settings/api-key/remove")
async def remove_api_key(request: Request):
    if not require_login(request):
        return RedirectResponse("/login")
    request.session.pop("claude_api_key", None)
    return RedirectResponse("/dashboard", status_code=302)


# ── 고객 등록 ─────────────────────────────────────────────
@router.get("/client/new", response_class=HTMLResponse)
def new_client_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("new_client.html", {"request": request})


@router.post("/client/new")
def create_client(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(...),
    memo: str = Form(""),
    db: Session = Depends(get_db)
):
    if not require_login(request):
        return RedirectResponse("/login")
    client = models.Client(
        user_id=request.session["user_id"],
        name=name, email=email, company=company, memo=memo
    )
    db.add(client)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)


# ── 담당자 목록 (통합관리자 전용) ────────────────────────
@router.get("/admins", response_class=HTMLResponse)
def admin_list(request: Request, db: Session = Depends(get_db)):
    if not is_superadmin(request):
        return RedirectResponse("/dashboard")
    admins = db.query(models.User).filter(models.User.role == "admin").order_by(models.User.created_at.desc()).all()
    return templates.TemplateResponse("admin_list.html", {"request": request, "admins": admins})


# ── 담당자 계정 생성 (통합관리자 전용) ───────────────────
@router.post("/admin/new")
def create_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    if not is_superadmin(request):
        return RedirectResponse("/dashboard")
    import bcrypt
    admins = db.query(models.User).filter(models.User.role == "admin").order_by(models.User.created_at.desc()).all()
    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse("admin_list.html", {"request": request, "admins": admins, "error": "이미 존재하는 아이디입니다."})
    pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.add(models.User(username=username, password_hash=pw, name=name, role="admin"))
    db.commit()
    return RedirectResponse("/admins", status_code=302)
