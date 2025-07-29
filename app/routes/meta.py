from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

from app.database import db_manager
from app.utils.auth import require_read

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metadata"])

@router.get("/datasets", response_model=List[str])
async def get_datasets(
    current_user: Dict[str, Any] = Depends(require_read)
) -> List[str]:
    """
    Get names of all available datasets (tables)
    """
    try:
        table_names = db_manager.get_table_names()
        logger.info(f"Datasets requested by user {current_user['user_id']}")
        return table_names
    except Exception as e:
        logger.error(f"Failed to retrieve datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dataset names"
        )

@router.get("/schema", response_model=List[Dict[str, Any]])
async def get_schema(
    table: str,
    current_user: Dict[str, Any] = Depends(require_read)
) -> List[Dict[str, Any]]:
    """
    Get schema for a specific dataset (table)
    """
    try:
        schema_info = db_manager.get_table_schema(table)
        logger.info(f"Schema requested for table '{table}' by user {current_user['user_id']}")
        return schema_info
    except Exception as e:
        logger.error(f"Failed to retrieve schema for table '{table}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema for table '{table}'"
        )
