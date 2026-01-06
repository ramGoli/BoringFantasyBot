#!/usr/bin/env python3
"""
Enhanced lineup optimizer with waiver wire management
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
from datetime import datetime, timezone

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

def waiver_optimizer():
    """Enhanced optimizer with waiver wire management."""
    try:
        print("🏈 Enhanced Lineup Optimizer with Waiver Wire Management")
        print("=" * 60)
        
        # Initialize clients
        config = get_config()
        auth_manager = YahooAuthManager()
        yahoo_client = YahooFantasyClient()
        yahoo_client.authenticate(auth_manager)
        yahoo_client.initialize_league()
        vegas_api = VegasAPI()
        
        print("✅ Systems initialized")
        print()
        
        # Get current roster
        print("📋 Getting current roster...")
        current_roster = yahoo_client.get_roster()
        print(f"✅ Found {len(current_roster)} players on roster")
        print()
        
        # Get available free agents
        print("🔍 Getting available free agents...")
        available_players = []
        
        # Get top free agents by position
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
        for position in positions:
            try:
                free_agents = yahoo_client.get_available_players(position, 10)  # Top 10 per position
                available_players.extend(free_agents)
                print(f"  📊 Found {len(free_agents)} {position} free agents")
            except Exception as e:
                print(f"  ⚠️  Could not get {position} free agents: {e}")
        
        print(f"✅ Found {len(available_players)} total free agents")
        print()
        
        # Determine target week (override or current) and its date range
        env_week = os.environ.get('WEEK_OVERRIDE')
        target_week = int(env_week) if env_week else yahoo_client.league_obj.current_week()
        week_range = yahoo_client.league_obj.week_date_range(target_week)
        # week_range returns tuple of strings like ('2025-10-01', '2025-10-07') or dates; normalize to datetimes
        def to_dt(d):
            if isinstance(d, datetime):
                return d
            return datetime.fromisoformat(str(d)).replace(tzinfo=timezone.utc) if 'T' not in str(d) else datetime.fromisoformat(str(d).replace('Z','+00:00'))
        week_start = to_dt(week_range[0])
        week_end = to_dt(week_range[1])

        # Analyze betting data for all players (roster + free agents)
        print("🎲 Analyzing betting data for all players...")
        print("=" * 50)
        
        all_players = current_roster + available_players
        player_analysis = {}
        
        # Create lookup for all players (for injury checks during analysis)
        all_players_lookup = {player.name: player for player in all_players}
        
        for player in all_players:
            player_name = player.name
            team = PLAYER_TEAMS.get(player_name, 'Unknown')
            position = player.position.value if player.position else 'Unknown'
            
            # Skip if we already analyzed this player
            if player_name in player_analysis:
                continue
            
            print(f"📊 {player_name} ({position}, {team})")
            
            # Get betting data
            odds_data = vegas_api.get_player_odds(player_name, team)
            
            # Analyze the data with week filtering
            analysis = analyze_player_betting_data(player_name, team, odds_data, position, week_start, week_end)
            
            # If no betting data, give a base score based on position (so star players aren't excluded)
            if analysis['score'] == 0 and not analysis.get('has_betting_data', False):
                # Give base scores for players without betting data based on position
                # This ensures star players like CeeDee Lamb aren't excluded
                base_scores = {
                    'QB': 3,  # QBs generally have decent floors
                    'RB': 2,  # RBs have decent floors
                    'WR': 2,  # WRs have decent floors
                    'TE': 1,  # TEs are more volatile
                    'K': 0,   # Kickers are less predictable
                    'DEF': 0  # Defenses are less predictable
                }
                analysis['score'] = base_scores.get(position, 0)
                analysis['insights'].append("⚠️  No betting data - using base score")
            
            # Apply injury penalty to the score
            player = all_players_lookup.get(player_name)
            if player:
                injury_info = getattr(player, 'injury_info', None)
                if injury_info:
                    from src.data.models import InjuryStatus
                    if injury_info.status == InjuryStatus.OUT:
                        analysis['score'] = -100  # Effectively exclude
                        analysis['insights'].append("❌ OUT - excluded")
                    elif injury_info.status == InjuryStatus.IR:
                        analysis['score'] = -100  # Effectively exclude
                        analysis['insights'].append("❌ IR - excluded")
                    elif injury_info.status == InjuryStatus.DOUBTFUL:
                        # Check probability of playing
                        prob = injury_info.probability_of_playing if hasattr(injury_info, 'probability_of_playing') else None
                        if prob is not None and prob < 0.5:
                            analysis['score'] = -100  # Effectively exclude if < 50% chance
                            analysis['insights'].append(f"❌ DOUBTFUL ({prob*100:.0f}% chance) - excluded")
                        else:
                            analysis['score'] -= 5  # Heavy penalty
                            analysis['insights'].append("⚠️  DOUBTFUL - heavy penalty")
                    elif injury_info.status == InjuryStatus.QUESTIONABLE:
                        # Check probability of playing
                        prob = getattr(injury_info, 'probability_of_playing', None)
                        if prob is not None and prob < 0.5:
                            analysis['score'] = -100  # Effectively exclude if < 50% chance
                            analysis['insights'].append(f"❌ QUESTIONABLE ({prob*100:.0f}% chance) - excluded")
                        elif prob is not None and prob < 0.75:
                            analysis['score'] -= 5  # Heavy penalty if 50-75% chance
                            analysis['insights'].append(f"⚠️  QUESTIONABLE ({prob*100:.0f}% chance) - heavy penalty")
                        elif prob is not None and prob >= 0.75:
                            analysis['score'] -= 2  # Moderate penalty if > 75% chance
                            analysis['insights'].append(f"⚠️  QUESTIONABLE ({prob*100:.0f}% chance) - moderate penalty")
                        else:
                            # No probability data - be conservative and apply heavy penalty
                            analysis['score'] -= 4  # Heavy penalty when probability unknown
                            analysis['insights'].append("⚠️  QUESTIONABLE (probability unknown) - heavy penalty")
            
            player_analysis[player_name] = analysis
            
            # Display insights
            display_player_insights(analysis)
            print()
        
        # Find waiver wire opportunities
        print("🎯 WAIVER WIRE OPPORTUNITIES")
        print("=" * 35)
        
        waiver_suggestions = find_waiver_opportunities(current_roster, available_players, player_analysis)
        
        if waiver_suggestions:
            for suggestion in waiver_suggestions:
                print(f"🔄 Consider adding: {suggestion['add_player']}")
                print(f"   📈 Betting Score: {suggestion['add_score']:+d}")
                print(f"   🗑️  Consider dropping: {suggestion['drop_player']}")
                print(f"   📉 Current Score: {suggestion['drop_score']:+d}")
                print(f"   💰 Net Improvement: {suggestion['improvement']:+d} points")
                print()
        else:
            print("✅ No clear waiver wire improvements found")
            print("Your current roster is already optimized!")
        
        # Generate optimal lineup with current roster
        print("🎯 OPTIMAL LINEUP (Current Roster)")
        print("=" * 40)
        
        current_analysis = {name: analysis for name, analysis in player_analysis.items() 
                          if any(p.name == name for p in current_roster)}
        
        optimal_lineup = generate_complete_lineup(current_analysis, current_roster)
        display_complete_lineup(optimal_lineup)
        
        # Ask if user wants to make waiver moves
        if waiver_suggestions:
            print("\n⚠️  WAIVER WIRE ACTIONS AVAILABLE")
            print("=" * 35)
            
            for i, suggestion in enumerate(waiver_suggestions[:3], 1):  # Show top 3
                print(f"{i}. Add {suggestion['add_player']} (Score: {suggestion['add_score']:+d})")
                print(f"   Drop {suggestion['drop_player']} (Score: {suggestion['drop_score']:+d})")
                print(f"   Net: {suggestion['improvement']:+d} points")
                print()
            
            make_waivers = input("Do you want to make waiver wire moves? (yes/no): ").lower().strip()
            
            if make_waivers in ['yes', 'y']:
                print("\n🚀 Making waiver wire moves...")
                # Note: Actual waiver moves would require additional Yahoo API calls
                print("⚠️  Note: Waiver moves require manual implementation")
                print("   This would involve:")
                print("   1. Dropping the suggested player")
                print("   2. Adding the free agent")
                print("   3. Confirming the transaction")
        
        # Ask if user wants to submit current lineup
        print("\n📤 SUBMIT CURRENT LINEUP?")
        print("=" * 30)
        
        submit_lineup = input("Do you want to submit the current optimal lineup? (yes/no): ").lower().strip()
        
        if submit_lineup in ['yes', 'y']:
            print("\n🚀 Submitting lineup...")
            
            # Convert to Yahoo Lineup object
            yahoo_lineup = convert_to_yahoo_lineup(optimal_lineup, current_roster, yahoo_client)
            
            # Submit lineup
            success = yahoo_client.submit_lineup(yahoo_lineup)
            
            if success:
                print("✅ Lineup successfully submitted to Yahoo Fantasy!")
            else:
                print("❌ Failed to submit lineup to Yahoo Fantasy")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")

def find_waiver_opportunities(current_roster, available_players, player_analysis):
    """Find waiver wire opportunities by comparing scores."""
    suggestions = []
    
    # Group players by position
    roster_by_position = {}
    for player in current_roster:
        pos = player.position.value
        if pos not in roster_by_position:
            roster_by_position[pos] = []
        roster_by_position[pos].append(player)
    
    # Find opportunities for each position
    for position, roster_players in roster_by_position.items():
        # Get available players for this position
        available_at_position = [p for p in available_players if p.position.value == position]
        
        if not available_at_position:
            continue
        
        # Sort roster players by score (worst first)
        roster_players.sort(key=lambda p: player_analysis.get(p.name, {}).get('score', 0))
        
        # Sort available players by score (best first)
        available_at_position.sort(key=lambda p: player_analysis.get(p.name, {}).get('score', 0), reverse=True)
        
        # Find improvements
        for available_player in available_at_position[:3]:  # Check top 3 available
            available_score = player_analysis.get(available_player.name, {}).get('score', 0)
            
            for roster_player in roster_players:
                roster_score = player_analysis.get(roster_player.name, {}).get('score', 0)
                
                # If available player is significantly better
                if available_score > roster_score + 5:  # At least 5 point improvement
                    suggestions.append({
                        'add_player': available_player.name,
                        'add_score': available_score,
                        'drop_player': roster_player.name,
                        'drop_score': roster_score,
                        'improvement': available_score - roster_score,
                        'position': position
                    })
                    break  # Only suggest one move per position
    
    # Sort by improvement amount
    suggestions.sort(key=lambda x: x['improvement'], reverse=True)
    
    return suggestions

def analyze_player_betting_data(player_name: str, team: str, odds_data: dict, position: str, week_start: datetime, week_end: datetime) -> dict:
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
    has_data = False
    if game_lines:
        # Date filtering: only score games within the week's window
        commence_raw = game_lines.get('commence_time')
        if commence_raw:
            try:
                commence_dt = datetime.fromisoformat(str(commence_raw).replace('Z','+00:00'))
                if not (week_start <= commence_dt <= week_end):
                    # Outside the requested week; ignore this player's scoring this run
                    analysis['has_betting_data'] = False
                    return analysis
            except Exception:
                pass
        analysis['game_total'] = game_lines.get('total')
        analysis['spread'] = game_lines.get('spread')
        has_data = True
        
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
    if player_odds:
        has_data = True
    
    # Mark if we have any betting data
    analysis['has_betting_data'] = has_data

    # Accumulators for QB-specific evaluation
    qb_best_pass_tds_price = None
    qb_best_pass_yds_line = None
    qb_best_completions_line = None
    qb_best_attempts_line = None
    qb_best_rush_yds_line = None

    # Accumulators for non-QB props (to avoid counting multiple bookmakers)
    best_td_price = None  # Best (most negative) TD price
    best_reception_line = None  # Highest reception line
    best_rush_yds_line = None  # Highest rush yards line

    # First pass: collect best values for each market type
    for prop in player_odds:
        market = prop.get('market')
        outcome = prop.get('outcome')
        price = prop.get('price')
        point = prop.get('point')

        if market == 'player_anytime_td' and outcome == 'Yes':
            # Track best (most negative) TD price
            if price is not None:
                if best_td_price is None or price < best_td_price:
                    best_td_price = price
                    analysis['td_odds'] = price

        elif market == 'player_receptions' and outcome == 'Over':
            # Track highest reception line
            if point is not None:
                if best_reception_line is None or point > best_reception_line:
                    best_reception_line = point
                    analysis['reception_odds'] = point

        elif market == 'player_rush_yds' and outcome == 'Over':
            # Track highest rush yards line
            if point is not None:
                if position != 'QB':
                    if best_rush_yds_line is None or point > best_rush_yds_line:
                        best_rush_yds_line = point
                        analysis['rush_odds'] = point
                else:
                    # Capture for QB rushing evaluation later
                    qb_best_rush_yds_line = max(qb_best_rush_yds_line or 0, point)

        # Record QB-related markets
        if position == 'QB':
            if market == 'player_pass_tds' and outcome == 'Over':
                # Prefer most favorable (most negative) price if multiple books
                if price is not None:
                    qb_best_pass_tds_price = min(qb_best_pass_tds_price, price) if qb_best_pass_tds_price is not None else price
            elif market == 'player_pass_yds' and outcome == 'Over':
                if point is not None:
                    qb_best_pass_yds_line = max(qb_best_pass_yds_line or 0, point)
            elif market == 'player_pass_completions' and outcome == 'Over':
                if point is not None:
                    qb_best_completions_line = max(qb_best_completions_line or 0, point)
            elif market == 'player_pass_attempts' and outcome == 'Over':
                if point is not None:
                    qb_best_attempts_line = max(qb_best_attempts_line or 0, point)

    # Score based on collected best values (non-QB)
    if position != 'QB':
        # TD odds scoring (only once)
        if best_td_price is not None:
            if best_td_price < 0:  # Favorite
                analysis['score'] += 3
                analysis['insights'].append("🎯 TD favorite")
            elif best_td_price < 200:  # Contender
                analysis['score'] += 1
                analysis['insights'].append("🎯 TD contender")
            else:  # Long shot
                analysis['insights'].append("🎲 TD long shot")

        # Reception line scoring (only once)
        if best_reception_line is not None:
            if best_reception_line >= 6:
                analysis['score'] += 2
                analysis['insights'].append("📈 High reception expectation")
            elif best_reception_line >= 4:
                analysis['score'] += 1
                analysis['insights'].append("📈 Good reception potential")

        # Rush yards scoring (only once)
        # Sanity check: WRs rarely have rush yards lines > 30, TEs rarely > 20
        # If the line is too high, it's likely a data error or wrong player match
        if best_rush_yds_line is not None:
            # Filter out unrealistic lines for WRs and TEs
            if position == 'WR' and best_rush_yds_line > 30:
                # Likely a data error or wrong player match - ignore
                pass
            elif position == 'TE' and best_rush_yds_line > 20:
                # Likely a data error or wrong player match - ignore
                pass
            else:
                if best_rush_yds_line >= 80:
                    analysis['score'] += 2
                    analysis['insights'].append("🏃 High rush expectation")
                elif best_rush_yds_line >= 50:
                    analysis['score'] += 1
                    analysis['insights'].append("🏃 Good rush potential")

    # Apply QB scoring weights after collecting best lines
    if position == 'QB':
        # Pass TDs: strong signal for ceiling
        if qb_best_pass_tds_price is not None:
            if qb_best_pass_tds_price < 0:
                analysis['score'] += 3
                analysis['insights'].append("🎯 Pass TDs favored (o1.5)")
            else:
                analysis['score'] += 1
                analysis['insights'].append("📈 Pass TDs viable (o1.5)")

        # Pass yards
        if qb_best_pass_yds_line is not None:
            if qb_best_pass_yds_line >= 275:
                analysis['score'] += 3
                analysis['insights'].append("🚀 High pass yards expectation")
            elif qb_best_pass_yds_line >= 250:
                analysis['score'] += 2
                analysis['insights'].append("📈 Good pass yards expectation")
            elif qb_best_pass_yds_line >= 225:
                analysis['score'] += 1
                analysis['insights'].append("📊 Solid pass yards line")

        # Completions
        if qb_best_completions_line is not None:
            if qb_best_completions_line >= 24.5:
                analysis['score'] += 2
                analysis['insights'].append("📡 High completions expectation")
            elif qb_best_completions_line >= 21.5:
                analysis['score'] += 1
                analysis['insights'].append("📡 Good completions line")

        # Attempts
        if qb_best_attempts_line is not None:
            if qb_best_attempts_line >= 36.5:
                analysis['score'] += 2
                analysis['insights'].append("🎯 High attempts expectation")
            elif qb_best_attempts_line >= 33.5:
                analysis['score'] += 1
                analysis['insights'].append("🎯 Good attempts line")

        # QB rushing
        if qb_best_rush_yds_line is not None:
            if qb_best_rush_yds_line >= 35:
                analysis['score'] += 2
                analysis['insights'].append("🏃 QB rushing upside")
            elif qb_best_rush_yds_line >= 20:
                analysis['score'] += 1
                analysis['insights'].append("🏃 QB rushing potential")
    
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
    
    # Create player lookup for injury/status checks
    player_lookup = {player.name: player for player in roster}
    roster_names = set(player.name for player in roster)
    
    # Also create lookup for all players (roster + available) for injury checks during analysis
    all_players_dict = {p.name: p for p in roster}
    # Note: available_players would need to be passed in, but for now we'll handle it in the main loop
    
    # Group players by position
    positions = {
        'QB': [],
        'RB': [],
        'WR': [],
        'TE': [],
        'K': [],
        'DEF': []
    }
    
    # Populate position groups (filter out injured/out players)
    for player_name, analysis in player_analysis.items():
        pos = analysis['position']
        if pos in positions:
            # Check if player is available (not injured/out)
            player = player_lookup.get(player_name)
            if player:
                # Skip players with negative scores (injured/excluded)
                if analysis.get('score', 0) < 0:
                    print(f"⚠️  Skipping {player_name} - Score too low (likely injured)")
                    continue
                
                # Also check injury status for display
                injury_info = getattr(player, 'injury_info', None)
                if injury_info:
                    from src.data.models import InjuryStatus
                    if injury_info.status == InjuryStatus.QUESTIONABLE:
                        prob = getattr(injury_info, 'probability_of_playing', None)
                        if prob is not None:
                            print(f"⚠️  {player_name} is QUESTIONABLE ({prob*100:.0f}% chance to play)")
                        else:
                            print(f"⚠️  {player_name} is QUESTIONABLE but still available")
                # Don't skip based on is_starting - bench players can be moved to starting lineup
                    
            positions[pos].append((player_name, analysis))
    
    # Sort each position by betting score, with tiebreakers
    for pos in positions:
        # Sort by: score (descending), then has_betting_data (True first), 
        # then is_on_roster (True first - prefer roster players), then name (alphabetical)
        positions[pos].sort(key=lambda x: (
            x[1]['score'], 
            x[1].get('has_betting_data', False),
            x[0] in roster_names,  # Prefer roster players when scores are tied
            x[0]
        ), reverse=True)
    
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

def convert_to_yahoo_lineup(optimal_lineup: dict, roster: list, yahoo_client) -> Lineup:
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
    
    # Create the Lineup object (get current week from Yahoo or override via env)
    config = get_config()
    # Get current week from Yahoo league object, allow env override for what-if runs
    env_week = os.environ.get('WEEK_OVERRIDE')
    current_week = int(env_week) if env_week else yahoo_client.league_obj.current_week()
    lineup = Lineup(
        team_id=str(config.team_id),
        week=current_week,
        season=2024,
        slots=slots
    )
    
    return lineup

if __name__ == "__main__":
    waiver_optimizer()
