import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
    print("WARNING: JWT_SECRET_KEY not set. Using auto-generated key (tokens will not survive restarts).")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_admin_credentials():
    username = os.getenv("ADMIN_USERNAME", "")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    plain_password = os.getenv("ADMIN_PASSWORD", "")
    if not username or (not password_hash and not plain_password):
        raise RuntimeError(
            "Admin credentials not configured. Set ADMIN_USERNAME and either "
            "ADMIN_PASSWORD_HASH or ADMIN_PASSWORD environment variables."
        )
    if not password_hash:
        password_hash = get_password_hash(plain_password)
    return username, password_hash


def authenticate_admin(username: str, password: str) -> bool:
    admin_username, admin_password_hash = get_admin_credentials()
    if username != admin_username:
        return False
    return verify_password(password, admin_password_hash)


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    admin_username, _ = get_admin_credentials()
    if username != admin_username:
        raise credentials_exception
    return username
