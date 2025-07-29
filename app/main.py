from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Dict, Any

from app.config import settings
from app.database import db_manager
from app.routes import query, meta, websocket, admin, export
from app.utils.auth import get_current_user, create_access_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Survey Data API Gateway...")
    
    # Test database connection
    if db_manager.test_connection():
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Survey Data API Gateway...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    ## Survey Data API Gateway
    
    A secure API gateway for querying survey datasets with SQL.
    
    ### Features
    - 🔍 Execute SELECT queries on survey data
    - 📊 Get dataset metadata and schema information
    - 🔐 JWT and API key authentication
    - 🛡️ SQL injection protection
    - 📝 Query templates for common operations
    
    ### Authentication
    This API supports two authentication methods:
    1. **API Key**: Use a Bearer token with your API key
    2. **JWT Token**: Use a Bearer token with a valid JWT
    
    ### Demo API Keys
    - `demo-key-123`: Read and query permissions
    - `admin-key-456`: Full admin permissions
    
    ### Example Usage
    ```bash
    curl -X POST "http://localhost:8000/query/" \\
         -H "Authorization: Bearer demo-key-123" \\
         -H "Content-Type: application/json" \\
         -d '{"sql": "SELECT * FROM surveys LIMIT 10"}'
    ```
    """,
    lifespan=lifespan,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query.router)
app.include_router(meta.router)
app.include_router(websocket.router)
app.include_router(admin.router)
app.include_router(export.router)


@app.get("/", tags=["health"])
async def root():
    """
    API root endpoint - returns basic API information
    """
    return {
        "message": "Survey Data API Gateway",
        "version": settings.api_version,
        "status": "operational",
        "docs": "/docs",
        "timestamp": datetime.utcnow()
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint
    """
    # Test database connection
    db_healthy = db_manager.test_connection()
    
    status = "healthy" if db_healthy else "unhealthy"
    status_code = 200 if db_healthy else 503
    
    response = {
        "status": status,
        "timestamp": datetime.utcnow(),
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "api": "healthy"
        }
    }
    
    return JSONResponse(
        content=response,
        status_code=status_code
    )


@app.post("/auth/token", tags=["auth"])
async def create_token(user_id: str, permissions: list = ["read", "query"]):
    """
    Create a JWT token for testing purposes
    
    In production, this would be replaced with proper user authentication
    """
    token_data = {
        "user_id": user_id,
        "permissions": permissions
    }
    
    access_token = create_access_token(data=token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@app.get("/user/info", tags=["auth"])
async def get_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get information about the current authenticated user
    """
    return {
        "user_id": current_user["user_id"],
        "permissions": current_user["permissions"],
        "auth_type": current_user["auth_type"]
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
