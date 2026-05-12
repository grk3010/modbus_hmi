import sqlite3
import json
import logging
import asyncio
import os
import shutil

logger = logging.getLogger(__name__)

class DataLogger:
    def __init__(self, db_path="sensor_data.db"):
        self.db_path = db_path
        self._init_db()

    def update_db_path(self, storage_dir, migrate=False):
        """Updates the database file location dynamically and optionally migrates historical data."""
        if not storage_dir or storage_dir.strip() in ["", ".", "./"]:
            new_path = "sensor_data.db"
        else:
            os.makedirs(storage_dir, exist_ok=True)
            new_path = os.path.join(storage_dir, "sensor_data.db")
            
        old_path = self.db_path
        if old_path == new_path:
            return True

        logger.info(f"Switching database path from {old_path} to {new_path}")
        
        if migrate and os.path.exists(old_path):
            try:
                if os.path.exists(new_path):
                    logger.warning(f"Target DB {new_path} already exists. Backing it up.")
                    shutil.copy2(new_path, new_path + ".bak")
                    
                shutil.copy2(old_path, new_path)
                logger.info("Successfully copied database records to new location.")
                
                # Test connection to copied DB
                with sqlite3.connect(new_path) as test_conn:
                    test_conn.execute("SELECT count(*) FROM sensor_logs")
                
                try:
                    os.remove(old_path)
                    logger.info(f"Removed old database file: {old_path}")
                except Exception as del_e:
                    logger.warning(f"Could not remove old DB file: {del_e}")
                    
            except Exception as e:
                logger.error(f"Migration failed: {e}. Reinitializing clean DB at target.")
                
        self.db_path = new_path
        self._init_db()
        return True

    async def update_db_path_async(self, storage_dir, migrate=False):
        return await asyncio.to_thread(self.update_db_path, storage_dir, migrate)

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

    def clear_database(self):
        """Deletes all records from the sensor_logs table and resets the auto-increment ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sensor_logs')
                cursor.execute('DELETE FROM sqlite_sequence WHERE name="sensor_logs"')
                conn.commit()
                logger.info("Database successfully cleared.")
                return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    def prune_old_data(self, days: float):
        """Deletes records from the sensor_logs table that are older than the specified number of days."""
        if days <= 0:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM sensor_logs 
                    WHERE timestamp < datetime('now', ? || ' days')
                ''', (f'-{days}',))
                deleted_rows = cursor.rowcount
                conn.commit()
                if deleted_rows > 0:
                    logger.info(f"Pruned {deleted_rows} old records from the database.")
                return True
        except Exception as e:
            logger.error(f"Failed to prune old data: {e}")
            return False

    async def prune_old_data_async(self, days: float):
        """Asynchronously prune old data from SQLite."""
        return await asyncio.to_thread(self.prune_old_data, days)

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
                cursor.execute('''
                    SELECT timestamp, port, sensor_type, data 
                    FROM sensor_logs 
                    WHERE timestamp >= datetime('now', ? || ' hours')
                    ORDER BY timestamp ASC
                ''', (f'-{hours_back}',))
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
