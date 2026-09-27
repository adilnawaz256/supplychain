import hashlib
import secrets
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Header
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.models import User, WorkspaceMember

router = APIRouter()

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}", salt

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    if "$" not in stored_password_hash:
        return hashlib.sha256(provided_password.encode('utf-8')).hexdigest() == stored_password_hash
    salt, original_hash = stored_password_hash.split("$", 1)
    computed_hash, _ = hash_password(provided_password, salt)
    return computed_hash == stored_password_hash

def format_user_response(user: User):
    return {
        "id": f"usr-{user.id}",
        "email": user.email,
        "user_metadata": {
            "full_name": user.full_name or user.email.split("@")[0].title(),
            "company_name": user.company_name or "Global Supply Chain Co.",
            "role": user.role or "Admin"
        },
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@router.post("/api/auth/signup", tags=["Authentication"])
def signup(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "").strip()
    full_name = payload.get("fullName", "").strip()
    company_name = payload.get("companyName", "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    password_hash, _ = hash_password(password)

    new_user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name or email.split("@")[0].title(),
        company_name=company_name or "Global Supply Chain Co.",
        role="Admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    wm = db.query(WorkspaceMember).filter(WorkspaceMember.email == email).first()
    if not wm:
        initials = "".join([part[0] for part in new_user.full_name.split()])[:2].upper() or "U"
        db.add(WorkspaceMember(
            name=new_user.full_name,
            email=email,
            role="Admin",
            status="Active",
            initials=initials,
            color="#2563eb",
            bg="#eff6ff"
        ))
        db.commit()

    user_data = format_user_response(new_user)

    return {
        "status": "SUCCESS",
        "message": "Account created successfully",
        "user": user_data,
        "token": f"bearer-{new_user.id}-{secrets.token_hex(8)}"
    }

@router.post("/api/auth/login", tags=["Authentication"])
def login(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        password_hash, _ = hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=email.split("@")[0].replace(".", " ").title(),
            company_name="Global Supply Chain Co.",
            role="Admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not verify_password(user.password_hash, password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

    user_data = format_user_response(user)

    return {
        "status": "SUCCESS",
        "message": "Login successful",
        "user": user_data,
        "token": f"bearer-{user.id}-{secrets.token_hex(8)}"
    }

@router.get("/api/auth/me", tags=["Authentication"])
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("bearer-"):
        try:
            parts = authorization.split("-")
            user_id = int(parts[1])
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return format_user_response(user)
        except Exception:
            pass

    user = db.query(User).first()
    if user:
        return format_user_response(user)
    return None

@router.post("/api/auth/logout", tags=["Authentication"])
def logout():
    return {"status": "SUCCESS", "message": "Logged out successfully"}
