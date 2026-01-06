#!/usr/bin/env python3
"""
Auto-submit optimal lineup to Yahoo Fantasy
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.yahoo_client import YahooFantasyClient
from src.api.auth_manager import YahooAuthManager
from src.api.external_data import VegasAPI
from src.config.settings import get_config
from src.data.models import Player, Position, Lineup, LineupSlot
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Corrected player to team mapping
PLAYER_TEAMS = {
    'Justin Fields': 'Pittsburgh Steelers',
    'Patrick Mahomes': 'Kansas City Chiefs',
    'Saquon Barkley': 'Philadelphia Eagles',
    'Aaron Jones Sr.': 'Minnesota Vikings',
    'De\'Von Achane': 'Miami Dolphins',
    'Jonathan Taylor': 'Indianapolis Colts',
    'Joe Mixon': 'Houston Texans',
    'Davante Adams': 'New York Jets',
    'CeeDee Lamb': 'Dallas Cowboys',
    'DJ Moore': 'Chicago Bears',
    'Xavier Worthy': 'Kansas City Chiefs',
    'DeVonta Smith': 'Philadelphia Eagles',
    'Jerry Jeudy': 'Denver Broncos',
    'Sam LaPorta': 'Detroit Lions',
    'Tyler Loop': 'Tennessee Titans',
    'Baltimore': 'Baltimore Ravens',
    'Philadelphia': 'Philadelphia Eagles',
}

def auto_submit_optimal_lineup():
    """Auto-submit the optimal lineup to Yahoo Fantasy."""
    try:
        print("🏈 Auto-Submit Optimal Lineup to Yahoo Fantasy")
        print("=" * 50)
        
        # Initialize clients
        config = get_config()
        auth_manager = YahooAuthManager()
        yahoo_client = YahooFantasyClient()
        yahoo_client.authenticate(auth_manager)
        yahoo_client.initialize_league()
        vegas_api = VegasAPI()
        
        print("✅ Systems initialized")
        print()
        
        # Get roster
        print("📋 Getting roster...")
        roster = yahoo_client.get_roster()
        print(f"✅ Found {len(roster)} players")
        print()
        
        # Analyze betting data for all players
        print("🎲 Analyzing betting data for all players...")
        print("=" * 45)
        
        player_analysis = {}
        
        for player in roster:
            player_name = player.name
            team = PLAYER_TEAMS.get(player_name, 'Unknown')
            position = player.position.value if player.position else 'Unknown'
            
            print(f"📊 {player_name} ({position}, {team})")
            
            # Get betting data
            odds_data = vegas_api.get_player_odds(player_name, team)
            
            # Analyze the data
            analysis = analyze_player_betting_data(player_name, team, odds_data, position)
            player_analysis[player_name] = analysis
            
            # Display insights
            display_player_insights(analysis)
            print()
        
        # Generate complete lineup
        print("🎯 GENERATING OPTIMAL LINEUP")
        print("=" * 30)
        
        optimal_lineup = generate_complete_lineup(player_analysis, roster)
        display_complete_lineup(optimal_lineup)
        
        # Convert to Yahoo Lineup object
        print("\n🔄 Converting to Yahoo format...")
        yahoo_lineup = convert_to_yahoo_lineup(optimal_lineup, roster)
        
        # Show what will be submitted
        print("\n📤 LINEUP TO BE SUBMITTED:")
        print("=" * 30)
        display_yahoo_lineup(yahoo_lineup)
        
        # Ask for confirmation
        print("\n⚠️  WARNING: This will submit the lineup to Yahoo Fantasy!")
        print("This action cannot be undone.")
        
        confirm = input("\nDo you want to proceed? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            print("\n🚀 Submitting lineup to Yahoo...")
            success = yahoo_client.submit_lineup(yahoo_lineup)
            
            if success:
                print("✅ Lineup successfully submitted to Yahoo Fantasy!")
                print("🎉 Your optimal lineup is now active!")
            else:
                print("❌ Failed to submit lineup to Yahoo Fantasy")
                print("Please check the logs for more details")
        else:
            print("❌ Lineup submission cancelled")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")

def analyze_player_betting_data(player_name: str, team: str, odds_data: dict, position: str) -> dict:
    """Analyze betting data for a player."""
    analysis = {
        'name': player_name,
        'team': team,
        'position': position,
        'game_total': None,
        'spread': None,
        'td_odds': None,
        'reception_odds': None,
        'rush_odds': None,
        'score': 0,
        'insights': [],
        'flex_eligible': position in ['RB', 'WR', 'TE']
    }
    
    # Game lines
    game_lines = odds_data.get('game_lines')
    if game_lines:
        analysis['game_total'] = game_lines.get('total')
        analysis['spread'] = game_lines.get('spread')
        
        # Score based on game total
        if analysis['game_total']:
            if analysis['game_total'] >= 50:
                analysis['score'] += 3
                analysis['insights'].append("🔥 High-scoring game")
            elif analysis['game_total'] >= 45:
                analysis['score'] += 1
                analysis['insights'].append("📊 Good scoring potential")
            elif analysis['game_total'] <= 40:
                analysis['score'] -= 2
                analysis['insights'].append("❄️  Low-scoring game")
        
        # Score based on spread
        if analysis['spread']:
            home_team = game_lines.get('home_team', '')
            is_home = team == home_team
            
            if is_home and analysis['spread'] > 3:
                analysis['score'] += 2
                analysis['insights'].append("🏠 Home favorite")
            elif not is_home and analysis['spread'] < -3:
                analysis['score'] += 2
                analysis['insights'].append("✈️  Away favorite")
            elif is_home and analysis['spread'] < -3:
                analysis['score'] -= 1
                analysis['insights'].append("🏠 Home underdog")
            elif not is_home and analysis['spread'] > 3:
                analysis['score'] -= 1
                analysis['insights'].append("✈️  Away underdog")
    
    # Player props
    player_odds = odds_data.get('odds', [])
    for prop in player_odds:
        if prop['market'] == 'player_anytime_td' and prop['outcome'] == 'Yes':
            analysis['td_odds'] = prop['price']
            if prop['price'] < 0:  # Favorite
                analysis['score'] += 3
                analysis['insights'].append("🎯 TD favorite")
            elif prop['price'] < 200:  # Contender
                analysis['score'] += 1
                analysis['insights'].append("🎯 TD contender")
            else:  # Long shot
                analysis['insights'].append("🎲 TD long shot")
        
        elif prop['market'] == 'player_receptions':
            analysis['reception_odds'] = prop.get('point')
            if prop.get('point', 0) >= 6:
                analysis['score'] += 2
                analysis['insights'].append("📈 High reception expectation")
            elif prop.get('point', 0) >= 4:
                analysis['score'] += 1
                analysis['insights'].append("📈 Good reception potential")
        
        elif prop['market'] == 'player_rush_yds':
            analysis['rush_odds'] = prop.get('point')
            if prop.get('point', 0) >= 80:
                analysis['score'] += 2
                analysis['insights'].append("🏃 High rush expectation")
            elif prop.get('point', 0) >= 50:
                analysis['score'] += 1
                analysis['insights'].append("🏃 Good rush potential")
    
    return analysis

def display_player_insights(analysis: dict):
    """Display insights for a player."""
    if analysis['insights']:
        for insight in analysis['insights']:
            print(f"   {insight}")
    else:
        print("   ⚠️  No betting data available")
    
    if analysis['score'] != 0:
        print(f"   📊 Betting Score: {analysis['score']:+d}")

def generate_complete_lineup(player_analysis: dict, roster: list) -> dict:
    """Generate complete lineup with all required positions."""
    
    # Group players by position
    positions = {
        'QB': [],
        'RB': [],
        'WR': [],
        'TE': [],
        'K': [],
        'DEF': []
    }
    
    # Populate position groups
    for player_name, analysis in player_analysis.items():
        pos = analysis['position']
        if pos in positions:
            positions[pos].append((player_name, analysis))
    
    # Sort each position by betting score
    for pos in positions:
        positions[pos].sort(key=lambda x: x[1]['score'], reverse=True)
    
    # Create optimal lineup
    lineup = {
        'QB': None,
        'RB1': None,
        'RB2': None,
        'WR1': None,
        'WR2': None,
        'FLEX': None,
        'TE': None,
        'K': None,
        'DEF': None,
        'bench': []
    }
    
    # Fill required positions
    if positions['QB']:
        lineup['QB'] = positions['QB'][0]  # Best QB
    
    if len(positions['RB']) >= 2:
        lineup['RB1'] = positions['RB'][0]  # Best RB
        lineup['RB2'] = positions['RB'][1]  # Second best RB
    elif len(positions['RB']) == 1:
        lineup['RB1'] = positions['RB'][0]
    
    if len(positions['WR']) >= 2:
        lineup['WR1'] = positions['WR'][0]  # Best WR
        lineup['WR2'] = positions['WR'][1]  # Second best WR
    elif len(positions['WR']) == 1:
        lineup['WR1'] = positions['WR'][0]
    
    if positions['TE']:
        lineup['TE'] = positions['TE'][0]  # Best TE
    
    if positions['K']:
        lineup['K'] = positions['K'][0]  # Best K
    
    if positions['DEF']:
        lineup['DEF'] = positions['DEF'][0]  # Best DEF
    
    # Fill FLEX position (best remaining RB/WR/TE)
    flex_candidates = []
    
    # Add remaining RBs
    if len(positions['RB']) > 2:
        for rb in positions['RB'][2:]:
            flex_candidates.append(rb)
    
    # Add remaining WRs
    if len(positions['WR']) > 2:
        for wr in positions['WR'][2:]:
            flex_candidates.append(wr)
    
    # Add remaining TEs
    if len(positions['TE']) > 1:
        for te in positions['TE'][1:]:
            flex_candidates.append(te)
    
    # Sort flex candidates by score
    flex_candidates.sort(key=lambda x: x[1]['score'], reverse=True)
    
    if flex_candidates:
        lineup['FLEX'] = flex_candidates[0]
    
    # Fill bench with remaining players
    all_used = set()
    for position in ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'FLEX', 'TE', 'K', 'DEF']:
        if lineup[position]:
            all_used.add(lineup[position][0])
    
    # Add remaining players to bench
    for player_name, analysis in player_analysis.items():
        if player_name not in all_used:
            lineup['bench'].append((player_name, analysis))
    
    # Sort bench by score
    lineup['bench'].sort(key=lambda x: x[1]['score'], reverse=True)
    
    return lineup

def display_complete_lineup(lineup: dict):
    """Display the complete optimal lineup."""
    
    print("🏆 OPTIMAL STARTING LINEUP:")
    print("-" * 30)
    
    # QB
    if lineup['QB']:
        player_name, analysis = lineup['QB']
        print(f"QB:  {player_name} (Score: {analysis['score']:+d})")
    
    # RBs
    if lineup['RB1']:
        player_name, analysis = lineup['RB1']
        print(f"RB1: {player_name} (Score: {analysis['score']:+d})")
    
    if lineup['RB2']:
        player_name, analysis = lineup['RB2']
        print(f"RB2: {player_name} (Score: {analysis['score']:+d})")
    
    # WRs
    if lineup['WR1']:
        player_name, analysis = lineup['WR1']
        print(f"WR1: {player_name} (Score: {analysis['score']:+d})")
    
    if lineup['WR2']:
        player_name, analysis = lineup['WR2']
        print(f"WR2: {player_name} (Score: {analysis['score']:+d})")
    
    # FLEX
    if lineup['FLEX']:
        player_name, analysis = lineup['FLEX']
        print(f"FLEX: {player_name} ({analysis['position']}) (Score: {analysis['score']:+d})")
    
    # TE
    if lineup['TE']:
        player_name, analysis = lineup['TE']
        print(f"TE:  {player_name} (Score: {analysis['score']:+d})")
    
    # K
    if lineup['K']:
        player_name, analysis = lineup['K']
        print(f"K:   {player_name} (Score: {analysis['score']:+d})")
    
    # DEF
    if lineup['DEF']:
        player_name, analysis = lineup['DEF']
        print(f"DEF: {player_name} (Score: {analysis['score']:+d})")

def convert_to_yahoo_lineup(optimal_lineup: dict, roster: list) -> Lineup:
    """Convert optimal lineup to Yahoo Lineup object."""
    
    # Create a mapping of player names to Player objects
    player_map = {player.name: player for player in roster}
    
    # Create lineup slots
    slots = []
    
    # Define the lineup structure
    lineup_structure = [
        ('QB', 'QB'),
        ('RB1', 'RB'),
        ('RB2', 'RB'),
        ('WR1', 'WR'),
        ('WR2', 'WR'),
        ('FLEX', 'FLEX'),
        ('TE', 'TE'),
        ('K', 'K'),
        ('DEF', 'DEF')
    ]
    
    for slot_name, position in lineup_structure:
        if optimal_lineup[slot_name]:
            player_name, analysis = optimal_lineup[slot_name]
            player = player_map.get(player_name)
            
            if player:
                slot = LineupSlot(
                    position=Position(position),
                    player=player,
                    is_filled=True
                )
                slots.append(slot)
                print(f"  {position}: {player_name}")
    
    # Add bench players
    for player_name, analysis in optimal_lineup['bench']:
        player = player_map.get(player_name)
        if player:
            slot = LineupSlot(
                position=Position('BN'),
                player=player,
                is_filled=True
            )
            slots.append(slot)
            print(f"  Bench: {player_name}")
    
    # Create the Lineup object (assuming week 2)
    config = get_config()
    lineup = Lineup(
        team_id=str(config.team_id),
        week=2,
        season=2024,
        slots=slots
    )
    
    return lineup

def display_yahoo_lineup(lineup: Lineup):
    """Display the Yahoo lineup that will be submitted."""
    
    print("Starting Lineup:")
    for slot in lineup.slots:
        if slot.position.value != 'BN':
            print(f"  {slot.position.value}: {slot.player.name}")
    
    print("\nBench:")
    for slot in lineup.slots:
        if slot.position.value == 'BN':
            print(f"  {slot.player.name}")

if __name__ == "__main__":
    auto_submit_optimal_lineup()
