"""
Data storage and persistence for the Fantasy Football Auto-Lineup Bot.
Handles saving and loading of decisions, performance metrics, and cached data.
"""

import json
import logging
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import pickle

from ..data.models import DecisionLog, PerformanceMetrics, Player, Lineup
from ..config.settings import get_config


logger = logging.getLogger(__name__)


class DataStorage:
    """Manages data persistence for the fantasy football bot."""
    
    def __init__(self, db_path: str = "fantasy_bot.db"):
        self.config = get_config()
        self.db_path = Path(db_path)
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create decisions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        week INTEGER NOT NULL,
                        season INTEGER NOT NULL,
                        decision_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        players_involved TEXT,
                        reasoning TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        was_executed BOOLEAN NOT NULL,
                        outcome TEXT
                    )
                """)
                
                # Create performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        week INTEGER NOT NULL,
                        season INTEGER NOT NULL,
                        projected_points REAL NOT NULL,
                        actual_points REAL NOT NULL,
                        accuracy REAL NOT NULL,
                        decision_quality REAL NOT NULL,
                        notes TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)
                
                # Create player cache table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_cache (
                        player_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        ttl_hours INTEGER NOT NULL
                    )
                """)
                
                # Create lineup history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS lineup_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team_id TEXT NOT NULL,
                        week INTEGER NOT NULL,
                        season INTEGER NOT NULL,
                        lineup_data TEXT NOT NULL,
                        total_projected_points REAL NOT NULL,
                        risk_level TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_decision(self, decision: DecisionLog) -> bool:
        """Save a decision to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO decisions (
                        timestamp, week, season, decision_type, description,
                        players_involved, reasoning, confidence, was_executed, outcome
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision.timestamp.isoformat(),
                    decision.week,
                    decision.season,
                    decision.decision_type,
                    decision.description,
                    json.dumps(decision.players_involved),
                    decision.reasoning,
                    decision.confidence,
                    decision.was_executed,
                    decision.outcome
                ))
                
                conn.commit()
                logger.info(f"Saved decision: {decision.decision_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving decision: {e}")
            return False
    
    def get_decisions(self, week: Optional[int] = None, season: Optional[int] = None,
                     decision_type: Optional[str] = None, limit: int = 100) -> List[DecisionLog]:
        """Retrieve decisions from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM decisions WHERE 1=1"
                params = []
                
                if week is not None:
                    query += " AND week = ?"
                    params.append(week)
                
                if season is not None:
                    query += " AND season = ?"
                    params.append(season)
                
                if decision_type is not None:
                    query += " AND decision_type = ?"
                    params.append(decision_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                decisions = []
                for row in rows:
                    decision = DecisionLog(
                        timestamp=datetime.fromisoformat(row[1]),
                        week=row[2],
                        season=row[3],
                        decision_type=row[4],
                        description=row[5],
                        players_involved=json.loads(row[6]) if row[6] else [],
                        reasoning=row[7],
                        confidence=row[8],
                        was_executed=bool(row[9]),
                        outcome=row[10]
                    )
                    decisions.append(decision)
                
                return decisions
                
        except Exception as e:
            logger.error(f"Error retrieving decisions: {e}")
            return []
    
    def save_performance_metrics(self, metrics: PerformanceMetrics) -> bool:
        """Save performance metrics to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO performance_metrics (
                        week, season, projected_points, actual_points,
                        accuracy, decision_quality, notes, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.week,
                    metrics.season,
                    metrics.projected_points,
                    metrics.actual_points,
                    metrics.accuracy,
                    metrics.decision_quality,
                    metrics.notes,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"Saved performance metrics for week {metrics.week}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
            return False
    
    def get_performance_metrics(self, week: Optional[int] = None, 
                              season: Optional[int] = None) -> List[PerformanceMetrics]:
        """Retrieve performance metrics from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM performance_metrics WHERE 1=1"
                params = []
                
                if week is not None:
                    query += " AND week = ?"
                    params.append(week)
                
                if season is not None:
                    query += " AND season = ?"
                    params.append(season)
                
                query += " ORDER BY timestamp DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                metrics = []
                for row in rows:
                    metric = PerformanceMetrics(
                        week=row[1],
                        season=row[2],
                        projected_points=row[3],
                        actual_points=row[4],
                        accuracy=row[5],
                        decision_quality=row[6],
                        notes=row[7] or ""
                    )
                    metrics.append(metric)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error retrieving performance metrics: {e}")
            return []
    
    def cache_player_data(self, player_id: str, data: Any, ttl_hours: int = 24) -> bool:
        """Cache player data in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Serialize data
                serialized_data = pickle.dumps(data)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO player_cache (
                        player_id, data, timestamp, ttl_hours
                    ) VALUES (?, ?, ?, ?)
                """, (
                    player_id,
                    serialized_data,
                    datetime.now().isoformat(),
                    ttl_hours
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error caching player data: {e}")
            return False
    
    def get_cached_player_data(self, player_id: str) -> Optional[Any]:
        """Retrieve cached player data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT data, timestamp, ttl_hours FROM player_cache 
                    WHERE player_id = ?
                """, (player_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                data, timestamp_str, ttl_hours = row
                timestamp = datetime.fromisoformat(timestamp_str)
                
                # Check if data is still valid
                if datetime.now() - timestamp > timedelta(hours=ttl_hours):
                    # Data expired, remove it
                    cursor.execute("DELETE FROM player_cache WHERE player_id = ?", (player_id,))
                    conn.commit()
                    return None
                
                # Deserialize and return data
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Error retrieving cached player data: {e}")
            return None
    
    def save_lineup_history(self, lineup: Lineup, total_projected_points: float,
                          risk_level: str) -> bool:
        """Save lineup to history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Serialize lineup data
                lineup_data = pickle.dumps(lineup)
                
                cursor.execute("""
                    INSERT INTO lineup_history (
                        team_id, week, season, lineup_data, total_projected_points,
                        risk_level, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    lineup.team_id,
                    lineup.week,
                    lineup.season,
                    lineup_data,
                    total_projected_points,
                    risk_level,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"Saved lineup history for week {lineup.week}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving lineup history: {e}")
            return False
    
    def get_lineup_history(self, team_id: str, week: Optional[int] = None,
                          season: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve lineup history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM lineup_history WHERE team_id = ?"
                params = [team_id]
                
                if week is not None:
                    query += " AND week = ?"
                    params.append(week)
                
                if season is not None:
                    query += " AND season = ?"
                    params.append(season)
                
                query += " ORDER BY timestamp DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    lineup = pickle.loads(row[4])  # Deserialize lineup data
                    history.append({
                        'id': row[0],
                        'team_id': row[1],
                        'week': row[2],
                        'season': row[3],
                        'lineup': lineup,
                        'total_projected_points': row[5],
                        'risk_level': row[6],
                        'timestamp': datetime.fromisoformat(row[7])
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error retrieving lineup history: {e}")
            return []
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries and return count of cleared items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM player_cache 
                    WHERE datetime(timestamp) + ttl_hours || ' hours' < datetime('now')
                """)
                
                cleared_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {cleared_count} expired cache entries")
                return cleared_count
                
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count decisions
                cursor.execute("SELECT COUNT(*) FROM decisions")
                stats['total_decisions'] = cursor.fetchone()[0]
                
                # Count performance metrics
                cursor.execute("SELECT COUNT(*) FROM performance_metrics")
                stats['total_metrics'] = cursor.fetchone()[0]
                
                # Count cached players
                cursor.execute("SELECT COUNT(*) FROM player_cache")
                stats['cached_players'] = cursor.fetchone()[0]
                
                # Count lineup history
                cursor.execute("SELECT COUNT(*) FROM lineup_history")
                stats['lineup_history'] = cursor.fetchone()[0]
                
                # Database size
                stats['database_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False


# Global storage instance
storage = DataStorage()

