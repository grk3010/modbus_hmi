import sqlite3
import logging
import asyncio
import os
import shutil

logger = logging.getLogger(__name__)

# Use high-performance orjson if available, otherwise fall back to standard json
try:
    import orjson
    def dumps_json(obj):
        return orjson.dumps(obj).decode('utf-8')
    def loads_json(s):
        return orjson.loads(s)
except ImportError:
    import json
    def dumps_json(obj):
        return json.dumps(obj)
    def loads_json(s):
        return json.loads(s)


class DataLogger:
    def __init__(self, db_path="sensor_data.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        """Creates a connection with high-performance PRAGMAs tailored for CM4 flash storage."""
        conn = sqlite3.connect(self.db_path)
        # Enable Write-Ahead Logging to eliminate read/write blocking & reduce SD/eMMC wear
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        # Allocate 8MB cache in RAM
        conn.execute("PRAGMA cache_size = -8000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        return conn

    def update_db_path(self, storage_dir, migrate=False):
        """Updates the database file location dynamically and safely migrates historical data using SQLite Backup API."""
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
                # Use SQLite native backup API to safely copy data including all WAL pages
                with sqlite3.connect(old_path) as src_conn, sqlite3.connect(new_path) as dst_conn:
                    src_conn.backup(dst_conn)
                logger.info("Successfully copied database records to new location using SQLite backup API.")
                
                # Test connection to copied DB
                with sqlite3.connect(new_path) as test_conn:
                    test_conn.execute("SELECT count(*) FROM sensor_logs")
                
                try:
                    # Clean up old database and any WAL/SHM artifacts
                    for ext in ["", "-wal", "-shm", "-journal"]:
                        f_path = old_path + ext
                        if os.path.exists(f_path):
                            os.remove(f_path)
                    logger.info(f"Removed old database file(s): {old_path}")
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
            with self._connect() as conn:
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
                # Critical performance optimization: Indexes for range queries and pruning
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_logs_timestamp ON sensor_logs(timestamp);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_logs_port_ts ON sensor_logs(port, timestamp);')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def clear_database(self):
        """Deletes all records from the sensor_logs table and resets the auto-increment ID."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sensor_logs')
                cursor.execute('DELETE FROM sqlite_sequence WHERE name="sensor_logs"')
                conn.commit()
                # Run vacuum to reclaim disk space immediately
                cursor.execute('VACUUM')
                conn.commit()
                logger.info("Database successfully cleared and vacuumed.")
                return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    def prune_old_data(self, days: float):
        """Deletes records older than the specified number of days using the timestamp index."""
        if days <= 0:
            return False
            
        try:
            with self._connect() as conn:
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
        self.log_batch([(port, sensor_type, data)])

    async def log_data_async(self, port: int, sensor_type: str, data: dict):
        """Asynchronously log data to SQLite by running in a separate thread."""
        await asyncio.to_thread(self.log_data, port, sensor_type, data)

    def log_batch(self, records: list):
        """
        Inserts multiple sensor log records in a single database transaction.
        records: list of tuples: (port: int, sensor_type: str, data: dict)
        """
        if not records:
            return
            
        try:
            payloads = [
                (port, sensor_type, dumps_json(data))
                for port, sensor_type, data in records
                if data
            ]
            if not payloads:
                return

            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO sensor_logs (port, sensor_type, data)
                    VALUES (?, ?, ?)
                ''', payloads)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log batch data: {e}")

    async def log_batch_async(self, records: list):
        """Asynchronously log a batch of records to SQLite."""
        await asyncio.to_thread(self.log_batch, records)
        
    def get_historical_data(self, hours_back: float = 1.0, start_date: str = None, end_date: str = None):
        """
        Fetches historical sensor logs using an indexed timestamp scan and intelligent
        time-bucketing per port for large query ranges to prevent OOM/UI lag on CM4.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Determine bucketing interval in seconds for even sampling across all ports
                bucket_sec = 0
                if start_date:
                    import datetime
                    try:
                        s_dt = datetime.datetime.fromisoformat(start_date)
                        e_dt = datetime.datetime.fromisoformat(end_date) if end_date else datetime.datetime.now()
                        span_sec = max(3600.0, (e_dt - s_dt).total_seconds())
                        bucket_sec = int(max(10, span_sec // 350))
                    except Exception:
                        bucket_sec = 120
                else:
                    if hours_back > 168:      # > 1 week (e.g. 1 month)
                        bucket_sec = 7200     # 2 hour buckets (~360 pts/port)
                    elif hours_back > 24:     # > 24 hours (e.g. 1 week)
                        bucket_sec = 1800     # 30 min buckets (~336 pts/port)
                    elif hours_back > 6:      # > 6 hours (e.g. 24 hours)
                        bucket_sec = 240      # 4 min buckets (~360 pts/port)
                    elif hours_back > 2:      # > 2 hours (e.g. 6 hours)
                        bucket_sec = 60       # 1 min buckets (~360 pts/port)
                    else:
                        bucket_sec = 0        # <= 2 hours: raw 10-second data

                if start_date:
                    params = [f"{start_date} 00:00:00" if len(start_date) <= 10 else start_date]
                    where_clause = "WHERE timestamp >= ?"
                    if end_date:
                        where_clause += " AND timestamp <= ?"
                        params.append(f"{end_date} 23:59:59" if len(end_date) <= 10 else end_date)
                        
                    if bucket_sec > 0:
                        query = f'''
                            SELECT timestamp, port, sensor_type, data 
                            FROM sensor_logs 
                            {where_clause}
                            GROUP BY port, CAST(strftime('%s', timestamp) / ? AS INTEGER)
                            ORDER BY timestamp ASC
                        '''
                        params.append(bucket_sec)
                    else:
                        query = f'''
                            SELECT timestamp, port, sensor_type, data 
                            FROM sensor_logs 
                            {where_clause}
                            ORDER BY timestamp ASC
                        '''
                    cursor.execute(query, params)
                else:
                    if bucket_sec > 0:
                        cursor.execute('''
                            SELECT timestamp, port, sensor_type, data 
                            FROM sensor_logs 
                            WHERE timestamp >= datetime('now', ? || ' hours')
                            GROUP BY port, CAST(strftime('%s', timestamp) / ? AS INTEGER)
                            ORDER BY timestamp ASC
                        ''', (f'-{hours_back}', bucket_sec))
                    else:
                        cursor.execute('''
                            SELECT timestamp, port, sensor_type, data 
                            FROM sensor_logs 
                            WHERE timestamp >= datetime('now', ? || ' hours')
                            ORDER BY timestamp ASC
                        ''', (f'-{hours_back}',))
                        
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    try:
                        parsed_data = loads_json(row[3])
                    except Exception:
                        parsed_data = {}
                    results.append({
                        "timestamp": row[0],
                        "port": row[1],
                        "sensor_type": row[2],
                        "data": parsed_data
                    })
                return results
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return []

    async def get_historical_data_async(self, hours_back: float = 1.0, start_date: str = None, end_date: str = None):
        """Asynchronously fetches historical data."""
        return await asyncio.to_thread(self.get_historical_data, hours_back, start_date, end_date)
