from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from api.auth import authenticate_admin, create_access_token, get_current_admin
from fastapi import Depends

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    if not authenticate_admin(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    access_token = create_access_token(data={"sub": request.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_admin: str = Depends(get_current_admin)):
    return {"username": current_admin}
