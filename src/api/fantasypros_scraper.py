"""
FantasyPros web scraper for fantasy football rankings and projections.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from bs4 import BeautifulSoup
import re

from ..data.models import PlayerProjection, InjuryInfo
from ..config.settings import get_config

logger = logging.getLogger(__name__)


class FantasyProsScraper:
    """Web scraper for FantasyPros fantasy football data."""
    
    def __init__(self):
        self.config = get_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache
        self._rate_limit_delay = 2.0  # 2 seconds between requests
        
        # FantasyPros URLs for different positions
        self.ranking_urls = {
            'QB': 'https://www.fantasypros.com/nfl/rankings/qb.php',
            'RB': 'https://www.fantasypros.com/nfl/rankings/rb.php',
            'WR': 'https://www.fantasypros.com/nfl/rankings/wr.php',
            'TE': 'https://www.fantasypros.com/nfl/rankings/te.php',
            'K': 'https://www.fantasypros.com/nfl/rankings/k.php',
            'DST': 'https://www.fantasypros.com/nfl/rankings/dst.php'
        }
    
    def _rate_limit(self):
        """Implement rate limiting to be respectful to FantasyPros."""
        time.sleep(self._rate_limit_delay)
    
    def get_position_rankings(self, position: str, week: int = 1) -> List[Dict[str, Any]]:
        """Get rankings for a specific position and week."""
        cache_key = f"rankings_{position}_{week}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
        
        if position not in self.ranking_urls:
            logger.error(f"Unknown position: {position}")
            return []
        
        try:
            self._rate_limit()
            
            url = self.ranking_urls[position]
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            rankings = self._parse_rankings_page(soup, position)
            
            # Cache the result
            self._cache[cache_key] = (rankings, time.time())
            
            logger.info(f"Successfully scraped {len(rankings)} {position} rankings from FantasyPros")
            return rankings
            
        except requests.RequestException as e:
            logger.error(f"Error scraping FantasyPros {position} rankings: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing FantasyPros {position} rankings: {e}")
            return []
    
    def _parse_rankings_page(self, soup: BeautifulSoup, position: str) -> List[Dict[str, Any]]:
        """Parse the rankings page HTML to extract player data."""
        rankings = []
        
        try:
            # Look for the main rankings table
            # FantasyPros typically uses table-based layouts for rankings
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for table with ranking data
                rows = table.find_all('tr')
                
                for row in rows:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    cells = row.find_all('td')
                    if len(cells) < 3:  # Need at least rank, name, and some data
                        continue
                    
                    player_data = self._extract_player_from_row(cells, position)
                    if player_data:
                        rankings.append(player_data)
            
            # If no table found, try alternative parsing methods
            if not rankings:
                rankings = self._parse_alternative_layout(soup, position)
            
        except Exception as e:
            logger.error(f"Error parsing rankings table: {e}")
        
        return rankings
    
    def _extract_player_from_row(self, cells: List, position: str) -> Optional[Dict[str, Any]]:
        """Extract player information from a table row."""
        try:
            # Common patterns in FantasyPros tables
            # Cell 0: Rank
            # Cell 1: Player name
            # Cell 2+: Various stats/projections
            
            rank_text = cells[0].get_text(strip=True)
            if not rank_text or not rank_text.isdigit():
                return None
            
            rank = int(rank_text)
            
            # Extract player name
            name_cell = cells[1]
            player_name = name_cell.get_text(strip=True)
            
            # Clean up player name (remove team, injury status, etc.)
            player_name = self._clean_player_name(player_name)
            
            if not player_name:
                return None
            
            # Extract injury status
            injury_status = self._extract_injury_status(name_cell)
            
            # Extract team (if available)
            team = self._extract_team(name_cell)
            
            # Extract projections/stats from remaining cells
            projections = self._extract_projections(cells[2:], position)
            
            return {
                'rank': rank,
                'name': player_name,
                'position': position,
                'team': team,
                'injury_status': injury_status,
                'projections': projections
            }
            
        except Exception as e:
            logger.error(f"Error extracting player from row: {e}")
            return None
    
    def _parse_alternative_layout(self, soup: BeautifulSoup, position: str) -> List[Dict[str, Any]]:
        """Parse alternative page layouts if table parsing fails."""
        rankings = []
        
        try:
            # Look for div-based rankings
            ranking_divs = soup.find_all('div', class_=re.compile(r'ranking|player|rank'))
            
            for div in ranking_divs:
                # Look for player information in divs
                player_name = div.find('span', class_=re.compile(r'name|player'))
                if player_name:
                    name = player_name.get_text(strip=True)
                    if name and len(name) > 2:  # Basic validation
                        rankings.append({
                            'rank': len(rankings) + 1,
                            'name': self._clean_player_name(name),
                            'position': position,
                            'team': '',
                            'injury_status': '',
                            'projections': {}
                        })
            
        except Exception as e:
            logger.error(f"Error parsing alternative layout: {e}")
        
        return rankings
    
    def _clean_player_name(self, name: str) -> str:
        """Clean up player name by removing team, injury status, etc."""
        # Remove common suffixes and team abbreviations
        name = re.sub(r'\s+\([^)]+\)', '', name)  # Remove (Team) or (IR)
        name = re.sub(r'\s+[A-Z]{2,3}$', '', name)  # Remove team abbreviations
        name = re.sub(r'\s+[QDOIR]$', '', name)  # Remove injury status
        name = re.sub(r'\s+Sr\.?$', '', name)  # Remove Sr.
        name = re.sub(r'\s+Jr\.?$', '', name)  # Remove Jr.
        
        return name.strip()
    
    def _extract_injury_status(self, name_cell) -> str:
        """Extract injury status from player name cell."""
        try:
            # Look for injury indicators
            injury_indicators = ['Q', 'O', 'IR', 'D', 'P']
            cell_text = name_cell.get_text()
            
            for indicator in injury_indicators:
                if indicator in cell_text:
                    return indicator
            
            return ''
        except:
            return ''
    
    def _extract_team(self, name_cell) -> str:
        """Extract team from player name cell."""
        try:
            # Look for team in parentheses
            team_match = re.search(r'\(([^)]+)\)', name_cell.get_text())
            if team_match:
                return team_match.group(1)
            return ''
        except:
            return ''
    
    def _extract_projections(self, cells: List, position: str) -> Dict[str, Any]:
        """Extract projections from data cells."""
        projections = {}
        
        try:
            # Different positions have different projection types
            if position == 'QB':
                if len(cells) >= 3:
                    projections['passing_yards'] = self._extract_number(cells[0])
                    projections['passing_tds'] = self._extract_number(cells[1])
                    projections['fantasy_points'] = self._extract_number(cells[2])
            elif position in ['RB', 'WR']:
                if len(cells) >= 4:
                    projections['rushing_yards'] = self._extract_number(cells[0])
                    projections['receiving_yards'] = self._extract_number(cells[1])
                    projections['total_tds'] = self._extract_number(cells[2])
                    projections['fantasy_points'] = self._extract_number(cells[3])
            elif position == 'TE':
                if len(cells) >= 3:
                    projections['receiving_yards'] = self._extract_number(cells[0])
                    projections['receiving_tds'] = self._extract_number(cells[1])
                    projections['fantasy_points'] = self._extract_number(cells[2])
            elif position == 'K':
                if len(cells) >= 2:
                    projections['field_goals'] = self._extract_number(cells[0])
                    projections['fantasy_points'] = self._extract_number(cells[1])
            elif position == 'DST':
                if len(cells) >= 3:
                    projections['sacks'] = self._extract_number(cells[0])
                    projections['interceptions'] = self._extract_number(cells[1])
                    projections['fantasy_points'] = self._extract_number(cells[2])
                    
        except Exception as e:
            logger.error(f"Error extracting projections: {e}")
        
        return projections
    
    def _extract_number(self, cell) -> float:
        """Extract numeric value from a cell."""
        try:
            text = cell.get_text(strip=True)
            # Remove common non-numeric characters
            text = re.sub(r'[^\d.-]', '', text)
            if text:
                return float(text)
            return 0.0
        except:
            return 0.0
    
    def get_player_projection(self, player_name: str, position: str, week: int = 1) -> Optional[PlayerProjection]:
        """Get player projection by searching rankings."""
        try:
            rankings = self.get_position_rankings(position, week)
            
            # Search for player in rankings
            for player in rankings:
                if self._names_match(player_name, player['name']):
                    projections = player.get('projections', {})
                    
                    return PlayerProjection(
                        player_name=player_name,
                        week=week,
                        season=2024,
                        projected_points=float(projections.get('fantasy_points', 0)),
                        confidence=0.85,  # FantasyPros consensus rankings are reliable
                        source="FantasyPros",
                        timestamp=datetime.now(),
                        details=projections
                    )
            
            logger.warning(f"Player {player_name} not found in {position} rankings")
            return None
            
        except Exception as e:
            logger.error(f"Error getting FantasyPros projection for {player_name}: {e}")
            return None
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two player names match (allowing for variations)."""
        # Normalize names
        n1 = name1.lower().replace('.', '').replace("'", '').strip()
        n2 = name2.lower().replace('.', '').replace("'", '').strip()
        
        # Exact match
        if n1 == n2:
            return True
        
        # Handle common variations
        if n1.replace(' ', '') == n2.replace(' ', ''):
            return True
        
        # Handle initials vs full names
        if len(n1.split()) == 1 and len(n2.split()) > 1:
            # n1 is single word, n2 is multiple words
            if n1 in n2.split():
                return True
        
        return False
    
    def get_all_rankings(self, week: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Get rankings for all positions."""
        all_rankings = {}
        
        for position in self.ranking_urls.keys():
            logger.info(f"Getting {position} rankings for week {week}")
            rankings = self.get_position_rankings(position, week)
            all_rankings[position] = rankings
        
        return all_rankings

