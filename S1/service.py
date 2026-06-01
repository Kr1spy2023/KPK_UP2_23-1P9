from datetime import datetime, timedelta
from typing import Optional, List
import secrets

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr
from passlib.hash import bcrypt
from models import db, User, Token, init_db

app = FastAPI(title="Auth Service")

# ==================== СХЕМЫ ====================

class RegisterRequest(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)

class LoginRequest(BaseModel):
    username: str
    password: constr(min_length=8)

class TokenRequest(BaseModel):
    token: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ConfirmResetRequest(BaseModel):
    token: str
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

def create_token(user: User, token_type: str, hours: int) -> Token:
    Token.delete().where(
        (Token.user == user) & (Token.token_type == token_type)
    ).execute()
    return Token.create(
        user=user,
        token=secrets.token_urlsafe(64),
        token_type=token_type,
        expires_at=datetime.now() + timedelta(hours=hours)
    )

# ==================== ЭНДПОИНТЫ ====================

@app.on_event("startup")
def startup():
    init_db()

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest):
    get_db()
    if User.select().where(User.username == data.username).exists():
        raise HTTPException(status_code=400, detail="username уже занят")
    if User.select().where(User.email == data.email).exists():
        raise HTTPException(status_code=400, detail="email уже занят")
    user = User.create(
        username=data.username,
        email=data.email,
        pass_hash=bcrypt.hash(data.password)
    )
    return user_to_dict(user)

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest):
    get_db()
    user = User.get_or_none(User.username == data.username)
    if not user or not bcrypt.verify(data.password, user.pass_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь деактивирован")
    token = create_token(user, 'access', hours=24)
    return {"token": token.token, "expires_at": token.expires_at.isoformat()}

@app.post("/auth/refresh", response_model=TokenOut)
def refresh_token(data: TokenRequest):
    get_db()
    token = Token.get_or_none(
        (Token.token == data.token) & (Token.token_type == 'access')
    )
    if not token or not token.is_valid:
        raise HTTPException(status_code=401, detail="Токен недействителен или истёк")
    new_token = create_token(token.user, 'access', hours=24)
    return {"token": new_token.token, "expires_at": new_token.expires_at.isoformat()}

@app.delete("/auth/users/{user_id}", response_model=SuccessOut)
def deactivate_user(user_id: int):
    get_db()
    result = User.soft_delete(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Пользователь не найден или уже деактивирован")
    return {"success": True}

@app.post("/auth/password/reset-request", response_model=SuccessOut)
def reset_request(data: ResetPasswordRequest):
    get_db()
    user = User.get_or_none(User.email == data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email не найден")
    create_token(user, 'reset', hours=1)
    return {"success": True}

@app.post("/auth/password/reset", response_model=SuccessOut)
def reset_password(data: ConfirmResetRequest):
    get_db()
    token = Token.get_or_none(
        (Token.token == data.token) & (Token.token_type == 'reset')
    )
    if not token or not token.is_valid:
        raise HTTPException(status_code=400, detail="Токен недействителен или истёк")
    User.update(pass_hash=bcrypt.hash(data.new_pass)).where(
        User.id == token.user_id
    ).execute()
    token.delete_instance()
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
    limit: int = 20,
    offset: int = 0
):
    get_db()
    query = User.select()
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(User.username.contains(search))
    query = query.limit(limit).offset(offset)
    return [user_to_dict(u) for u in query]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
