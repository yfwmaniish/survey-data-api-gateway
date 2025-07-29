from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional
import logging
from app.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for ORM models
Base = declarative_base()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Database manager for executing queries and getting metadata"""
    
    def __init__(self):
        self.engine = engine
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries representing the query results
            
        Raises:
            SQLAlchemyError: If query execution fails
        """
        try:
            with self.engine.connect() as connection:
                # Set query timeout
                connection = connection.execution_options(
                    autocommit=True,
                    compiled_cache={},
                    query_timeout=settings.max_query_timeout
                )
                
                result = connection.execute(text(query), params or {})
                
                # Convert to list of dictionaries
                columns = result.keys()
                rows = result.fetchmany(settings.max_result_rows)
                
                return [dict(zip(columns, row)) for row in rows]
                
        except SQLAlchemyError as e:
            logger.error(f"Database query failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {str(e)}")
            raise SQLAlchemyError(f"Query execution failed: {str(e)}")
    
    def get_table_names(self) -> List[str]:
        """Get all table names in the database"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
        try:
            result = self.execute_query(query)
            return [row['table_name'] for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get table names: {str(e)}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries with column information
        """
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = :table_name
        ORDER BY ordinal_position;
        """
        try:
            return self.execute_query(query, {"table_name": table_name})
        except SQLAlchemyError as e:
            logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.warning(f"Database connection test failed: {str(e)}")
            return False


# Create database manager instance
db_manager = DatabaseManager()
