from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, List, Any, Optional
import json
import asyncio
import logging
from datetime import datetime
import uuid

from app.database import db_manager
from app.utils.auth import verify_token, verify_api_key
from app.utils.query_validator import query_validator
from app.utils.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}
        
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str, user_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {str(e)}")
                # Connection might be dead, remove it
                await self._cleanup_connection(connection_id)
    
    async def broadcast_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a user"""
        if user_id in self.user_connections:
            dead_connections = []
            for connection_id in self.user_connections[user_id]:
                try:
                    await self.send_personal_message(message, connection_id)
                except:
                    dead_connections.append(connection_id)
            
            # Clean up dead connections
            for connection_id in dead_connections:
                self.disconnect(connection_id, user_id)
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up a dead connection"""
        # Find and remove from user connections
        for user_id, connections in self.user_connections.items():
            if connection_id in connections:
                self.disconnect(connection_id, user_id)
                break

# Global connection manager
manager = ConnectionManager()

async def authenticate_websocket(token: str) -> Dict[str, Any]:
    """Authenticate WebSocket connection"""
    try:
        # Try JWT first
        payload = verify_token(token)
        if "user_id" in payload:
            return {
                "user_id": payload["user_id"],
                "permissions": payload.get("permissions", ["read"]),
                "auth_type": "jwt"
            }
    except:
        pass
    
    try:
        # Try API key
        user_info = verify_api_key(token)
        user_info["auth_type"] = "api_key"
        return user_info
    except:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token"
    )

@router.websocket("/query")
async def websocket_query_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time query execution
    
    Expected message format:
    {
        "type": "auth",
        "token": "your-token-here"
    }
    
    {
        "type": "query",
        "query_id": "unique-id",
        "sql": "SELECT * FROM table",
        "params": {},
        "stream_results": true
    }
    """
    connection_id = str(uuid.uuid4())
    user_info = None
    
    try:
        # Wait for authentication
        auth_data = await websocket.receive_text()
        auth_message = json.loads(auth_data)
        
        if auth_message.get("type") != "auth":
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # Authenticate user
        token = auth_message.get("token")
        if not token:
            await websocket.close(code=4001, reason="Token required")
            return
        
        user_info = await authenticate_websocket(token)
        user_id = user_info["user_id"]
        
        # Register connection
        await manager.connect(websocket, connection_id, user_id)
        
        # Send authentication success
        await manager.send_personal_message({
            "type": "auth_success",
            "user_id": user_id,
            "connection_id": connection_id,
            "permissions": user_info["permissions"]
        }, connection_id)
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(message, connection_id, user_info)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "error": "Invalid JSON format"
                }, connection_id)
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                await manager.send_personal_message({
                    "type": "error",
                    "error": str(e)
                }, connection_id)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
    finally:
        if user_info:
            manager.disconnect(connection_id, user_info["user_id"])

async def handle_websocket_message(message: dict, connection_id: str, user_info: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "query":
        await handle_query_message(message, connection_id, user_info)
    elif message_type == "cancel_query":
        await handle_cancel_query(message, connection_id, user_info)
    elif message_type == "ping":
        await manager.send_personal_message({"type": "pong"}, connection_id)
    else:
        await manager.send_personal_message({
            "type": "error",
            "error": f"Unknown message type: {message_type}"
        }, connection_id)

async def handle_query_message(message: dict, connection_id: str, user_info: Dict[str, Any]):
    """Handle query execution via WebSocket"""
    query_id = message.get("query_id", str(uuid.uuid4()))
    sql = message.get("sql")
    params = message.get("params", {})
    stream_results = message.get("stream_results", False)
    
    if not sql:
        await manager.send_personal_message({
            "type": "query_error",
            "query_id": query_id,
            "error": "SQL query is required"
        }, connection_id)
        return
    
    # Check permissions
    if "query" not in user_info.get("permissions", []):
        await manager.send_personal_message({
            "type": "query_error",
            "query_id": query_id,
            "error": "Insufficient permissions for query execution"
        }, connection_id)
        return
    
    try:
        # Validate query
        query_validator.validate_query(sql)
        
        # Send query started message
        await manager.send_personal_message({
            "type": "query_started",
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Execute query
        start_time = datetime.utcnow()
        
        if stream_results:
            await execute_streaming_query(sql, params, query_id, connection_id, user_info, start_time)
        else:
            await execute_regular_query(sql, params, query_id, connection_id, user_info, start_time)
    
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        await manager.send_personal_message({
            "type": "query_error",
            "query_id": query_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)

async def execute_regular_query(sql: str, params: dict, query_id: str, 
                               connection_id: str, user_info: Dict[str, Any], start_time: datetime):
    """Execute regular query and send complete results"""
    try:
        # Execute query (this should be made async in production)
        result_data = db_manager.execute_query(sql, params)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Record performance
        performance_monitor.record_query_performance(
            user_info["user_id"], sql, execution_time, len(result_data)
        )
        
        # Send results
        await manager.send_personal_message({
            "type": "query_complete",
            "query_id": query_id,
            "data": result_data,
            "row_count": len(result_data),
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        performance_monitor.record_query_performance(
            user_info["user_id"], sql, execution_time, 0, "error", str(e)
        )
        raise

async def execute_streaming_query(sql: str, params: dict, query_id: str, 
                                 connection_id: str, user_info: Dict[str, Any], start_time: datetime):
    """Execute query with streaming results"""
    try:
        # This is a simplified streaming implementation
        # In production, you'd want to use async database cursors
        result_data = db_manager.execute_query(sql, params)
        
        # Stream results in chunks
        chunk_size = 100
        total_rows = len(result_data)
        
        for i in range(0, total_rows, chunk_size):
            chunk = result_data[i:i + chunk_size]
            
            await manager.send_personal_message({
                "type": "query_chunk",
                "query_id": query_id,
                "data": chunk,
                "chunk_number": i // chunk_size + 1,
                "total_chunks": (total_rows + chunk_size - 1) // chunk_size,
                "rows_in_chunk": len(chunk),
                "timestamp": datetime.utcnow().isoformat()
            }, connection_id)
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Send completion message
        await manager.send_personal_message({
            "type": "query_complete",
            "query_id": query_id,
            "total_rows": total_rows,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Record performance
        performance_monitor.record_query_performance(
            user_info["user_id"], sql, execution_time, total_rows
        )
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        performance_monitor.record_query_performance(
            user_info["user_id"], sql, execution_time, 0, "error", str(e)
        )
        raise

async def handle_cancel_query(message: dict, connection_id: str, user_info: Dict[str, Any]):
    """Handle query cancellation (placeholder implementation)"""
    query_id = message.get("query_id")
    
    # In a real implementation, you'd cancel the running query
    await manager.send_personal_message({
        "type": "query_cancelled",
        "query_id": query_id,
        "timestamp": datetime.utcnow().isoformat()
    }, connection_id)

@router.get("/connections")
async def get_active_connections():
    """Get information about active WebSocket connections (admin endpoint)"""
    return {
        "total_connections": len(manager.active_connections),
        "users_connected": len(manager.user_connections),
        "connections_per_user": {
            user_id: len(connections) 
            for user_id, connections in manager.user_connections.items()
        }
    }
