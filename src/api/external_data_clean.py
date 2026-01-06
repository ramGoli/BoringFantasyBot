"""
External data integrations for fantasy football.
This is a cleaned-up version that only includes the VegasAPI for betting data.
"""

import time
import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..config.settings import get_config

logger = logging.getLogger(__name__)


class VegasAPI:
    """Vegas betting lines integration using The Odds API."""
    
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.external_apis.odds_api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FantasyFootballBot/1.0 (Odds API Integration)'
        })
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache for odds data
    
    def get_game_lines(self, home_team: str, away_team: str, week: int) -> Dict[str, Optional[float]]:
        """Get betting lines for a game."""
        try:
            if not self.api_key:
                logger.warning("Odds API key not configured")
                return {'spread': None, 'total': None, 'home_team': home_team, 'away_team': away_team}
            
            # Get NFL odds for the current week
            odds_data = self._get_nfl_odds()
            
            # Find the specific game
            for game in odds_data:
                if (self._team_matches(game.get('home_team', ''), home_team) and 
                    self._team_matches(game.get('away_team', ''), away_team)):
                    
                    # Extract spread and total from bookmakers
                    spread, total = self._extract_lines(game.get('bookmakers', []))
                    
                    return {
                        'spread': spread,
                        'total': total,
                        'home_team': home_team,
                        'away_team': away_team,
                        'commence_time': game.get('commence_time')
                    }
            
            logger.debug(f"No odds found for {away_team} @ {home_team}")
            return {'spread': None, 'total': None, 'home_team': home_team, 'away_team': away_team}
            
        except Exception as e:
            logger.error(f"Error getting game lines: {e}")
            return {'spread': None, 'total': None, 'home_team': home_team, 'away_team': away_team}
    
    def get_player_odds(self, player_name: str, team: str) -> Dict[str, Any]:
        """Get player-specific betting odds (props) from The Odds API."""
        try:
            if not self.api_key:
                logger.warning("Odds API key not configured")
                return {}
            
            # Get player props from The Odds API
            props_data = self._get_player_props()
            
            # Find odds for the specific player
            player_odds = []
            for event_data in props_data:
                # Each event_data is a single event with bookmakers
                for bookmaker in event_data.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        if market.get('key') in ['player_pass_tds', 'player_pass_yds', 'player_rush_yds', 
                                                'player_receptions', 'player_anytime_td', 'player_pass_completions', 'player_pass_attempts']:
                            for outcome in market.get('outcomes', []):
                                if self._player_matches(outcome.get('description', ''), player_name):
                                    player_odds.append({
                                        'market': market.get('key'),
                                        'bookmaker': bookmaker.get('title'),
                                        'outcome': outcome.get('name'),
                                        'price': outcome.get('price'),
                                        'point': outcome.get('point'),
                                        'description': outcome.get('description')
                                    })
            
            # Also get game lines for the team
            game_lines = None
            odds_data = self._get_nfl_odds()
            for game in odds_data:
                if (self._team_matches(game.get('home_team', ''), team) or 
                    self._team_matches(game.get('away_team', ''), team)):
                    spread, total = self._extract_lines(game.get('bookmakers', []))
                    game_lines = {
                        'home_team': game.get('home_team'),
                        'away_team': game.get('away_team'),
                        'spread': spread,
                        'total': total,
                        'commence_time': game.get('commence_time')
                    }
                    break
            
            return {
                'player_name': player_name,
                'team': team,
                'game_lines': game_lines,
                'odds': player_odds
            }
            
        except Exception as e:
            logger.error(f"Error getting player odds for {player_name} ({team}): {e}")
            return {'player_name': player_name, 'team': team, 'odds': []}
    
    def _get_nfl_odds(self) -> List[Dict[str, Any]]:
        """Get NFL odds from The Odds API."""
        cache_key = "nfl_odds"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
        
        try:
            url = f"{self.base_url}/sports/americanfootball_nfl/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': 'spreads,totals',
                'oddsFormat': 'american',
                'dateFormat': 'iso'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            odds_data = response.json()
            
            # Cache the result
            self._cache[cache_key] = (odds_data, time.time())
            
            return odds_data
            
        except Exception as e:
            logger.error(f"Error fetching NFL odds: {e}")
            return []
    
    def _get_player_props(self) -> List[Dict[str, Any]]:
        """Get player props from The Odds API using the events endpoint."""
        cache_key = "player_props"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
        
        try:
            # First get the list of events
            events_url = f"{self.base_url}/sports/americanfootball_nfl/events"
            events_params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'dateFormat': 'iso'
            }
            
            events_response = self.session.get(events_url, params=events_params, timeout=15)
            events_response.raise_for_status()
            events_data = events_response.json()
            
            if not events_data:
                logger.warning("No NFL events found")
                return []
            
            # Get player props for each event
            all_props = []
            for event in events_data:  # Check all events to find the right games
                event_id = event.get('id')
                if not event_id:
                    continue
                
                # Check if this is a relevant game (has teams we care about)
                home_team = event.get('home_team', '')
                away_team = event.get('away_team', '')
                
                # Only get props for games that might have our players
                relevant_teams = ['Philadelphia', 'Eagles', 'Kansas City', 'Chiefs', 'Dallas', 'Cowboys', 
                                'Miami', 'Dolphins', 'Minnesota', 'Vikings', 'Detroit', 'Lions',
                                'Chicago', 'Bears', 'Denver', 'Broncos', 'Indianapolis', 'Colts',
                                'Houston', 'Texans', 'Tennessee', 'Titans', 'Baltimore', 'Ravens']
                
                if not any(team in home_team or team in away_team for team in relevant_teams):
                    continue
                
                try:
                    # Get player props for this specific event
                    props_url = f"{self.base_url}/sports/americanfootball_nfl/events/{event_id}/odds"
                    props_params = {
                        'apiKey': self.api_key,
                        'regions': 'us',
                        'markets': 'player_pass_tds,player_pass_yds,player_rush_yds,player_receptions,player_anytime_td,player_pass_completions,player_pass_attempts',
                        'oddsFormat': 'american',
                        'dateFormat': 'iso'
                    }
                    
                    props_response = self.session.get(props_url, params=props_params, timeout=15)
                    props_response.raise_for_status()
                    event_props = props_response.json()
                    
                    if event_props:
                        all_props.append(event_props)
                        
                except Exception as e:
                    logger.debug(f"Error getting props for event {event_id}: {e}")
                    continue
            
            # Cache the result
            self._cache[cache_key] = (all_props, time.time())
            
            return all_props
            
        except Exception as e:
            logger.error(f"Error fetching player props: {e}")
            return []
    
    def _team_matches(self, api_team: str, our_team: str) -> bool:
        """Check if team names match (handle abbreviations and full names)."""
        if not api_team or not our_team:
            return False
        
        # Convert to lowercase for comparison
        api_lower = api_team.lower()
        our_lower = our_team.lower()
        
        # Direct match
        if api_lower == our_lower:
            return True
        
        # Check if our team abbreviation is in the API team name
        if len(our_team) <= 4 and our_lower in api_lower:
            return True
        
        # Check if API team abbreviation is in our team name
        if len(api_team) <= 4 and api_lower in our_lower:
            return True
        
        # Handle common team name variations
        team_variations = {
            'kc': 'kansas city chiefs',
            'gb': 'green bay packers',
            'ne': 'new england patriots',
            'sf': 'san francisco 49ers',
            'la': 'los angeles rams',
            'lv': 'las vegas raiders',
            'nyg': 'new york giants',
            'nyj': 'new york jets',
            'tb': 'tampa bay buccaneers',
            'wsh': 'washington commanders',
            'ari': 'arizona cardinals',
            'atl': 'atlanta falcons',
            'car': 'carolina panthers',
            'cin': 'cincinnati bengals',
            'cle': 'cleveland browns',
            'jax': 'jacksonville jaguars',
            'no': 'new orleans saints',
            'sea': 'seattle seahawks'
        }
        
        # Check variations
        for abbrev, full_name in team_variations.items():
            if our_lower == abbrev and full_name in api_lower:
                return True
        
        return False
    
    def _player_matches(self, api_player: str, our_player: str) -> bool:
        """Check if player names match."""
        if not api_player or not our_player:
            return False
        
        # Convert to lowercase and split names
        api_parts = api_player.lower().split()
        our_parts = our_player.lower().split()
        
        # Remove common suffixes from our player name
        suffixes_to_remove = ['sr.', 'jr.', 'iii', 'ii', 'iv']
        our_parts_clean = [part for part in our_parts if part not in suffixes_to_remove]
        
        # Check if last names match (most reliable)
        if len(api_parts) >= 2 and len(our_parts_clean) >= 2:
            return api_parts[-1] == our_parts_clean[-1]
        
        # Also check if first and last names match (ignoring suffixes)
        if len(api_parts) >= 2 and len(our_parts_clean) >= 2:
            return (api_parts[0] == our_parts_clean[0] and 
                    api_parts[-1] == our_parts_clean[-1])
        
        return False
    
    def _extract_lines(self, bookmakers: List[Dict[str, Any]]) -> tuple[Optional[float], Optional[float]]:
        """Extract spread and total from bookmakers data."""
        spread = None
        total = None
        
        for bookmaker in bookmakers:
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'spreads' and not spread:
                    # Get the home team spread (usually the second outcome)
                    outcomes = market.get('outcomes', [])
                    if len(outcomes) >= 2:
                        spread = outcomes[1].get('point')  # Home team spread
                
                elif market.get('key') == 'totals' and not total:
                    # Get the over/under total
                    outcomes = market.get('outcomes', [])
                    if len(outcomes) >= 1:
                        total = outcomes[0].get('point')
        
        return spread, total
    
    def clear_cache(self):
        """Clear the Vegas API cache."""
        self._cache.clear()





