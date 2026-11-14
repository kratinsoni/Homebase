from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_access_token, get_current_user, hash_password, verify_password
from worker.db.models import User
from worker.db.session import get_session

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)

class UserOut(BaseModel):
    id: str
    email: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    user = User(email=body.email.lower(), password_hash = hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="User already exists!")

    return UserOut(id=user.id, email=body.email)

@router.post("/login", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email)