import re
from typing import List, Set
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# Dangerous SQL keywords that should be blocked
DANGEROUS_KEYWORDS = {
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE',
    'REPLACE', 'MERGE', 'EXEC', 'EXECUTE', 'CALL', 'DECLARE', 'SET',
    'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'LOAD',
    '--', '/*', '*/', 'xp_', 'sp_'
}

# Allowed SQL keywords for SELECT queries
ALLOWED_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
    'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS',
    'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'AS', 'CASE',
    'WHEN', 'THEN', 'ELSE', 'END', 'UNION', 'ALL', 'WITH', 'CTE'
}

# Common SQL injection patterns
INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)",
    r"UNION\s+SELECT",
    r"--\s",
    r"/\*.*\*/",
    r"xp_\w+",
    r"sp_\w+",
    r"@@\w+",
    r"char\(\d+\)",
    r"0x[0-9a-f]+",
    r"benchmark\s*\(",
    r"sleep\s*\(",
    r"waitfor\s+delay"
]


class QueryValidator:
    """SQL query validator to prevent SQL injection and enforce security policies"""
    
    def __init__(self):
        self.dangerous_keywords = DANGEROUS_KEYWORDS
        self.allowed_keywords = ALLOWED_KEYWORDS
        self.injection_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS]
    
    def validate_query(self, query: str) -> bool:
        """
        Validate a SQL query for security issues
        
        Args:
            query: SQL query string to validate
            
        Returns:
            True if query is safe, raises HTTPException if not
            
        Raises:
            HTTPException: If query contains dangerous elements
        """
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        # Normalize query
        normalized_query = query.strip().upper()
        
        # Check if query starts with SELECT
        if not normalized_query.startswith('SELECT'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only SELECT queries are allowed"
            )
        
        # Check for dangerous keywords
        self._check_dangerous_keywords(query)
        
        # Check for SQL injection patterns
        self._check_injection_patterns(query)
        
        # Check for multiple statements
        self._check_multiple_statements(query)
        
        # Validate basic SQL structure
        self._validate_sql_structure(query)
        
        logger.info(f"Query validation passed for: {query[:100]}...")
        return True
    
    def _check_dangerous_keywords(self, query: str) -> None:
        """Check for dangerous SQL keywords"""
        query_upper = query.upper()
        
        for keyword in self.dangerous_keywords:
            if keyword in query_upper:
                logger.warning(f"Dangerous keyword detected: {keyword}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dangerous keyword '{keyword}' is not allowed"
                )
    
    def _check_injection_patterns(self, query: str) -> None:
        """Check for common SQL injection patterns"""
        for pattern in self.injection_patterns:
            if pattern.search(query):
                logger.warning(f"SQL injection pattern detected: {pattern.pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Query contains potentially dangerous patterns"
                )
    
    def _check_multiple_statements(self, query: str) -> None:
        """Check for multiple SQL statements"""
        # Remove string literals to avoid false positives
        cleaned_query = re.sub(r"'[^']*'", "", query)
        cleaned_query = re.sub(r'"[^"]*"', "", cleaned_query)
        
        # Count semicolons (excluding those in comments)
        semicolon_count = cleaned_query.count(';')
        
        # Allow one trailing semicolon
        if semicolon_count > 1 or (semicolon_count == 1 and not query.rstrip().endswith(';')):
            logger.warning("Multiple statements detected in query")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple SQL statements are not allowed"
            )
    
    def _validate_sql_structure(self, query: str) -> None:
        """Basic SQL structure validation"""
        # Check for balanced parentheses
        open_parens = query.count('(')
        close_parens = query.count(')')
        
        if open_parens != close_parens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unbalanced parentheses in query"
            )
        
        # Check for balanced quotes
        single_quotes = query.count("'")
        double_quotes = query.count('"')
        
        if single_quotes % 2 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unbalanced single quotes in query"
            )
        
        if double_quotes % 2 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unbalanced double quotes in query"
            )
    
    def get_query_info(self, query: str) -> dict:
        """
        Extract information about the query
        
        Args:
            query: SQL query string
            
        Returns:
            Dictionary with query information
        """
        info = {
            "query_type": "SELECT",
            "estimated_complexity": "low",
            "contains_joins": False,
            "contains_subqueries": False,
            "contains_aggregation": False
        }
        
        query_upper = query.upper()
        
        # Check for joins
        join_keywords = ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'OUTER JOIN']
        if any(keyword in query_upper for keyword in join_keywords):
            info["contains_joins"] = True
            info["estimated_complexity"] = "medium"
        
        # Check for subqueries
        if '(' in query and 'SELECT' in query[query.find('('):]:
            info["contains_subqueries"] = True
            info["estimated_complexity"] = "high"
        
        # Check for aggregation
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP BY']
        if any(func in query_upper for func in agg_functions):
            info["contains_aggregation"] = True
        
        return info


# Create validator instance
query_validator = QueryValidator()
