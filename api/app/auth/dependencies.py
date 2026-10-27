from fastapi import Depends, HTTPException, status, Header, Query
from typing import Optional, Dict, Any
from api.app.auth.jwt_handler import decode_access_token
from api.app.database import db_cursor

def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Extracts and authenticates user from Bearer header or query parameter (for SSE EventSource).
    Raises 401 if token is missing, expired, or invalid.
    """
    extracted_token = None
    if authorization and authorization.startswith("Bearer "):
        extracted_token = authorization.split(" ")[1]
    elif token:
        extracted_token = token
        
    if not extracted_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Token no proporcionado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_access_token(extracted_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_email = payload["sub"]
    
    with db_cursor(as_admin=False, commit=False) as cur:
        cur.execute(
            "SELECT id, email, full_name, role, is_active, created_at FROM auth.users WHERE email = %s;",
            (user_email,)
        )
        user = cur.fetchone()
        
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return dict(user)

def require_role(required_role: str):
    """
    Role-Based Access Control (RBAC) dependency.
    Role hierarchy: 'admin' can access both 'viewer' and 'admin' endpoints.
    'viewer' cannot access 'admin' endpoints (returns 403 Forbidden).
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "viewer")
        
        if required_role == "admin" and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Se requieren privilegios de Administrador para esta acción."
            )
        return current_user
        
    return role_checker
