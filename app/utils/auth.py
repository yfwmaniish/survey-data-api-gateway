from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Predefined API keys (in production, store these in database)
VALID_API_KEYS = {
    "demo-key-123": {
        "user_id": "demo_user",
        "permissions": ["read", "query"],
        "description": "Demo API key"
    },
    "admin-key-456": {
        "user_id": "admin_user", 
        "permissions": ["read", "query", "admin"],
        "description": "Admin API key"
    }
}


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: str) -> Dict[str, Any]:
    """
    Verify API key and return user information
    
    Args:
        api_key: API key string
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If API key is invalid
    """
    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return VALID_API_KEYS[api_key]


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    Get current user from JWT token or API key
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    # Try JWT token first
    try:
        payload = verify_token(token)
        if "user_id" in payload:
            return {
                "user_id": payload["user_id"],
                "permissions": payload.get("permissions", ["read"]),
                "auth_type": "jwt"
            }
    except HTTPException:
        pass  # Try API key next
    
    # Try API key
    try:
        user_info = verify_api_key(token)
        user_info["auth_type"] = "api_key"
        return user_info
    except HTTPException:
        pass
    
    # If both fail, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_dependency


# Convenience dependencies
require_read = require_permission("read")
require_query = require_permission("query")
require_admin = require_permission("admin")
