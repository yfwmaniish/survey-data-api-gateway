import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import json
from statistics import mean, median
from app.config import settings

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Advanced performance monitoring and analytics"""
    
    def __init__(self):
        self.query_metrics = defaultdict(list)
        self.system_metrics = deque(maxlen=1000)  # Keep last 1000 measurements
        self.slow_queries = deque(maxlen=100)     # Keep last 100 slow queries
        self.error_metrics = defaultdict(int)
        self.user_metrics = defaultdict(lambda: {"queries": 0, "total_time": 0, "errors": 0})
        
        # Thresholds
        self.slow_query_threshold = getattr(settings, 'slow_query_threshold', 5.0)  # seconds
        self.error_rate_threshold = getattr(settings, 'error_rate_threshold', 0.1)  # 10%
        
    def record_query_performance(self, 
                                user_id: str,
                                query: str, 
                                execution_time: float, 
                                row_count: int,
                                status: str = "success",
                                error: Optional[str] = None):
        """Record query performance metrics"""
        timestamp = datetime.utcnow()
        
        # Query complexity analysis
        complexity = self._analyze_query_complexity(query)
        
        metric = {
            "timestamp": timestamp,
            "user_id": user_id,
            "query_hash": hash(query.lower().strip()) % 10000,
            "query_snippet": query[:100] + "..." if len(query) > 100 else query,
            "execution_time": execution_time,
            "row_count": row_count,
            "status": status,
            "error": error,
            "complexity": complexity,
            "query_length": len(query)
        }
        
        # Store in appropriate collections
        self.query_metrics["all"].append(metric)
        self.query_metrics[user_id].append(metric)
        
        # Track slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append(metric)
            logger.warning(f"Slow query detected: {execution_time:.2f}s - {query[:50]}...")
        
        # Update user metrics
        self.user_metrics[user_id]["queries"] += 1
        self.user_metrics[user_id]["total_time"] += execution_time
        if status == "error":
            self.user_metrics[user_id]["errors"] += 1
            self.error_metrics[error or "unknown"] += 1
        
        # Record system metrics
        self._record_system_metrics()
        
        logger.info(f"Query performance recorded: {execution_time:.2f}s, {row_count} rows, {status}")
    
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity"""
        query_lower = query.lower()
        
        complexity_score = 0
        features = {
            "has_joins": False,
            "has_subqueries": False,
            "has_aggregation": False,
            "has_window_functions": False,
            "has_complex_where": False,
            "estimated_complexity": "low"
        }
        
        # Check for joins
        join_keywords = ['join', 'inner join', 'left join', 'right join', 'full join']
        if any(keyword in query_lower for keyword in join_keywords):
            features["has_joins"] = True
            complexity_score += 2
        
        # Check for subqueries
        if '(' in query and 'select' in query_lower[query_lower.find('('):]:
            features["has_subqueries"] = True
            complexity_score += 3
        
        # Check for aggregation
        agg_functions = ['count(', 'sum(', 'avg(', 'min(', 'max(', 'group by']
        if any(func in query_lower for func in agg_functions):
            features["has_aggregation"] = True
            complexity_score += 1
        
        # Check for window functions
        window_keywords = ['over(', 'partition by', 'row_number(', 'rank(']
        if any(keyword in query_lower for keyword in window_keywords):
            features["has_window_functions"] = True
            complexity_score += 4
        
        # Check for complex WHERE clauses
        if query_lower.count('and') > 2 or query_lower.count('or') > 1:
            features["has_complex_where"] = True
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 6:
            features["estimated_complexity"] = "high"
        elif complexity_score >= 3:
            features["estimated_complexity"] = "medium"
        
        features["complexity_score"] = complexity_score
        return features
    
    def _record_system_metrics(self):
        """Record current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_metric = {
                "timestamp": datetime.utcnow(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            }
            
            self.system_metrics.append(system_metric)
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {str(e)}")
    
    def get_performance_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Filter recent queries
        recent_queries = [
            q for q in self.query_metrics["all"] 
            if q["timestamp"] > cutoff_time
        ]
        
        if not recent_queries:
            return {"message": "No queries in the specified time window"}
        
        # Calculate statistics
        execution_times = [q["execution_time"] for q in recent_queries]
        row_counts = [q["row_count"] for q in recent_queries]
        
        summary = {
            "time_window_hours": time_window_hours,
            "total_queries": len(recent_queries),
            "successful_queries": len([q for q in recent_queries if q["status"] == "success"]),
            "failed_queries": len([q for q in recent_queries if q["status"] == "error"]),
            "success_rate": len([q for q in recent_queries if q["status"] == "success"]) / len(recent_queries) * 100,
            
            "performance_metrics": {
                "avg_execution_time": round(mean(execution_times), 3),
                "median_execution_time": round(median(execution_times), 3),
                "max_execution_time": round(max(execution_times), 3),
                "min_execution_time": round(min(execution_times), 3),
                "avg_row_count": round(mean(row_counts), 0),
                "total_rows_processed": sum(row_counts)
            },
            
            "query_complexity": {
                "high_complexity": len([q for q in recent_queries if q["complexity"]["estimated_complexity"] == "high"]),
                "medium_complexity": len([q for q in recent_queries if q["complexity"]["estimated_complexity"] == "medium"]),
                "low_complexity": len([q for q in recent_queries if q["complexity"]["estimated_complexity"] == "low"])
            },
            
            "slow_queries_count": len([q for q in recent_queries if q["execution_time"] > self.slow_query_threshold]),
            "most_active_users": self._get_most_active_users(recent_queries),
            "common_errors": dict(self.error_metrics),
            "system_health": self._get_system_health_summary()
        }
        
        return summary
    
    def _get_most_active_users(self, queries: List[Dict], top_n: int = 5) -> List[Dict]:
        """Get most active users by query count"""
        user_counts = defaultdict(int)
        for q in queries:
            user_counts[q["user_id"]] += 1
        
        return [
            {"user_id": user_id, "query_count": count}
            for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ]
    
    def _get_system_health_summary(self) -> Dict[str, Any]:
        """Get system health summary"""
        if not self.system_metrics:
            return {"status": "no_data"}
        
        recent_metrics = list(self.system_metrics)[-10:]  # Last 10 measurements
        
        return {
            "status": "healthy",
            "avg_cpu_percent": round(mean([m["cpu_percent"] for m in recent_metrics]), 1),
            "avg_memory_percent": round(mean([m["memory_percent"] for m in recent_metrics]), 1),
            "avg_disk_percent": round(mean([m["disk_percent"] for m in recent_metrics]), 1),
            "memory_available_gb": round(recent_metrics[-1]["memory_available_gb"], 2),
            "disk_free_gb": round(recent_metrics[-1]["disk_free_gb"], 2)
        }
    
    def get_slow_queries_report(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get report of slowest queries"""
        sorted_slow_queries = sorted(
            list(self.slow_queries), 
            key=lambda x: x["execution_time"], 
            reverse=True
        )
        
        return [
            {
                "query_snippet": q["query_snippet"],
                "execution_time": q["execution_time"],
                "row_count": q["row_count"],
                "user_id": q["user_id"],
                "timestamp": q["timestamp"].isoformat(),
                "complexity": q["complexity"]["estimated_complexity"],
                "complexity_score": q["complexity"]["complexity_score"]
            }
            for q in sorted_slow_queries[:limit]
        ]
    
    def get_user_performance_stats(self, user_id: str) -> Dict[str, Any]:
        """Get performance statistics for a specific user"""
        if user_id not in self.user_metrics:
            return {"error": "User not found"}
        
        user_data = self.user_metrics[user_id]
        user_queries = self.query_metrics[user_id]
        
        if not user_queries:
            return {"user_id": user_id, "queries": 0}
        
        recent_queries = [q for q in user_queries if q["timestamp"] > datetime.utcnow() - timedelta(hours=24)]
        execution_times = [q["execution_time"] for q in recent_queries]
        
        return {
            "user_id": user_id,
            "total_queries": user_data["queries"],
            "total_execution_time": round(user_data["total_time"], 2),
            "error_count": user_data["errors"],
            "error_rate": round(user_data["errors"] / user_data["queries"] * 100, 2) if user_data["queries"] > 0 else 0,
            "avg_execution_time": round(user_data["total_time"] / user_data["queries"], 3) if user_data["queries"] > 0 else 0,
            "recent_24h": {
                "queries": len(recent_queries),
                "avg_execution_time": round(mean(execution_times), 3) if execution_times else 0,
                "max_execution_time": round(max(execution_times), 3) if execution_times else 0
            }
        }
    
    def clear_metrics(self, older_than_hours: int = 168):  # Default: 1 week
        """Clear old metrics to free memory"""
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        # Clear old query metrics
        for user_id in self.query_metrics:
            self.query_metrics[user_id] = [
                q for q in self.query_metrics[user_id] 
                if q["timestamp"] > cutoff_time
            ]
        
        # Clear old slow queries
        self.slow_queries = deque([
            q for q in self.slow_queries 
            if q["timestamp"] > cutoff_time
        ], maxlen=100)
        
        logger.info(f"Cleared metrics older than {older_than_hours} hours")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
