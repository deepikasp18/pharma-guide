"""
Connection pooling and management for Neptune database
"""
import asyncio
import logging
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from .database import NeptuneConnection, NeptuneConnectionError

logger = logging.getLogger(__name__)

@dataclass
class ConnectionStats:
    """Connection statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

class ConnectionPool:
    """Neptune connection pool manager"""
    
    def __init__(self, min_size: int = 2, max_size: int = 10, 
                 max_idle_time: int = 300, health_check_interval: int = 60):
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time  # seconds
        self.health_check_interval = health_check_interval  # seconds
        
        self._pool: List[NeptuneConnection] = []
        self._in_use: Dict[id, NeptuneConnection] = {}
        self._last_used: Dict[id, datetime] = {}
        self._lock = asyncio.Lock()
        self._stats = ConnectionStats()
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the connection pool"""
        async with self._lock:
            if self._initialized:
                return
            
            # Create minimum number of connections
            for _ in range(self.min_size):
                try:
                    conn = NeptuneConnection()
                    await conn.connect()
                    self._pool.append(conn)
                    self._last_used[id(conn)] = datetime.utcnow()
                    self._stats.total_connections += 1
                    logger.info("Created connection in pool")
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")
                    self._stats.failed_connections += 1
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._initialized = True
            
            logger.info(f"Connection pool initialized with {len(self._pool)} connections")
    
    async def get_connection(self) -> NeptuneConnection:
        """Get a connection from the pool"""
        async with self._lock:
            # Try to get an idle connection
            if self._pool:
                conn = self._pool.pop()
                self._in_use[id(conn)] = conn
                self._last_used[id(conn)] = datetime.utcnow()
                self._stats.active_connections += 1
                self._stats.idle_connections = len(self._pool)
                logger.debug("Retrieved connection from pool")
                return conn
            
            # Create new connection if under max size
            if len(self._in_use) < self.max_size:
                try:
                    conn = NeptuneConnection()
                    await conn.connect()
                    self._in_use[id(conn)] = conn
                    self._last_used[id(conn)] = datetime.utcnow()
                    self._stats.total_connections += 1
                    self._stats.active_connections += 1
                    logger.info("Created new connection for pool")
                    return conn
                except Exception as e:
                    logger.error(f"Failed to create new connection: {e}")
                    self._stats.failed_connections += 1
                    self._stats.last_error = str(e)
                    self._stats.last_error_time = datetime.utcnow()
                    raise NeptuneConnectionError(f"Cannot create connection: {e}")
            
            # Pool is exhausted
            raise NeptuneConnectionError("Connection pool exhausted")
    
    async def return_connection(self, conn: NeptuneConnection) -> None:
        """Return a connection to the pool"""
        async with self._lock:
            conn_id = id(conn)
            
            if conn_id not in self._in_use:
                logger.warning("Attempting to return connection not in use")
                return
            
            # Remove from in-use
            del self._in_use[conn_id]
            self._stats.active_connections -= 1
            
            # Check if connection is still healthy
            try:
                # Simple health check
                if hasattr(conn, 'g') and conn.g:
                    conn.g.V().limit(1).toList()
                
                # Return to pool if under min size or add to idle
                if len(self._pool) < self.min_size:
                    self._pool.append(conn)
                    self._last_used[conn_id] = datetime.utcnow()
                    self._stats.idle_connections = len(self._pool)
                    logger.debug("Returned connection to pool")
                else:
                    # Close excess connection
                    await conn.close()
                    if conn_id in self._last_used:
                        del self._last_used[conn_id]
                    self._stats.total_connections -= 1
                    logger.debug("Closed excess connection")
                    
            except Exception as e:
                logger.error(f"Connection health check failed, closing: {e}")
                await conn.close()
                if conn_id in self._last_used:
                    del self._last_used[conn_id]
                self._stats.total_connections -= 1
                self._stats.failed_connections += 1
    
    @asynccontextmanager
    async def get_connection_context(self):
        """Context manager for getting and returning connections"""
        conn = await self.get_connection()
        try:
            yield conn
        finally:
            await self.return_connection(conn)
    
    async def _health_check_loop(self) -> None:
        """Background task for connection health checks"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._cleanup_idle_connections()
                await self._health_check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections that have exceeded max idle time"""
        async with self._lock:
            now = datetime.utcnow()
            connections_to_remove = []
            
            for conn in self._pool[:]:  # Create a copy to iterate
                conn_id = id(conn)
                last_used = self._last_used.get(conn_id, now)
                
                if (now - last_used).total_seconds() > self.max_idle_time:
                    connections_to_remove.append(conn)
            
            # Remove and close idle connections (but keep minimum)
            for conn in connections_to_remove:
                if len(self._pool) > self.min_size:
                    self._pool.remove(conn)
                    conn_id = id(conn)
                    if conn_id in self._last_used:
                        del self._last_used[conn_id]
                    await conn.close()
                    self._stats.total_connections -= 1
                    logger.debug("Closed idle connection")
            
            self._stats.idle_connections = len(self._pool)
    
    async def _health_check_connections(self) -> None:
        """Health check all connections in the pool"""
        async with self._lock:
            healthy_connections = []
            
            for conn in self._pool:
                try:
                    # Simple health check
                    if hasattr(conn, 'g') and conn.g:
                        conn.g.V().limit(1).toList()
                    healthy_connections.append(conn)
                except Exception as e:
                    logger.warning(f"Unhealthy connection detected, removing: {e}")
                    conn_id = id(conn)
                    if conn_id in self._last_used:
                        del self._last_used[conn_id]
                    await conn.close()
                    self._stats.total_connections -= 1
                    self._stats.failed_connections += 1
            
            self._pool = healthy_connections
            self._stats.idle_connections = len(self._pool)
            
            # Ensure minimum connections
            while len(self._pool) < self.min_size:
                try:
                    conn = NeptuneConnection()
                    await conn.connect()
                    self._pool.append(conn)
                    self._last_used[id(conn)] = datetime.utcnow()
                    self._stats.total_connections += 1
                    logger.info("Added connection to maintain minimum pool size")
                except Exception as e:
                    logger.error(f"Failed to create replacement connection: {e}")
                    break
            
            self._stats.idle_connections = len(self._pool)
    
    async def close_all(self) -> None:
        """Close all connections and shutdown the pool"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            # Close all idle connections
            for conn in self._pool:
                await conn.close()
            self._pool.clear()
            
            # Close all in-use connections
            for conn in self._in_use.values():
                await conn.close()
            self._in_use.clear()
            
            self._last_used.clear()
            self._stats = ConnectionStats()
            self._initialized = False
            
            logger.info("Connection pool closed")
    
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics"""
        self._stats.idle_connections = len(self._pool)
        self._stats.active_connections = len(self._in_use)
        return self._stats

# Global connection pool instance
connection_pool = ConnectionPool()