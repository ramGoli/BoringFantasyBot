"""
Data models for the Fantasy Football Auto-Lineup Bot.
Defines the structure for players, teams, lineups, and other entities.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class Position(Enum):
    """Fantasy football positions."""
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"
    FLEX = "FLEX"
    SUPER_FLEX = "SUPER_FLEX"
    BN = "BN"  # Bench


class InjuryStatus(Enum):
    """Player injury status."""
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"
    DOUBTFUL = "doubtful"
    OUT = "out"
    IR = "ir"


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Team:
    """NFL team information."""
    team_id: str
    name: str
    abbreviation: str
    city: str
    conference: str
    division: str


@dataclass
class PlayerStats:
    """Player statistics for a specific week."""
    week: int
    season: int
    passing_yards: float = 0
    passing_touchdowns: float = 0
    passing_interceptions: float = 0
    rushing_yards: float = 0
    rushing_touchdowns: float = 0
    receiving_yards: float = 0
    receiving_touchdowns: float = 0
    receptions: float = 0
    field_goals_made: float = 0
    field_goals_attempted: float = 0
    extra_points_made: float = 0
    extra_points_attempted: float = 0
    sacks: float = 0
    interceptions: float = 0
    fumbles_recovered: float = 0
    touchdowns: float = 0
    points_allowed: float = 0
    fantasy_points: float = 0
    
    def get_total_touchdowns(self) -> float:
        """Get total touchdowns (passing + rushing + receiving)."""
        return self.passing_touchdowns + self.rushing_touchdowns + self.receiving_touchdowns


@dataclass
class PlayerProjection:
    """Player projection for upcoming week."""
    week: int
    season: int
    projected_points: float
    confidence: float  # 0.0 to 1.0
    source: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InjuryInfo:
    """Player injury information."""
    status: InjuryStatus
    description: str
    probability_of_playing: Optional[float] = None  # 0.0 to 1.0
    last_updated: datetime = field(default_factory=datetime.now)
    source: str = ""


@dataclass
class WeatherInfo:
    """Weather information for a game."""
    temperature: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation_chance: Optional[float] = None
    humidity: Optional[float] = None
    is_dome: bool = False
    description: str = ""


@dataclass
class MatchupInfo:
    """Information about a player's matchup."""
    opponent_team: Team
    opponent_defense_ranking: Optional[int] = None
    game_total: Optional[float] = None
    spread: Optional[float] = None
    weather: Optional[WeatherInfo] = None
    game_time: Optional[datetime] = None
    is_home: bool = True


@dataclass
class Player:
    """Fantasy football player information."""
    player_id: str
    name: str
    position: Position
    team: Team
    nfl_team: Team
    eligible_positions: List[Position] = field(default_factory=list)
    injury_info: Optional[InjuryInfo] = None
    stats: List[PlayerStats] = field(default_factory=list)
    projections: List[PlayerProjection] = field(default_factory=list)
    matchup: Optional[MatchupInfo] = None
    bye_week: Optional[int] = None
    is_on_roster: bool = False
    is_starting: bool = False
    roster_position: Optional[str] = None
    
    def get_recent_stats(self, weeks: int = 4) -> List[PlayerStats]:
        """Get recent stats for the specified number of weeks."""
        return sorted(self.stats, key=lambda x: x.week, reverse=True)[:weeks]
    
    def get_average_points(self, weeks: int = 4) -> float:
        """Get average fantasy points over recent weeks."""
        recent_stats = self.get_recent_stats(weeks)
        if not recent_stats:
            return 0.0
        return sum(stat.fantasy_points for stat in recent_stats) / len(recent_stats)
    
    def get_trend(self, weeks: int = 4) -> float:
        """Get point trend over recent weeks (positive = improving)."""
        recent_stats = self.get_recent_stats(weeks)
        if len(recent_stats) < 2:
            return 0.0
        
        # Simple linear trend calculation
        points = [stat.fantasy_points for stat in recent_stats]
        return (points[0] - points[-1]) / len(points)
    
    def get_latest_projection(self) -> Optional[PlayerProjection]:
        """Get the most recent projection."""
        if not self.projections:
            return None
        return max(self.projections, key=lambda x: x.timestamp)


@dataclass
class LineupSlot:
    """A position slot in the fantasy lineup."""
    position: Position
    player: Optional[Player] = None
    is_filled: bool = False
    is_required: bool = True


@dataclass
class Lineup:
    """Fantasy football lineup configuration."""
    team_id: str
    week: int
    season: int
    slots: List[LineupSlot] = field(default_factory=list)
    total_projected_points: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_starting_players(self) -> List[Player]:
        """Get all starting players in the lineup."""
        return [slot.player for slot in self.slots if slot.player is not None]
    
    def get_player_by_position(self, position: Position) -> Optional[Player]:
        """Get player in a specific position slot."""
        for slot in self.slots:
            if slot.position == position and slot.player:
                return slot.player
        return None
    
    def set_player(self, position: Position, player: Player) -> bool:
        """Set a player in a specific position slot."""
        for slot in self.slots:
            if slot.position == position:
                slot.player = player
                slot.is_filled = True
                return True
        return False
    
    def remove_player(self, position: Position) -> bool:
        """Remove player from a specific position slot."""
        for slot in self.slots:
            if slot.position == position:
                slot.player = None
                slot.is_filled = False
                return True
        return False


@dataclass
class LeagueSettings:
    """Fantasy league settings and rules."""
    league_id: str
    name: str
    season: int
    roster_positions: Dict[str, int] = field(default_factory=dict)
    scoring_settings: Dict[str, float] = field(default_factory=dict)
    waiver_settings: Dict[str, Any] = field(default_factory=dict)
    playoff_settings: Dict[str, Any] = field(default_factory=dict)
    trade_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionLog:
    """Log of lineup decisions made by the bot."""
    timestamp: datetime
    week: int
    season: int
    decision_type: str  # "lineup_change", "waiver_pickup", "injury_replacement"
    description: str
    reasoning: str
    confidence: float
    players_involved: List[str] = field(default_factory=list)
    was_executed: bool = False
    outcome: Optional[str] = None  # "success", "failure", "pending"


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    week: int
    season: int
    projected_points: float
    actual_points: float
    accuracy: float  # How close projection was to actual
    decision_quality: float  # 0.0 to 1.0 rating of decision quality
    notes: str = ""
