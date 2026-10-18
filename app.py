import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.auth import (
    TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_email_from_token,
    hash_password,
    verify_password,
)
from src.db import Base, OtpChallenge, User, engine, get_db
from src.email_service import send_otp_email
from src.otp_codes import (
    generate_otp,
    hash_otp,
    otp_expiry_time,
    verify_otp_hash,
)


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
MODEL_PATH = PROJECT_ROOT / "models" / "spam_model.joblib"
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"
FEEDBACK_PATH = PROJECT_ROOT / "feedback" / "feedback.jsonl"

COOKIE_NAME = "messageguard_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_BATCH_ROWS = 500
MAX_OTP_ATTEMPTS = 5


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MessageGuard API",
    description="API for the MessageGuard spam detection website.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class FeedbackRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    predicted_label: Literal["spam", "ham"]
    corrected_label: Literal["spam", "ham"]
    consent: bool


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class OtpVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    otp: str = Field(pattern=r"^\d{6}$")


class SignupOtpVerificationRequest(OtpVerificationRequest):
    password: str = Field(min_length=8, max_length=128)


_model = None


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    return normalized


def get_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail="Trained model not found. Run: python -m src.train",
            )
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Could not load the trained model: {error}",
            ) from error

    return _model


def predict_texts(texts):
    model = get_model()
    labels = model.predict(texts)
    probabilities = model.predict_proba(texts)
    spam_index = list(model.classes_).index("spam")

    return [
        {
            "text": text,
            "label": str(label),
            "spam_probability": float(probability[spam_index]),
        }
        for text, label, probability in zip(texts, labels, probabilities)
    ]


def set_login_cookie(response: Response, email: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(email),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def public_user(user: User):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def create_and_send_otp(email: str, purpose: str, database: Session):
    otp = generate_otp()

    old_challenge = (
        database.query(OtpChallenge)
        .filter(
            OtpChallenge.email == email,
            OtpChallenge.purpose == purpose,
        )
        .first()
    )
    if old_challenge:
        database.delete(old_challenge)
        database.flush()

    challenge = OtpChallenge(
        email=email,
        purpose=purpose,
        otp_hash=hash_otp(email, purpose, otp),
        expires_at=otp_expiry_time(),
        attempts=0,
    )
    database.add(challenge)
    database.commit()

    try:
        send_otp_email(email, otp, purpose)
    except RuntimeError as error:
        database.delete(challenge)
        database.commit()
        raise HTTPException(status_code=502, detail=str(error)) from error


def check_otp(email: str, purpose: str, entered_otp: str, database: Session):
    challenge = (
        database.query(OtpChallenge)
        .filter(
            OtpChallenge.email == email,
            OtpChallenge.purpose == purpose,
        )
        .first()
    )

    if not challenge:
        raise HTTPException(
            status_code=400,
            detail="OTP nahi mila ya expire ho chuka hai. Naya OTP request karein.",
        )

    if challenge.attempts >= MAX_OTP_ATTEMPTS:
        database.delete(challenge)
        database.commit()
        raise HTTPException(
            status_code=429,
            detail="Bahut attempts ho gaye. Naya OTP request karein.",
        )

    expiry = challenge.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry <= datetime.now(timezone.utc):
        database.delete(challenge)
        database.commit()
        raise HTTPException(
            status_code=400,
            detail="OTP expire ho gaya. Naya OTP request karein.",
        )

    if not verify_otp_hash(email, purpose, entered_otp, challenge.otp_hash):
        challenge.attempts += 1
        database.commit()
        raise HTTPException(status_code=400, detail="OTP sahi nahi hai.")

    database.delete(challenge)
    database.commit()


def get_optional_current_user(
    request: Request,
    database: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)
    email = get_email_from_token(token) if token else None

    if not email:
        return None

    user = database.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None

    return user


def get_current_user(
    request: Request,
    database: Session = Depends(get_db),
):
    user = get_optional_current_user(request, database)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


@app.get("/", include_in_schema=False)
def home(user: User | None = Depends(get_optional_current_user)):
    if user:
        return RedirectResponse(url="/app", status_code=303)
    return FileResponse(WEB_DIR / "index.html")


@app.get("/app", include_in_schema=False)
def detector_page(user: User = Depends(get_current_user)):
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "model_available": MODEL_PATH.exists()}


@app.post("/api/auth/signup/request-otp")
def signup_request_otp(
    request: AuthRequest,
    database: Session = Depends(get_db),
):
    email = normalize_email(request.email)

    existing_user = database.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    create_and_send_otp(email, "signup", database)
    return {"message": "Signup verification code email par bhej diya gaya hai."}


@app.post("/api/auth/signup/verify-otp")
def signup_verify_otp(
    request: SignupOtpVerificationRequest,
    response: Response,
    database: Session = Depends(get_db),
):
    email = normalize_email(request.email)

    existing_user = database.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    check_otp(email, "signup", request.otp, database)

    user = User(
        email=email,
        hashed_password=hash_password(request.password),
    )
    database.add(user)
    database.commit()
    database.refresh(user)

    set_login_cookie(response, user.email)
    return {"user": public_user(user)}


@app.post("/api/auth/signin/request-otp")
def signin_request_otp(
    request: AuthRequest,
    database: Session = Depends(get_db),
):
    email = normalize_email(request.email)
    user = database.query(User).filter(User.email == email).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")

    create_and_send_otp(email, "signin", database)
    return {"message": "Signin verification code email par bhej diya gaya hai."}


@app.post("/api/auth/signin/verify-otp")
def signin_verify_otp(
    request: OtpVerificationRequest,
    response: Response,
    database: Session = Depends(get_db),
):
    email = normalize_email(request.email)
    check_otp(email, "signin", request.otp, database)

    user = database.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Please sign in again.")

    set_login_cookie(response, user.email)
    return {"user": public_user(user)}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "You have signed out."}


@app.get("/api/auth/me")
def current_user(user: User = Depends(get_current_user)):
    return {"user": public_user(user)}


@app.get("/api/metrics")
def get_metrics(user: User = Depends(get_current_user)):
    if not METRICS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Model metrics not found. Run: python -m src.train",
        )

    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read model metrics.",
        ) from error


@app.post("/api/predict")
def predict_message(
    request: MessageRequest,
    user: User = Depends(get_current_user),
):
    message = request.text.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    result = predict_texts([message])[0]
    return {
        "label": result["label"],
        "spam_probability": result["spam_probability"],
    }


@app.post("/api/predict/batch")
async def predict_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV file must be 2 MB or smaller.")

    try:
        data = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the CSV file: {error}",
        ) from error

    text_column = next(
        (column for column in data.columns if str(column).strip().lower() == "text"),
        None,
    )
    if text_column is None:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain a column named 'text'.",
        )

    messages = data[text_column].dropna().astype(str).str.strip()
    messages = messages[messages != ""]

    if messages.empty:
        raise HTTPException(status_code=400, detail="No messages found in the CSV.")
    if len(messages) > MAX_BATCH_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"CSV can contain at most {MAX_BATCH_ROWS} messages.",
        )

    results = predict_texts(messages.tolist())
    spam_count = sum(result["label"] == "spam" for result in results)

    return {
        "total": len(results),
        "spam_count": spam_count,
        "ham_count": len(results) - spam_count,
        "results": results,
    }


@app.post("/api/feedback")
def save_feedback(
    feedback: FeedbackRequest,
    user: User = Depends(get_current_user),
):
    if not feedback.consent:
        raise HTTPException(
            status_code=400,
            detail="Consent is required before saving feedback.",
        )

    record = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "text": feedback.text.strip(),
        "predicted_label": feedback.predicted_label,
        "corrected_label": feedback.corrected_label,
    }

    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FEEDBACK_PATH.open("a", encoding="utf-8") as feedback_file:
            feedback_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save feedback on the server.",
        ) from error

    return {"message": "Thank you. Your feedback has been saved."}