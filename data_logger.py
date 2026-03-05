import sqlite3
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class DataLogger:
    def __init__(self, db_path="sensor_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensor_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        port INTEGER,
                        sensor_type TEXT,
                        data JSON
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def log_data(self, port: int, sensor_type: str, data: dict):
        if not data:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sensor_logs (port, sensor_type, data)
                    VALUES (?, ?, ?)
                ''', (port, sensor_type, json.dumps(data)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log data for port {port}: {e}")

    async def log_data_async(self, port: int, sensor_type: str, data: dict):
        """Asynchronously log data to SQLite by running in a separate thread to prevent blocking."""
        await asyncio.to_thread(self.log_data, port, sensor_type, data)
        
    def get_historical_data(self, hours_back: float = 1.0):
        """Fetches historical sensor logs from the last X hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT timestamp, port, sensor_type, data 
                    FROM sensor_logs 
                    WHERE timestamp >= datetime('now', '-{hours_back} hours')
                    ORDER BY timestamp ASC
                ''')
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        "timestamp": row[0],
                        "port": row[1],
                        "sensor_type": row[2],
                        "data": json.loads(row[3])
                    })
                return results
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return []

    async def get_historical_data_async(self, hours_back: float = 1.0):
        """Asynchronously fetches historical data."""
        return await asyncio.to_thread(self.get_historical_data, hours_back)
