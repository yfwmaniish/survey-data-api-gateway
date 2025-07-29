from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

from app.database import db_manager
from app.utils.auth import require_query
from app.utils.query_validator import query_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request model for SQL queries"""
    sql: str = Field(..., description="SQL query to execute", min_length=1, max_length=10000)
    params: Optional[Dict[str, Any]] = Field(default=None, description="Optional query parameters")


class QueryResponse(BaseModel):
    """Response model for query results"""
    data: List[Dict[str, Any]] = Field(..., description="Query result data")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    query_info: Dict[str, Any] = Field(..., description="Information about the executed query")


class QueryError(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@router.post("/", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    current_user: Dict[str, Any] = Depends(require_query)
) -> QueryResponse:
    """
    Execute a SQL query and return results
    
    This endpoint allows users to execute SELECT queries on the survey database.
    Only SELECT statements are allowed for security reasons.
    
    - **sql**: The SQL query to execute (SELECT statements only)
    - **params**: Optional parameters for parameterized queries
    
    Returns the query results as JSON along with metadata.
    """
    start_time = time.time()
    
    try:
        # Log the query attempt
        logger.info(f"Query request from user {current_user['user_id']}: {request.sql[:100]}...")
        
        # Validate the query
        query_validator.validate_query(request.sql)
        
        # Get query information
        query_info = query_validator.get_query_info(request.sql)
        
        # Execute the query
        result_data = db_manager.execute_query(request.sql, request.params)
        
        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000
        
        # Log successful execution
        logger.info(f"Query executed successfully for user {current_user['user_id']}, "
                   f"returned {len(result_data)} rows in {execution_time:.2f}ms")
        
        return QueryResponse(
            data=result_data,
            row_count=len(result_data),
            execution_time_ms=round(execution_time, 2),
            query_info=query_info
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (validation errors)
        logger.warning(f"Query validation failed for user {current_user['user_id']}: {e.detail}")
        raise e
        
    except Exception as e:
        # Handle database and other errors
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e)
        
        logger.error(f"Query execution failed for user {current_user['user_id']}: {error_msg}")
        
        # Don't expose internal database errors to the user
        if "database" in error_msg.lower() or "sql" in error_msg.lower():
            detail = "Database query failed. Please check your SQL syntax and try again."
        else:
            detail = "An unexpected error occurred while executing the query."
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_query_templates(
    current_user: Dict[str, Any] = Depends(require_query)
) -> List[Dict[str, Any]]:
    """
    Get predefined query templates
    
    Returns a list of safe, predefined SQL query templates that users can use
    as starting points for their own queries.
    """
    templates = [
        {
            "id": "basic_select",
            "name": "Basic Select",
            "description": "Simple SELECT query with optional WHERE clause",
            "sql": "SELECT * FROM {table_name} WHERE {condition} LIMIT 100;",
            "parameters": ["table_name", "condition"],
            "category": "basic"
        },
        {
            "id": "count_records",
            "name": "Count Records",
            "description": "Count total records in a table",
            "sql": "SELECT COUNT(*) as total_count FROM {table_name};",
            "parameters": ["table_name"],
            "category": "aggregation"
        },
        {
            "id": "group_by_analysis",
            "name": "Group By Analysis",
            "description": "Group records by a column and count occurrences",
            "sql": "SELECT {column_name}, COUNT(*) as count FROM {table_name} GROUP BY {column_name} ORDER BY count DESC LIMIT 20;",
            "parameters": ["table_name", "column_name"],
            "category": "aggregation"
        },
        {
            "id": "date_range_filter",
            "name": "Date Range Filter",
            "description": "Filter records by date range",
            "sql": "SELECT * FROM {table_name} WHERE {date_column} BETWEEN '{start_date}' AND '{end_date}' ORDER BY {date_column} DESC LIMIT 100;",
            "parameters": ["table_name", "date_column", "start_date", "end_date"],
            "category": "filtering"
        },
        {
            "id": "join_tables",
            "name": "Join Tables",
            "description": "Join two tables on a common field",
            "sql": "SELECT a.*, b.{column_name} FROM {table1} a JOIN {table2} b ON a.{join_field} = b.{join_field} LIMIT 100;",
            "parameters": ["table1", "table2", "join_field", "column_name"],
            "category": "joins"
        }
    ]
    
    logger.info(f"Query templates requested by user {current_user['user_id']}")
    return templates


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_query_history(
    current_user: Dict[str, Any] = Depends(require_query),
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get query history for the current user
    
    Note: This is a placeholder implementation. In a production system,
    you would store query history in a separate table/logging system.
    """
    # Placeholder - in production, implement proper query history logging
    logger.info(f"Query history requested by user {current_user['user_id']}")
    
    return [
        {
            "query_id": "placeholder",
            "sql": "This would contain historical queries...",
            "timestamp": datetime.utcnow(),
            "execution_time_ms": 0,
            "row_count": 0,
            "status": "placeholder"
        }
    ]
