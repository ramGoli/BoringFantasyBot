"""
Yahoo Fantasy Sports API client for fantasy football.
"""

import time
import logging
import base64
from typing import List, Dict, Optional, Any
import requests
from datetime import datetime, timedelta

from yahoo_fantasy_api import game, league, team

from ..data.models import Player, Team, Lineup, LineupSlot, LeagueSettings, Position, PlayerStats, PlayerProjection, InjuryInfo
from ..config.settings import get_config

logger = logging.getLogger(__name__)


class YahooFantasyClient:
    """Yahoo Fantasy Sports API client."""
    
    def __init__(self):
        self.config = get_config()
        self.auth_manager = None
        self.league_obj = None
        self.team_obj = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache
    
    def authenticate(self, auth_manager):
        """Set the authentication manager."""
        self.auth_manager = auth_manager
    
    def initialize_league(self):
        """Initialize league and team objects."""
        if not self.auth_manager:
            raise Exception("Authentication manager not set")
        
        try:
            access_token = self.auth_manager.get_access_token()
            if not access_token:
                raise Exception("No valid access token available")
            
            class SimpleOAuth:
                def __init__(self, token):
                    self.token = token
                    self.session = requests.Session()
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}',
                        'User-Agent': 'FantasyFootballBot/1.0'
                    })
                
                def get(self, url, params=None):
                    response = self.session.get(url, params=params)
                    response.raise_for_status()
                    return response
            
            oauth_obj = SimpleOAuth(access_token)
            
            # Initialize league and team with proper game keys
            self.league_obj = league.League(oauth_obj, f"nfl.l.{self.config.league_id}")
            self.team_obj = team.Team(oauth_obj, f"nfl.l.{self.config.league_id}.t.{self.config.team_id}")
            
            logger.info(f"Successfully initialized league with key: {self.config.league_id}")
            
        except Exception as e:
            logger.error(f"Error initializing league: {e}")
            raise
    
    def get_roster(self) -> List[Player]:
        """Get current roster from Yahoo."""
        if not self.team_obj:
            raise Exception("Team not initialized")
        
        try:
            roster_data = self.team_obj.roster()
            players = []
            
            for player_data in roster_data:
                try:
                    # Fetch player details to get team information
                    player_id_raw = player_data.get('player_id')
                    player_id = str(player_id_raw) if player_id_raw else ''
                    player_details = None
                    
                    if player_id_raw and self.league_obj:
                        try:
                            # player_details expects an integer, not a string
                            details_list = self.league_obj.player_details(player_id_raw)
                            if details_list and len(details_list) > 0:
                                player_details = details_list[0]
                        except Exception as e:
                            logger.debug(f"Could not fetch player details for {player_id}: {e}")
                    
                    # Parse player data with details
                    player = self._parse_player_data(player_data, player_details)
                    if player:
                        # If no injury info found in player data, try fetching from news
                        if not player.injury_info and player.player_id:
                            injury_info = self._get_injury_from_news(player.player_id, player.name)
                            if injury_info:
                                player.injury_info = injury_info
                        players.append(player)
                except Exception as e:
                    logger.error(f"Error parsing player data: {e}")
                    continue
            
            logger.info(f"Retrieved {len(players)} players from roster")
            return players
            
        except Exception as e:
            logger.error(f"Error getting roster: {e}")
            return []
    
    def get_player_projections(self, week: int) -> List[PlayerProjection]:
        """Get Yahoo's projections for players on your roster."""
        if not self.team_obj:
            raise Exception("Team not initialized")
        
        try:
            # Get roster with projections
            roster_data = self.team_obj.roster()
            projections = []
            
            for player_data in roster_data:
                try:
                    player_name = player_data.get('name', '')
                    position = player_data.get('selected_position', '')
                    
                    if position == 'BN':  # Skip bench players for projections
                        continue
                    
                    # Get player's projected points from Yahoo
                    projected_points = self._get_yahoo_projection(player_data, week)
                    
                    if projected_points is not None:
                        projection = PlayerProjection(
                            player_name=player_name,
                            week=week,
                            season=2024,
                            projected_points=projected_points,
                            confidence=0.8,  # Yahoo projections are reliable
                            source="Yahoo Fantasy",
                            timestamp=datetime.now(),
                            details={
                                'position': position,
                                'yahoo_projection': projected_points
                            }
                        )
                        projections.append(projection)
                        
                except Exception as e:
                    logger.error(f"Error getting projection for {player_name}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(projections)} player projections from Yahoo")
            return projections
            
        except Exception as e:
            logger.error(f"Error getting player projections: {e}")
            return []
    
    def get_available_players(self, position: Optional[str] = None, count: int = 50) -> List[Player]:
        """Get available free agents from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            # Get free agents - yahoo-fantasy-api requires position parameter
            if position:
                players_data = self.league_obj.free_agents(position)
            else:
                # Default to RB if no position specified
                players_data = self.league_obj.free_agents('RB')
            
            players = []
            for player_data in players_data[:count]:
                try:
                    # Fetch player details to get team information
                    player_id_raw = player_data.get('player_id')
                    player_id = str(player_id_raw) if player_id_raw else ''
                    player_details = None
                    
                    if player_id_raw:
                        try:
                            # player_details expects an integer, not a string
                            details_list = self.league_obj.player_details(player_id_raw)
                            if details_list and len(details_list) > 0:
                                player_details = details_list[0]
                        except Exception as e:
                            logger.debug(f"Could not fetch player details for {player_id}: {e}")
                    
                    # Parse player data with details
                    player = self._parse_player_data(player_data, player_details)
                    if player:
                        players.append(player)
                except Exception as e:
                    logger.error(f"Error parsing free agent data: {e}")
                    continue
            
            logger.info(f"Retrieved {len(players)} available players from Yahoo")
            return players
            
        except Exception as e:
            logger.error(f"Error getting available players: {e}")
            return []
    
    def get_player_stats(self, player_id: str, weeks: List[int]) -> List[PlayerStats]:
        """Get player stats for specific weeks from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            stats = []
            for week in weeks:
                try:
                    # Get player stats for specific week
                    player_stats = self.league_obj.player_stats(player_id, week)
                    
                    if player_stats:
                        stats.append(PlayerStats(
                            week=week,
                            season=2024,
                            fantasy_points=float(player_stats.get('fantasy_points', 0))
                        ))
                        
                except Exception as e:
                    logger.error(f"Error getting stats for player {player_id} week {week}: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return []
    
    def get_league_settings(self) -> LeagueSettings:
        """Get league settings and scoring rules from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            settings_data = self.league_obj.settings()
            
            # Parse scoring rules
            scoring_rules = {}
            if 'scoring_settings' in settings_data:
                for rule in settings_data['scoring_settings']:
                    scoring_rules[rule.get('stat', '')] = float(rule.get('points', 0))
            
            return LeagueSettings(
                league_id=self.config.league_id,
                name=settings_data.get('name', 'Unknown League'),
                season=2024,
                roster_positions=settings_data.get('roster_positions', {}),
                scoring_settings=scoring_rules,
                waiver_settings=settings_data.get('waiver_rules', {}),
                playoff_settings={},
                trade_settings=settings_data.get('trade_rules', {})
            )
            
        except Exception as e:
            logger.error(f"Error getting league settings: {e}")
            # Return default settings
            return LeagueSettings(
                league_id=self.config.league_id,
                name='Unknown League',
                season=2024,
                roster_positions={'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'K': 1, 'DEF': 1, 'BN': 7},
                scoring_settings={},
                waiver_settings={},
                playoff_settings={},
                trade_settings={}
            )
    
    def get_weekly_matchup(self, week: int) -> Dict[str, Any]:
        """Get weekly matchup information from Yahoo."""
        if not self.team_obj:
            raise Exception("Team not initialized")
        
        try:
            # Get team's schedule/matchups
            schedule = self.team_obj.schedule()
            
            # Find the specific week
            for game in schedule:
                if game.get('week') == week:
                    return {
                        'week': week,
                        'opponent': game.get('opponent', {}),
                        'game_time': game.get('game_time'),
                        'status': game.get('status'),
                        'my_score': game.get('my_score', 0),
                        'opponent_score': game.get('opponent_score', 0)
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting weekly matchup: {e}")
            return {}
    
    def get_player_news(self, player_id: str) -> List[Dict[str, Any]]:
        """Get player news and injury updates from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            # Get player news
            news_data = self.league_obj.player_news(player_id)
            
            news_items = []
            for item in news_data:
                news_items.append({
                    'title': item.get('title', ''),
                    'content': item.get('content', ''),
                    'date': item.get('date', ''),
                    'source': item.get('source', 'Yahoo'),
                    'url': item.get('url', '')
                })
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error getting player news: {e}")
            return []
    
    def _get_injury_from_news(self, player_id: str, player_name: str) -> Optional[InjuryInfo]:
        """Extract injury information from player news."""
        try:
            from ..data.models import InjuryStatus
            
            news_items = self.get_player_news(player_id)
            if not news_items:
                return None
            
            # Look for injury-related news
            for news in news_items:
                title = news.get('title', '').lower()
                content = news.get('content', '').lower()
                
                # Check for injury keywords
                if any(keyword in title or keyword in content for keyword in 
                       ['injury', 'hurt', 'out', 'doubtful', 'questionable', 'ir', 'injured reserve']):
                    
                    status = None
                    if 'out' in title or 'out' in content:
                        status = InjuryStatus.OUT
                    elif 'doubtful' in title or 'doubtful' in content:
                        status = InjuryStatus.DOUBTFUL
                    elif 'questionable' in title or 'questionable' in content or ' q ' in title:
                        status = InjuryStatus.QUESTIONABLE
                    elif 'ir' in title or 'injured reserve' in title or 'injured reserve' in content:
                        status = InjuryStatus.IR
                    
                    if status:
                        return InjuryInfo(
                            status=status,
                            description=news.get('title', ''),
                            source='Yahoo Fantasy News'
                        )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting injury from news for {player_name}: {e}")
            return None
    
    def _get_yahoo_projection(self, player_data: Dict[str, Any], week: int) -> Optional[float]:
        """Extract Yahoo's projection for a player."""
        try:
            # Look for projection data in player data
            if 'projections' in player_data:
                week_projection = player_data['projections'].get(str(week), {})
                return float(week_projection.get('fantasy_points', 0))
            
            # Alternative: look for weekly stats that might include projections
            if 'weekly_stats' in player_data:
                week_stats = player_data['weekly_stats'].get(str(week), {})
                return float(week_stats.get('projected_points', 0))
            
            # If no projection found, return None
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Yahoo projection: {e}")
            return None
    
    def _parse_player_data(self, player_data: Dict[str, Any], player_details: Optional[Dict[str, Any]] = None) -> Optional[Player]:
        """Parse player data from Yahoo API response."""
        try:
            # Extract basic player information
            player_id = str(player_data.get('player_id', ''))
            name = str(player_data.get('name', ''))
            selected_position = str(player_data.get('selected_position', ''))
            eligible_positions = player_data.get('eligible_positions', [])
            
            # Extract injury information if available
            injury_info = None
            status_text = player_data.get('status', '').lower() if player_data.get('status') else ''
            injury_status_text = player_data.get('injury_status', '').lower() if player_data.get('injury_status') else ''
            
            # Check for injury indicators in status fields
            if status_text or injury_status_text:
                from ..data.models import InjuryStatus
                status = None
                
                if 'out' in status_text or 'out' in injury_status_text:
                    status = InjuryStatus.OUT
                elif 'doubtful' in status_text or 'doubtful' in injury_status_text:
                    status = InjuryStatus.DOUBTFUL
                elif 'questionable' in status_text or 'questionable' in injury_status_text or 'q' in status_text:
                    status = InjuryStatus.QUESTIONABLE
                elif 'ir' in status_text or 'ir' in injury_status_text or 'injured reserve' in status_text:
                    status = InjuryStatus.IR
                
                if status:
                    injury_info = InjuryInfo(
                        status=status,
                        description=player_data.get('injury_note', '') or player_data.get('status', ''),
                        source='Yahoo Fantasy'
                    )
            
            # Extract team information from player_details if available, otherwise from player_data
            team_name = ''
            team_abbr = ''
            team_id = ''
            
            if player_details:
                # Get team info from player_details (more reliable)
                team_name = player_details.get('editorial_team_full_name', '')
                team_abbr = player_details.get('editorial_team_abbr', '')
                # Extract team_id from editorial_team_key (format: "nfl.t.12")
                editorial_team_key = player_details.get('editorial_team_key', '')
                if editorial_team_key:
                    parts = editorial_team_key.split('.')
                    if len(parts) >= 3:
                        team_id = parts[2]
            else:
                # Fallback to player_data fields (usually empty)
                team_name = player_data.get('team_name', '')
                team_abbr = player_data.get('team_abbr', '')
                team_id = player_data.get('team_id', '')
            
            # Create team object
            team = Team(
                team_id=team_id,
                name=team_name,
                abbreviation=team_abbr,
                city='',  # Not available in player_details
                conference='',  # Not available in player_details
                division=''  # Not available in player_details
            )
            
            # Determine actual playing position
            # Priority: Use eligible_positions to find the primary position
            # This is more accurate than selected_position which might be FLEX
            # POSITION CLASSIFICATION HAPPENS HERE (lines 360-386)
            actual_position = 'RB'  # Default fallback
            
            if eligible_positions and len(eligible_positions) > 0:
                # Filter out FLEX positions and get the primary position
                primary_positions = [pos for pos in eligible_positions if pos not in ['W/R', 'W/R/T', 'Q/W/R/T']]
                if primary_positions:
                    # Prefer QB, RB, WR, TE, K, DEF in that order
                    position_priority = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
                    for preferred_pos in position_priority:
                        if preferred_pos in primary_positions:
                            actual_position = preferred_pos
                            break
                    else:
                        actual_position = primary_positions[0]  # Use first if no match
                else:
                    actual_position = eligible_positions[0]  # Fallback to first eligible
            elif selected_position and selected_position != 'BN':
                # Handle Yahoo's position format as fallback
                if selected_position == 'W/R':
                    actual_position = 'WR'  # Default to WR for W/R positions (more common)
                elif selected_position in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
                    actual_position = selected_position
                else:
                    actual_position = 'RB'  # Fallback
            
            # Create player object
            player = Player(
                player_id=player_id,
                name=name,
                position=Position(actual_position),
                team=team,
                nfl_team=team,
                is_on_roster=True,
                is_starting=selected_position != 'BN',
                roster_position=selected_position,
                injury_info=injury_info
            )
            
            # Add eligible positions
            if isinstance(eligible_positions, list):
                for pos in eligible_positions:
                    try:
                        player.eligible_positions.append(Position(pos))
                    except ValueError:
                        pass
            
            return player
            
        except Exception as e:
            logger.error(f"Error parsing player data: {e}")
            return None
    
    def get_league_rankings(self, position: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get league player rankings from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            # Get league leaders/rankings
            if position:
                rankings = self.league_obj.league_leaders(position)
            else:
                rankings = self.league_obj.league_leaders()
            
            return rankings
            
        except Exception as e:
            logger.error(f"Error getting league rankings: {e}")
            return []
    
    def get_waiver_players(self) -> List[Player]:
        """Get players on waivers from Yahoo."""
        if not self.league_obj:
            raise Exception("League not initialized")
        
        try:
            # Get waiver players
            waiver_data = self.league_obj.waiver_players()
            
            players = []
            for player_data in waiver_data:
                try:
                    player = self._parse_player_data(player_data)
                    if player:
                        players.append(player)
                except Exception as e:
                    logger.error(f"Error parsing waiver player data: {e}")
                    continue
            
            return players
            
        except Exception as e:
            logger.error(f"Error getting waiver players: {e}")
            return []
    
    def submit_lineup(self, lineup: Lineup) -> bool:
        """Submit lineup changes to Yahoo using the correct API endpoint."""
        if not self.team_obj:
            raise Exception("Team not initialized")
        
        try:
            logger.info(f"Submitting lineup with {len(lineup.slots)} slots to Yahoo")
            
            # Get the current week and team key
            week = lineup.week
            team_key = f"nfl.l.{self.config.league_id}.t.{self.config.team_id}"
            
            # Build the XML payload for Yahoo's roster endpoint
            xml_payload = self._build_roster_xml(lineup, week)
            logger.info(f"Generated XML payload for week {week}")
            
            # Submit the lineup using Yahoo's roster endpoint
            success = self._submit_roster_to_yahoo(team_key, week, xml_payload)
            
            if success:
                logger.info("✅ Lineup successfully submitted to Yahoo!")
                return True
            else:
                logger.error("❌ Failed to submit lineup to Yahoo")
                return False
            
        except Exception as e:
            logger.error(f"Error submitting lineup: {e}")
            return False
    
    def _build_roster_xml(self, lineup: Lineup, week: int) -> str:
        """Build the XML payload for Yahoo's roster endpoint."""
        try:
            # Start building the XML
            xml_parts = ['<fantasy_content>', '  <roster>']
            xml_parts.append(f'    <coverage_type>week</coverage_type>')
            xml_parts.append(f'    <week>{week}</week>')
            xml_parts.append('    <players>')
            
            # Add each player in the lineup
            for slot in lineup.slots:
                if slot.player and slot.is_filled:
                    # For duplicate positions (RB, WR), we need to ensure unique player assignments
                    yahoo_position = self._map_position_to_yahoo(slot.position.value)
                    logger.info(f"  {slot.position.value}: {slot.player.name} -> {yahoo_position}")
                    
                    # Yahoo uses player_key format: nfl.p.{player_id}
                    player_key = f"nfl.p.{slot.player.player_id}"
                    
                    xml_parts.append('      <player>')
                    xml_parts.append(f'        <player_key>{player_key}</player_key>')
                    xml_parts.append(f'        <position>{yahoo_position}</position>')
                    xml_parts.append('      </player>')
            
            # Add bench players (all players not in starting lineup)
            roster_players = self.get_roster()
            used_player_ids = {slot.player.player_id for slot in lineup.slots if slot.player}
            
            for player in roster_players:
                if player.player_id not in used_player_ids:
                    player_key = f"nfl.p.{player.player_id}"
                    xml_parts.append('      <player>')
                    xml_parts.append(f'        <player_key>{player_key}</player_key>')
                    xml_parts.append('        <position>BN</position>')
                    xml_parts.append('      </player>')
                    logger.info(f"  Bench: {player.name} -> BN ({player_key})")
            
            # Close XML tags
            xml_parts.append('    </players>')
            xml_parts.append('  </roster>')
            xml_parts.append('</fantasy_content>')
            
            xml_content = '\n'.join(xml_parts)
            logger.debug(f"Generated XML:\n{xml_content}")
            
            return xml_content
            
        except Exception as e:
            logger.error(f"Error building roster XML: {e}")
            raise
    
    def _submit_roster_to_yahoo(self, team_key: str, week: int, xml_payload: str) -> bool:
        """Submit the roster XML to Yahoo's API endpoint."""
        try:
            # Get access token from auth manager
            access_token = self.auth_manager.get_access_token()
            if not access_token:
                logger.error("No valid access token available")
                return False
            
            # Build the Yahoo API endpoint URL
            endpoint_url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}"
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/xml',
                'User-Agent': 'FantasyFootballBot/1.0'
            }
            
            logger.info(f"Submitting to Yahoo endpoint: {endpoint_url}")
            
            # Make the PUT request to Yahoo's API
            response = requests.put(
                endpoint_url,
                data=xml_payload,
                headers=headers
            )
            
            # Check response
            if response.status_code == 200:
                logger.info("✅ Yahoo API returned 200 OK")
                logger.debug(f"Response: {response.text}")
                return True
            else:
                logger.error(f"❌ Yahoo API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting roster to Yahoo: {e}")
            return False
    
    def _map_position_to_yahoo(self, position: str) -> str:
        """Map our position names to Yahoo's expected format."""
        position_mapping = {
            'QB': 'QB',
            'RB': 'RB', 
            'WR': 'WR',
            'TE': 'TE',
            'K': 'K',
            'DEF': 'DEF',
            'FLEX': 'W/R'  # Yahoo's flex position - RB/WR only, not TE
        }
        return position_mapping.get(position, position)
    
    def _is_player_eligible_for_position(self, player: Player, position: Position) -> bool:
        """Check if a player is eligible for a specific position."""
        # Direct position match
        if player.position == position:
            return True
        
        # Check eligible positions
        if position in player.eligible_positions:
            return True
        
        # Special handling for FLEX position
        if position.value == 'FLEX':
            return player.position.value in ['RB', 'WR']  # Most leagues only allow RB/WR in FLEX
        
        return False
    
    def _find_valid_position_for_player(self, player: Player) -> Optional[str]:
        """Find a valid position for a player."""
        # Try primary position first
        if player.position.value in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
            return player.position.value
        
        # Try eligible positions
        for pos in player.eligible_positions:
            if pos.value in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
                return pos.value
        
        # Default fallback
        return 'BN'  # Bench if no valid position found
    
    def get_current_lineup(self, week: Optional[int] = None) -> Lineup:
        """Get current lineup for the team."""
        if not self.team_obj:
            raise Exception("Team not initialized")
        
        try:
            # Get current roster
            roster_data = self.team_obj.roster()
            
            # Create lineup from roster
            slots = []
            positions = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'K', 'DEF']
            
            for pos in positions:
                slot = LineupSlot(position=Position(pos))
                slots.append(slot)
            
            # Create lineup
            lineup = Lineup(
                team_id=self.config.team_id,
                week=week or 1,
                season=2024,
                slots=slots
            )
            
            # Fill slots with current roster players
            for player_data in roster_data:
                try:
                    player = self._parse_player_data(player_data)
                    if player and player.is_starting and player.roster_position != 'BN':
                        # Find matching slot
                        for slot in slots:
                            if slot.position.value == player.position.value:
                                slot.player = player
                                slot.is_filled = True
                                break
                except Exception as e:
                    logger.error(f"Error parsing player for lineup: {e}")
                    continue
            
            return lineup
            
        except Exception as e:
            logger.error(f"Error getting current lineup: {e}")
            # Return empty lineup as fallback
            return Lineup(
                team_id=self.config.team_id,
                week=week or 1,
                season=2024,
                slots=[]
            )
