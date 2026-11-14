from datetime import datetime, timezone, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from worker.config.settings import settings
from worker.db.models import User
from worker.db.session import get_session

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()  # uses Argon2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password):
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(user_id) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.jwt_secret, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> User:
    error = HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except:
        raise error
    user_id = payload.get("sub")
    if user_id is None:
        raise error
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

