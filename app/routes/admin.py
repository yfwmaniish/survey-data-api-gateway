from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

from app.utils.auth import require_admin
from app.utils.performance_monitor import performance_monitor
from app.utils.cache import query_cache
from app.utils.rate_limiter import rate_limiter
from app.database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive admin dashboard data
    """
    # Get performance summary
    perf_summary = performance_monitor.get_performance_summary(24)
    
    # Get cache statistics
    cache_stats = query_cache.get_cache_stats()
    
    # Get system health
    db_healthy = db_manager.test_connection()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system_status": {
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "enabled" if cache_stats.get("enabled") else "disabled",
            "api": "operational"
        },
        "performance": perf_summary,
        "cache": cache_stats,
        "admin_user": current_user["user_id"]
    }

@router.get("/performance/detailed")
async def get_detailed_performance(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get detailed performance analytics
    """
    summary = performance_monitor.get_performance_summary(hours)
    slow_queries = performance_monitor.get_slow_queries_report(50)
    
    return {
        "time_window_hours": hours,
        "summary": summary,
        "slow_queries": slow_queries,
        "recommendations": _generate_performance_recommendations(summary, slow_queries)
    }

def _generate_performance_recommendations(summary: Dict, slow_queries: List) -> List[Dict[str, str]]:
    """Generate performance improvement recommendations"""
    recommendations = []
    
    if not summary or "performance_metrics" not in summary:
        return recommendations
    
    perf = summary["performance_metrics"]
    
    # Check average execution time
    if perf.get("avg_execution_time", 0) > 2.0:
        recommendations.append({
            "type": "performance",
            "priority": "high",
            "title": "High Average Query Time",
            "description": f"Average query time is {perf['avg_execution_time']:.2f}s. Consider query optimization.",
            "action": "Review slow queries and add database indexes"
        })
    
    # Check success rate
    if summary.get("success_rate", 100) < 95:
        recommendations.append({
            "type": "reliability",
            "priority": "high",
            "title": "Low Success Rate",
            "description": f"Query success rate is {summary['success_rate']:.1f}%. Investigate common errors.",
            "action": "Check error logs and improve query validation"
        })
    
    # Check slow queries
    if len(slow_queries) > 10:
        recommendations.append({
            "type": "optimization",
            "priority": "medium",
            "title": "Many Slow Queries",
            "description": f"{len(slow_queries)} slow queries detected.",
            "action": "Optimize frequently used slow queries and add caching"
        })
    
    # Check complexity distribution
    complexity = summary.get("query_complexity", {})
    high_complex = complexity.get("high_complexity", 0)
    total_queries = summary.get("total_queries", 1)
    
    if high_complex / total_queries > 0.3:
        recommendations.append({
            "type": "complexity",
            "priority": "medium",
            "title": "High Query Complexity",
            "description": f"{high_complex}/{total_queries} queries are high complexity.",
            "action": "Consider breaking down complex queries or creating materialized views"
        })
    
    return recommendations

@router.get("/users/analytics")
async def get_user_analytics(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get user behavior analytics
    """
    # This would typically query a user analytics database
    # For now, we'll use the performance monitor data
    
    summary = performance_monitor.get_performance_summary(168)  # 1 week
    
    return {
        "active_users": len(summary.get("most_active_users", [])),
        "most_active_users": summary.get("most_active_users", []),
        "user_distribution": {
            "power_users": len([u for u in summary.get("most_active_users", []) if u["query_count"] > 100]),
            "regular_users": len([u for u in summary.get("most_active_users", []) if 10 <= u["query_count"] <= 100]),
            "casual_users": len([u for u in summary.get("most_active_users", []) if u["query_count"] < 10])
        }
    }

@router.get("/cache/management")
async def get_cache_management(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cache management information
    """
    stats = query_cache.get_cache_stats()
    
    return {
        "cache_status": stats,
        "management_options": {
            "clear_all": "POST /admin/cache/clear",
            "clear_user": "POST /admin/cache/clear/{user_id}",
            "invalidate_pattern": "POST /admin/cache/invalidate"
        }
    }

@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clear cache entries
    """
    if pattern:
        cleared = query_cache.invalidate_pattern(pattern)
        return {
            "action": "pattern_clear",
            "pattern": pattern,
            "entries_cleared": cleared,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        # Clear all cache (this would need to be implemented in the cache class)
        return {
            "action": "full_clear",
            "message": "Full cache clear not implemented yet",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/cache/clear/{user_id}")
async def clear_user_cache(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clear cache for specific user
    """
    cleared = query_cache.clear_user_cache(user_id)
    
    return {
        "action": "user_cache_clear",
        "user_id": user_id,
        "entries_cleared": cleared,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/rate-limits/status")
async def get_rate_limit_status(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get rate limiting status and statistics
    """
    # This would typically aggregate rate limit data
    return {
        "rate_limiter_status": "active",
        "global_limits": {
            "basic_tier": "100 requests/hour",
            "premium_tier": "1000 requests/hour",
            "enterprise_tier": "10000 requests/hour"
        },
        "endpoint_limits": {
            "query": "50 requests/minute",
            "datasets": "100 requests/minute",
            "schema": "200 requests/minute"
        }
    }

@router.post("/rate-limits/clear/{user_id}")
async def clear_user_rate_limit(
    user_id: str,
    endpoint: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clear rate limits for a specific user
    """
    cleared = rate_limiter.clear_rate_limit(user_id, endpoint or "default")
    
    return {
        "action": "rate_limit_clear",
        "user_id": user_id,
        "endpoint": endpoint or "all",
        "success": cleared,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/database/health")
async def get_database_health(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get detailed database health information
    """
    # Test connection
    connection_healthy = db_manager.test_connection()
    
    health_info = {
        "connection_status": "healthy" if connection_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if connection_healthy:
        try:
            # Get database statistics
            stats_query = """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            LIMIT 10;
            """
            
            table_stats = db_manager.execute_query(stats_query)
            health_info["table_statistics"] = table_stats
            
        except Exception as e:
            health_info["statistics_error"] = str(e)
    
    return health_info

@router.get("/queries/analysis")
async def get_query_analysis(
    days: int = Query(7, ge=1, le=30),
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get advanced query analysis
    """
    hours = days * 24
    summary = performance_monitor.get_performance_summary(hours)
    slow_queries = performance_monitor.get_slow_queries_report(100)
    
    # Analyze query patterns
    query_patterns = {}
    complexity_trends = {"high": 0, "medium": 0, "low": 0}
    
    for query in slow_queries:
        complexity = query.get("complexity", "unknown")
        complexity_trends[complexity] = complexity_trends.get(complexity, 0) + 1
    
    return {
        "analysis_period_days": days,
        "query_patterns": query_patterns,
        "complexity_trends": complexity_trends,
        "performance_summary": summary,
        "optimization_opportunities": _identify_optimization_opportunities(slow_queries)
    }

def _identify_optimization_opportunities(slow_queries: List[Dict]) -> List[Dict[str, Any]]:
    """Identify query optimization opportunities"""
    opportunities = []
    
    # Group similar queries
    query_patterns = {}
    for query in slow_queries:
        # Simple pattern matching - in production, you'd use more sophisticated analysis
        snippet = query.get("query_snippet", "").lower()
        
        # Look for common patterns
        if "join" in snippet and "where" in snippet:
            key = "complex_joins"
        elif "group by" in snippet:
            key = "aggregations"
        elif "order by" in snippet:
            key = "sorting"
        else:
            key = "other"
        
        if key not in query_patterns:
            query_patterns[key] = []
        query_patterns[key].append(query)
    
    # Generate recommendations
    for pattern, queries in query_patterns.items():
        if len(queries) > 5:  # Frequent pattern
            avg_time = sum(q["execution_time"] for q in queries) / len(queries)
            opportunities.append({
                "pattern": pattern,
                "frequency": len(queries),
                "avg_execution_time": round(avg_time, 2),
                "recommendation": _get_pattern_recommendation(pattern)
            })
    
    return opportunities

def _get_pattern_recommendation(pattern: str) -> str:
    """Get optimization recommendation for query pattern"""
    recommendations = {
        "complex_joins": "Consider adding indexes on join columns and WHERE clause predicates",
        "aggregations": "Consider creating materialized views for frequently used aggregations",
        "sorting": "Add indexes on columns used in ORDER BY clauses",
        "other": "Review query structure and consider general optimization techniques"
    }
    return recommendations.get(pattern, "No specific recommendation available")

@router.post("/maintenance/cleanup")
async def run_maintenance_cleanup(
    older_than_days: int = Query(7, ge=1, le=30),
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Run maintenance cleanup tasks
    """
    older_than_hours = older_than_days * 24
    
    # Clear old performance metrics
    performance_monitor.clear_metrics(older_than_hours)
    
    return {
        "action": "maintenance_cleanup",
        "cleaned_data_older_than_days": older_than_days,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed"
    }

@router.get("/system/resources")
async def get_system_resources(
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get current system resource usage
    """
    import psutil
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu": {
            "usage_percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "usage_percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "usage_percent": round((disk.used / disk.total) * 100, 1)
        }
    }
