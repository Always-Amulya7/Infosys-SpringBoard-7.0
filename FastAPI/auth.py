from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .jwt_handler import verify_token
from .redis_client import redis_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def authenticate_token(token: str):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("username")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    stored_token = redis_client.get(f"user_session:{username}")
    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or logged out",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if isinstance(stored_token, bytes):
        stored_token = stored_token.decode("utf-8")
    if stored_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def get_current_user(token: str = Depends(oauth2_scheme)):
    return authenticate_token(token)

def get_org_admin(current_user=Depends(get_current_user)):
    role = current_user.get("role")
    if role != "Organization Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization Admin access required",
        )
    return current_user

def get_admin_user(current_user=Depends(get_current_user)):
    allowed_roles = [
        "Organization Admin",
        "Technical Admin",
        "Managerial Admin",
        "Operational Admin",
    ]
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user

def get_employee_user(current_user=Depends(get_current_user)):
    if current_user.get("role") != "Employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Employee access required"
        )
    return current_user

# Database authentication for our web app
