"""
Rotowire API integration for fantasy football projections and data.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

from ..data.models import PlayerProjection, InjuryInfo, WeatherInfo
from ..config.settings import get_config

logger = logging.getLogger(__name__)


class RotowireAPI:
    """Rotowire API client for fantasy football data."""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = "https://api.rotowire.com/v1"
        self.api_key = self.config.external_apis.rotowire_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'FantasyFootballBot/1.0'
        })
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache
    
    def get_player_projection(self, player_name: str, week: int, season: int = 2024) -> Optional[PlayerProjection]:
        """Get player projection for a specific week."""
        cache_key = f"projection_{player_name}_{week}_{season}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
        
        try:
            # Search for player
            search_url = f"{self.base_url}/players/search"
            search_params = {
                'q': player_name,
                'sport': 'nfl'
            }
            
            response = self.session.get(search_url, params=search_params)
            response.raise_for_status()
            
            players = response.json()
            if not players:
                logger.warning(f"No player found for: {player_name}")
                return None
            
            # Get first matching player
            player_id = players[0]['id']
            
            # Get projections
            projection_url = f"{self.base_url}/projections"
            projection_params = {
                'player_id': player_id,
                'week': week,
                'season': season,
                'sport': 'nfl'
            }
            
            response = self.session.get(projection_url, params=projection_params)
            response.raise_for_status()
            
            projection_data = response.json()
            
            if not projection_data:
                logger.warning(f"No projection found for {player_name} week {week}")
                return None
            
            # Parse projection data
            projection = PlayerProjection(
                player_name=player_name,
                week=week,
                season=season,
                projected_points=float(projection_data.get('fantasy_points', 0)),
                confidence=0.8,  # Rotowire projections are generally reliable
                source="Rotowire",
                timestamp=datetime.now(),
                details={
                    'passing_yards': projection_data.get('passing_yards', 0),
                    'passing_tds': projection_data.get('passing_tds', 0),
                    'rushing_yards': projection_data.get('rushing_yards', 0),
                    'rushing_tds': projection_data.get('rushing_tds', 0),
                    'receiving_yards': projection_data.get('receiving_yards', 0),
                    'receiving_tds': projection_data.get('receiving_tds', 0),
                    'receptions': projection_data.get('receptions', 0),
                    'interceptions': projection_data.get('interceptions', 0),
                    'fumbles': projection_data.get('fumbles', 0)
                }
            )
            
            # Cache the result
            self._cache[cache_key] = (projection, time.time())
            
            return projection
            
        except requests.RequestException as e:
            logger.error(f"Error getting Rotowire projection for {player_name}: {e}")
            return None
    
    def get_injury_info(self, player_name: str) -> Optional[InjuryInfo]:
        """Get injury information for a player."""
        try:
            # Search for player
            search_url = f"{self.base_url}/players/search"
            search_params = {
                'q': player_name,
                'sport': 'nfl'
            }
            
            response = self.session.get(search_url, params=search_params)
            response.raise_for_status()
            
            players = response.json()
            if not players:
                return None
            
            player_id = players[0]['id']
            
            # Get injury news
            news_url = f"{self.base_url}/news"
            news_params = {
                'player_id': player_id,
                'sport': 'nfl',
                'limit': 5
            }
            
            response = self.session.get(news_url, params=news_params)
            response.raise_for_status()
            
            news_data = response.json()
            
            if not news_data:
                return None
            
            # Find injury-related news
            injury_news = None
            for news in news_data:
                if any(keyword in news.get('title', '').lower() for keyword in ['injury', 'hurt', 'questionable', 'doubtful', 'out']):
                    injury_news = news
                    break
            
            if not injury_news:
                return None
            
            return InjuryInfo(
                player_name=player_name,
                status=injury_news.get('status', 'Unknown'),
                description=injury_news.get('title', ''),
                severity=self._parse_injury_severity(injury_news.get('title', '')),
                last_updated=datetime.fromisoformat(injury_news.get('date', datetime.now().isoformat())),
                source="Rotowire"
            )
            
        except requests.RequestException as e:
            logger.error(f"Error getting Rotowire injury info for {player_name}: {e}")
            return None
    
    def get_weather_info(self, team_abbr: str, game_date: datetime) -> Optional[WeatherInfo]:
        """Get weather information for a team's game."""
        try:
            # Get team schedule
            schedule_url = f"{self.base_url}/schedules"
            schedule_params = {
                'team': team_abbr,
                'sport': 'nfl',
                'date': game_date.strftime('%Y-%m-%d')
            }
            
            response = self.session.get(schedule_url, params=schedule_params)
            response.raise_for_status()
            
            schedule_data = response.json()
            if not schedule_data:
                return None
            
            game = schedule_data[0]
            venue = game.get('venue', {})
            
            # Get weather for venue location
            weather_url = f"{self.base_url}/weather"
            weather_params = {
                'lat': venue.get('latitude'),
                'lon': venue.get('longitude'),
                'date': game_date.strftime('%Y-%m-%d')
            }
            
            response = self.session.get(weather_url, params=weather_params)
            response.raise_for_status()
            
            weather_data = response.json()
            
            return WeatherInfo(
                temperature=weather_data.get('temperature', 0),
                humidity=weather_data.get('humidity', 0),
                wind_speed=weather_data.get('wind_speed', 0),
                wind_direction=weather_data.get('wind_direction', 0),
                precipitation_chance=weather_data.get('precipitation_chance', 0),
                conditions=weather_data.get('conditions', 'Unknown'),
                source="Rotowire"
            )
            
        except requests.RequestException as e:
            logger.error(f"Error getting Rotowire weather info for {team_abbr}: {e}")
            return None
    
    def _parse_injury_severity(self, title: str) -> str:
        """Parse injury severity from news title."""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['out', 'ir', 'season']):
            return 'high'
        elif any(word in title_lower for word in ['doubtful', 'questionable']):
            return 'medium'
        elif any(word in title_lower for word in ['probable', 'limited']):
            return 'low'
        else:
            return 'unknown'
    
    def get_team_rankings(self, position: str, week: int) -> List[Dict[str, Any]]:
        """Get team rankings for a position and week."""
        try:
            rankings_url = f"{self.base_url}/rankings"
            rankings_params = {
                'position': position,
                'week': week,
                'sport': 'nfl',
                'limit': 50
            }
            
            response = self.session.get(rankings_url, params=rankings_params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error getting Rotowire rankings for {position}: {e}")
            return []

