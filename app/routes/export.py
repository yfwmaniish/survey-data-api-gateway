from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from app.database import db_manager
from app.utils.auth import require_query
from app.utils.query_validator import query_validator
from app.utils.exporters import DataExporter, StreamingExporter, get_export_format_info
from app.utils.performance_monitor import performance_monitor
from app.utils.cache import query_cache
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])

class ExportRequest(BaseModel):
    """Request model for data export"""
    sql: str
    format: str = "csv"  # csv, excel, json, parquet
    filename: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    use_cache: bool = True
    streaming: bool = False  # For large datasets

@router.get("/formats")
async def get_supported_formats(
    current_user: Dict[str, Any] = Depends(require_query)
) -> Dict[str, Any]:
    """
    Get information about supported export formats
    """
    return {
        "supported_formats": get_export_format_info(),
        "streaming_support": ["csv", "json"],
        "max_rows_non_streaming": 10000,
        "recommendations": {
            "small_datasets": "csv or json",
            "medium_datasets": "excel or parquet", 
            "large_datasets": "parquet with streaming",
            "analytics": "parquet",
            "reporting": "excel"
        }
    }

@router.post("/query")
async def export_query_results(
    request: ExportRequest,
    current_user: Dict[str, Any] = Depends(require_query)
) -> StreamingResponse:
    """
    Execute query and export results in specified format
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate query
        query_validator.validate_query(request.sql)
        
        # Generate filename if not provided
        if not request.filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            format_info = get_export_format_info()
            extension = format_info.get(request.format, {}).get("extension", ".txt")
            request.filename = f"export_{timestamp}{extension}"
        
        # Check cache first (if enabled)
        cached_result = None
        if request.use_cache:
            cached_result = query_cache.get(
                request.sql, 
                request.params, 
                current_user["user_id"]
            )
        
        # Execute query if not cached
        if cached_result:
            logger.info(f"Using cached results for export: {request.sql[:50]}...")
            result_data = cached_result["result"]["data"]
            execution_time = 0  # Cache hit
        else:
            # Execute query
            result_data = db_manager.execute_query(request.sql, request.params)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Cache the results for future use
            if request.use_cache:
                query_cache.set(
                    request.sql,
                    {"data": result_data, "row_count": len(result_data)},
                    request.params,
                    current_user["user_id"],
                    ttl=3600  # 1 hour cache
                )
        
        # Record performance
        performance_monitor.record_query_performance(
            current_user["user_id"],
            request.sql,
            execution_time,
            len(result_data),
            "export_success"
        )
        
        # Handle streaming for large datasets
        if request.streaming and len(result_data) > 1000:
            return _handle_streaming_export(result_data, request.format, request.filename)
        
        # Regular export
        return _handle_regular_export(result_data, request.format, request.filename)
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        performance_monitor.record_query_performance(
            current_user["user_id"],
            request.sql,
            execution_time,
            0,
            "export_error",
            str(e)
        )
        
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

def _handle_regular_export(data: List[Dict[str, Any]], format: str, filename: str) -> StreamingResponse:
    """Handle regular export for small to medium datasets"""
    if format == "csv":
        return DataExporter.export_to_csv(data, filename)
    elif format == "excel":
        return DataExporter.export_to_excel(data, filename)
    elif format == "json":
        return DataExporter.export_to_json(data, filename, pretty=True)
    elif format == "parquet":
        return DataExporter.export_to_parquet(data, filename)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: {format}"
        )

def _handle_streaming_export(data: List[Dict[str, Any]], format: str, filename: str) -> StreamingResponse:
    """Handle streaming export for large datasets"""
    # Create a generator that yields data in chunks
    def data_generator():
        chunk_size = 1000
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    if format == "csv":
        return StreamingExporter.stream_csv(data_generator(), filename)
    elif format == "json":
        return StreamingExporter.stream_json(data_generator(), filename)
    else:
        # Fall back to regular export for unsupported streaming formats
        logger.warning(f"Streaming not supported for {format}, using regular export")
        return _handle_regular_export(data, format, filename)

@router.post("/template/{template_id}")
async def export_template_query(
    template_id: str,
    format: str = Query("csv", regex="^(csv|excel|json|parquet)$"),
    filename: Optional[str] = None,
    parameters: Optional[Dict[str, str]] = None,
    current_user: Dict[str, Any] = Depends(require_query)
) -> StreamingResponse:
    """
    Export results from a predefined query template
    """
    # Get template (this would typically come from a database)
    templates = {
        "user_summary": {
            "sql": "SELECT user_id, COUNT(*) as query_count, AVG(execution_time) as avg_time FROM query_logs WHERE created_date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY user_id ORDER BY query_count DESC LIMIT 100",
            "description": "30-day user activity summary"
        },
        "daily_stats": {
            "sql": "SELECT DATE(created_at) as date, COUNT(*) as queries, AVG(execution_time) as avg_time FROM query_logs WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY DATE(created_at) ORDER BY date",
            "description": "Daily query statistics for last 7 days"
        },
        "slow_queries": {
            "sql": "SELECT query_snippet, execution_time, user_id, created_at FROM query_logs WHERE execution_time > 5.0 ORDER BY execution_time DESC LIMIT 50",
            "description": "Slowest queries"
        }
    }
    
    if template_id not in templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    
    template = templates[template_id]
    
    # Create export request
    export_request = ExportRequest(
        sql=template["sql"],
        format=format,
        filename=filename or f"{template_id}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}",
        params=parameters,
        use_cache=True
    )
    
    return await export_query_results(export_request, current_user)

@router.get("/templates")
async def get_export_templates(
    current_user: Dict[str, Any] = Depends(require_query)
) -> Dict[str, Any]:
    """
    Get available export templates
    """
    return {
        "templates": {
            "user_summary": {
                "name": "User Activity Summary",
                "description": "30-day user activity summary with query counts and performance",
                "parameters": [],
                "estimated_rows": "< 100"
            },
            "daily_stats": {
                "name": "Daily Query Statistics", 
                "description": "Daily query statistics for the last 7 days",
                "parameters": [],
                "estimated_rows": "< 10"
            },
            "slow_queries": {
                "name": "Slow Query Report",
                "description": "Report of the slowest queries with execution times > 5 seconds",
                "parameters": [],
                "estimated_rows": "< 50"
            }
        },
        "usage": {
            "endpoint": "POST /export/template/{template_id}",
            "parameters": {
                "format": "csv|excel|json|parquet",
                "filename": "optional custom filename",
                "parameters": "template-specific parameters"
            }
        }
    }

@router.get("/history")
async def get_export_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_query)
) -> Dict[str, Any]:
    """
    Get export history for the current user
    """
    # This would typically query an export history table
    # For now, return a placeholder response
    
    return {
        "user_id": current_user["user_id"],
        "exports": [
            {
                "export_id": "placeholder",
                "timestamp": datetime.utcnow().isoformat(),
                "format": "csv",
                "filename": "example_export.csv",
                "row_count": 0,
                "status": "This feature will be implemented with persistent storage"
            }
        ],
        "total_exports": 0,
        "note": "Export history requires database storage implementation"
    }

@router.post("/bulk")
async def bulk_export(
    queries: List[str],
    format: str = Query("json", regex="^(csv|excel|json|parquet)$"),
    combine: bool = Query(True, description="Combine all results into single file"),
    current_user: Dict[str, Any] = Depends(require_query)
) -> StreamingResponse:
    """
    Export results from multiple queries
    """
    if len(queries) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 queries allowed for bulk export"
        )
    
    all_results = []
    query_info = []
    
    for i, sql in enumerate(queries):
        try:
            # Validate each query
            query_validator.validate_query(sql)
            
            # Execute query
            start_time = datetime.utcnow()
            result_data = db_manager.execute_query(sql)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Record performance
            performance_monitor.record_query_performance(
                current_user["user_id"],
                sql,
                execution_time,
                len(result_data),
                "bulk_export_success"
            )
            
            if combine:
                # Add query info to each row
                for row in result_data:
                    row["_query_index"] = i + 1
                    row["_query_snippet"] = sql[:50] + "..." if len(sql) > 50 else sql
                all_results.extend(result_data)
            else:
                all_results.append({
                    "query_index": i + 1,
                    "query": sql,
                    "row_count": len(result_data),
                    "execution_time": execution_time,
                    "results": result_data
                })
            
            query_info.append({
                "index": i + 1,
                "query": sql[:100] + "..." if len(sql) > 100 else sql,
                "row_count": len(result_data),
                "execution_time": execution_time
            })
            
        except Exception as e:
            logger.error(f"Bulk export query {i+1} failed: {str(e)}")
            query_info.append({
                "index": i + 1,
                "query": sql[:100] + "..." if len(sql) > 100 else sql,
                "error": str(e),
                "row_count": 0,
                "execution_time": 0
            })
    
    # Add metadata
    if combine and format == "json":
        export_data = {
            "metadata": {
                "export_type": "bulk_combined",
                "total_queries": len(queries),
                "total_rows": len(all_results),
                "export_timestamp": datetime.utcnow().isoformat(),
                "query_info": query_info
            },
            "data": all_results
        }
        all_results = [export_data]
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"bulk_export_{timestamp}.{format}"
    
    return _handle_regular_export(all_results, format, filename)
