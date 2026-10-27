from fastapi import APIRouter, HTTPException, status, Depends
from api.app.auth.models import LoginRequest, TokenResponse, UserResponse
from api.app.auth.jwt_handler import verify_password, create_access_token
from api.app.auth.dependencies import get_current_user
from api.app.database import db_cursor

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest):
    """
    Authenticates user and returns JWT access token with role and user profile.
    """
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(
            "SELECT id, email, password_hash, full_name, role, is_active, created_at FROM auth.users WHERE email = %s;",
            (creds.email.strip().lower(),)
        )
        user = cur.fetchone()
        
    if not user or not verify_password(creds.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifique correo y contraseña."
        )
        
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo en el sistema."
        )
        
    token_payload = {
        "sub": user["email"],
        "role": user["role"],
        "user_id": user["id"],
        "name": user["full_name"]
    }
    token = create_access_token(token_payload)
    
    user_res = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"]
    )
    
    return TokenResponse(access_token=token, token_type="bearer", user=user_res)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(get_current_user)):
    """
    Returns the currently logged-in user profile.
    """
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"]
    )
