"""
Error Response Schema - Standardized error responses for the API

Usage:
    from app.errors import APIError, error_response
    
    raise APIError(status_code=404, code="NOT_FOUND", message="Resource not found")
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
import logging


logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response schema"""
    success: bool = False
    error: dict


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    details: Optional[Any] = None


class APIError(HTTPException):
    """Custom API error with standardized format"""
    
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handler for APIError exceptions"""
    logger.warning(
        f"API Error: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": str(request.url.path),
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for standard HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": None,
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions"""
    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={"path": str(request.url.path)}
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": None,
            }
        }
    )


# Common error codes
class ErrorCodes:
    # Auth
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Agent
    SANDBOX_NOT_CONFIGURED = "SANDBOX_NOT_CONFIGURED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    
    # RAG
    INGESTION_FAILED = "INGESTION_FAILED"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    
    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
