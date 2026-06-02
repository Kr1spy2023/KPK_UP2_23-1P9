import re
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, constr, validator
from passlib.hash import bcrypt
from peewee import IntegrityError
from models import db, User, Token, init_db

app = FastAPI(title="Auth Service")

USERNAME_RE = re.compile(r'^[a-z0-9_]+$')

# ==================== СХЕМЫ ====================

class RegisterRequest(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)

    @validator('username')
    def username_normalize(cls, v):
        v = v.lower()
        if not USERNAME_RE.match(v):
            raise ValueError('username может содержать только a-z, 0-9, _')
        return v

    @validator('email')
    def email_normalize(cls, v):
        return v.lower()

class LoginRequest(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=8)

    @validator('username')
    def username_normalize(cls, v):
        v = v.lower()
        if not USERNAME_RE.match(v):
            raise ValueError('username может содержать только a-z, 0-9, _')
        return v

class TokenRequest(BaseModel):
    token: constr(min_length=1)

class ResetPasswordRequest(BaseModel):
    email: EmailStr

    @validator('email')
    def email_lower(cls, v):
        return v.lower()

class ConfirmResetRequest(BaseModel):
    token: constr(min_length=1)
    new_pass: constr(min_length=8)

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str

class TokenOut(BaseModel):
    token: str
    expires_at: str

class SuccessOut(BaseModel):
    success: bool

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_db():
    if db.is_closed():
        db.connect()

def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat()
    }

# ==================== ЭНДПОИНТЫ ====================

@app.on_event("startup")
def startup():
    init_db()

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest):
    get_db()
    try:
        user = User.create_user(
            username=data.username,
            email=data.email,
            pass_hash=bcrypt.hash(data.password)
        )
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    return user_to_dict(user)

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest):
    get_db()
    user = User.get_or_none(User.username == data.username)
    if not user or not bcrypt.verify(data.password, user.pass_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь деактивирован")
    token = Token.create_for_user(user, 'access')
    return {"token": token.token, "expires_at": token.expires_at.isoformat()}

@app.post("/auth/refresh", response_model=TokenOut)
def refresh_token(data: TokenRequest):
    get_db()
    # Явная проверка что токен именно типа 'access'
    token = Token.get_or_none(
        (Token.token == data.token) & (Token.token_type == 'access')
    )
    if not token or not token.is_valid:
        raise HTTPException(status_code=401, detail="Токен недействителен или истёк")
    new_token = Token.create_for_user(token.user, 'access')
    return {"token": new_token.token, "expires_at": new_token.expires_at.isoformat()}

@app.delete("/auth/users/{user_id}", response_model=SuccessOut)
def deactivate_user(user_id: int):
    get_db()
    return {"success": User.soft_delete(user_id)}

@app.post("/auth/password/reset-request", response_model=SuccessOut)
def reset_request(data: ResetPasswordRequest):
    get_db()
    try:
        Token.request_reset(data.email)
    except Exception:
        pass  # Всегда success=True — не раскрываем наличие аккаунта и не бросаем 500
    return {"success": True}

@app.post("/auth/password/reset", response_model=SuccessOut)
def reset_password(data: ConfirmResetRequest):
    get_db()
    result = Token.reset_password(data.token, bcrypt.hash(data.new_pass))
    if not result:
        raise HTTPException(status_code=400, detail="Токен недействителен или истёк")
    return {"success": True}

@app.get("/auth/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    get_db()
    user = User.get_or_none(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user_to_dict(user)

@app.get("/auth/users", response_model=List[UserOut])
def list_users(
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    get_db()
    users = User.get_list(is_active=is_active, search=search,
                          limit=limit, offset=offset)
    return [user_to_dict(u) for u in users]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)