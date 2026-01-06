"""
Main application entry point for the Fantasy Football Auto-Lineup Bot.
Orchestrates the entire bot workflow including authentication, data gathering,
analysis, and lineup optimization.
"""

import logging
import logging.handlers
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional, List
import sys
import argparse

from .config.settings import get_config
from .api.yahoo_client import YahooFantasyClient
from .api.external_data import VegasAPI
from .analysis.player_evaluator import PlayerEvaluator
from .analysis.lineup_optimizer import LineupOptimizer
from .data.storage import storage
from .data.models import DecisionLog, PerformanceMetrics, RiskLevel, Lineup, LineupSlot, Position, InjuryInfo, InjuryStatus, Player, MatchupInfo, Team


class FantasyFootballBot:
    """Main bot class that orchestrates all fantasy football operations."""
    
    def __init__(self):
        self.config = get_config()
        self.setup_logging()
        
        # Initialize components
        self.yahoo_client = YahooFantasyClient()
        self.evaluator = PlayerEvaluator()
        self.optimizer = LineupOptimizer()
        self.vegas_api = VegasAPI()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Fantasy Football Bot initialized")
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.logging
        
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_config.level))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_config.file,
            maxBytes=log_config.max_size_mb * 1024 * 1024,
            backupCount=log_config.backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def run_weekly_optimization(self, week: Optional[int] = None) -> bool:
        """Run the complete weekly lineup optimization process."""
        try:
            self.logger.info("Starting weekly lineup optimization")
            
            # Initialize Yahoo client with authentication
            if not hasattr(self, 'auth_manager') or not self.auth_manager:
                from .api.auth_manager import YahooAuthManager
                self.auth_manager = YahooAuthManager()
                self.yahoo_client.authenticate(self.auth_manager)
                self.yahoo_client.initialize_league()
            
            # Get current week if not specified
            if week is None:
                week = self._get_current_week()
            
            # Step 1: Get current roster and Yahoo projections
            self.logger.info("Fetching current roster and Yahoo projections")
            current_roster = self.yahoo_client.get_roster()
            yahoo_projections = self.yahoo_client.get_player_projections(week)
            
            # Create a simple lineup from current roster
            current_lineup = self._create_lineup_from_roster(current_roster, week)
            
            if not current_roster:
                self.logger.error("Failed to get current roster")
                return False
            
            # Step 2: Get available free agents first
            self.logger.info("Fetching available free agents from Yahoo")
            available_players = self.yahoo_client.get_available_players('RB', 20)  # Get 20 RBs for testing
            
            # Step 3: Enrich player data with weather, injuries, and matchups
            self.logger.info("Enriching player data with weather, injuries, and matchups")
            self._enrich_player_data(current_roster, week)
            self._enrich_player_data(available_players, week)
            
            # Step 4: Log player scores for debugging
            self.logger.info("Evaluating all players...")
            all_players = current_roster + available_players
            for player in all_players:
                if player.position.value in ['RB', 'WR', 'QB', 'TE']:
                    score = self.evaluator.evaluate_player(player, week)
                    self.logger.info(
                        f"  {player.name} ({player.position.value}): "
                        f"Total={score.total_score:.2f}, "
                        f"Base={score.base_projection:.2f}, "
                        f"Matchup={score.matchup_adjustment:.2f}, "
                        f"Injury={score.injury_adjustment:.2f}, "
                        f"Reasoning={score.reasoning[:100]}"
                    )
            
            # Step 5: Optimize lineup
            self.logger.info("Optimizing lineup")
            optimization_result = self.optimizer.optimize_lineup(
                current_lineup, current_roster + available_players, week
            )

            # Log concise lineup summary
            self._log_lineup_summary(optimization_result.optimized_lineup)
            
            # Step 6: Log the decision
            self._log_optimization_decision(optimization_result, week)
            
            # Step 7: Submit lineup if auto-submit is enabled
            if self.config.auto_submit and optimization_result.changes_made:
                self.logger.info("Auto-submitting optimized lineup")
                success = self.yahoo_client.submit_lineup(optimization_result.optimized_lineup)
                
                if success:
                    self.logger.info("Successfully submitted optimized lineup")
                    self._update_decision_outcome(optimization_result, "success")
                else:
                    self.logger.error("Failed to submit optimized lineup")
                    self._update_decision_outcome(optimization_result, "failure")
            else:
                self.logger.info("Auto-submit disabled or no changes needed")
                self._update_decision_outcome(optimization_result, "pending")
            
            # Step 8: Save lineup to history
            storage.save_lineup_history(
                optimization_result.optimized_lineup,
                optimization_result.total_projected_points,
                optimization_result.risk_level.value
            )
            
            # Step 9: Suggest waiver pickups
            if self.config.waiver_wire_management:
                self._suggest_waiver_pickups(current_roster, available_players, week)
            
            self.logger.info("Weekly optimization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in weekly optimization: {e}")
            return False
    
    def handle_injury_updates(self) -> bool:
        """Handle injury updates and make necessary roster changes."""
        try:
            self.logger.info("Checking for injury updates")
            
            current_week = self._get_current_week()
            current_roster = self.yahoo_client.get_roster(current_week)
            
            if not current_roster:
                return False
            
            # Check for injured players
            injured_players = []
            for player in current_roster:
                if player.injury_info and player.injury_info.status.value in ['out', 'doubtful']:
                    injured_players.append(player)
            
            if not injured_players:
                self.logger.info("No injured players found")
                return True
            
            # Find replacement players
            available_players = self.yahoo_client.get_available_players(count=50)
            
            for injured_player in injured_players:
                replacement = self._find_replacement_player(injured_player, available_players, current_week)
                
                if replacement:
                    self.logger.info(f"Found replacement for {injured_player.name}: {replacement.name}")
                    
                    # Log the decision
                    decision = DecisionLog(
                        timestamp=datetime.now(),
                        week=current_week,
                        season=2024,
                        decision_type="injury_replacement",
                        description=f"Replacing injured {injured_player.name} with {replacement.name}",
                        players_involved=[injured_player.name, replacement.name],
                        reasoning=f"{injured_player.name} is {injured_player.injury_info.status.value}",
                        confidence=0.8,
                        was_executed=False
                    )
                    storage.save_decision(decision)
                    
                    # Make the change if auto-submit is enabled
                    if self.config.auto_submit:
                        # Drop injured player and add replacement
                        if (self.yahoo_client.drop_player(injured_player.player_id) and
                            self.yahoo_client.add_player(replacement.player_id)):
                            self.logger.info(f"Successfully replaced {injured_player.name} with {replacement.name}")
                            self._update_decision_outcome(decision, "success")
                        else:
                            self.logger.error(f"Failed to replace {injured_player.name}")
                            self._update_decision_outcome(decision, "failure")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling injury updates: {e}")
            return False
    
    def run_daily_maintenance(self) -> bool:
        """Run daily maintenance tasks."""
        try:
            self.logger.info("Running daily maintenance")
            
            # Clear expired cache
            cleared_count = storage.clear_expired_cache()
            self.logger.info(f"Cleared {cleared_count} expired cache entries")
            
            # Clear external data cache
            # external_data_manager.clear_cache()  # Not used in betting-based optimization
            
            # Backup database
            backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            storage.backup_database(backup_path)
            
            self.logger.info("Daily maintenance completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in daily maintenance: {e}")
            return False
    
    def _enrich_player_data(self, players: List, week: int):
        """Enrich player data with weather, injuries, and matchups."""
        for player in players:
            # Get player stats from Yahoo for recent weeks (to calculate averages)
            try:
                if player.player_id:
                    # Get stats from previous 4 weeks to calculate recent averages
                    # Only get stats for weeks that have already completed (week - 1, week - 2, etc.)
                    recent_weeks = [max(1, week - i) for i in range(1, 5)]  # weeks 14, 13, 12, 11
                    stats = self.yahoo_client.get_player_stats(player.player_id, recent_weeks)
                    if stats:
                        # Initialize stats list if needed
                        if not player.stats:
                            player.stats = []
                        # Add stats (avoid duplicates)
                        existing_weeks = {s.week for s in player.stats}
                        for stat in stats:
                            if stat.week not in existing_weeks:
                                player.stats.append(stat)
            except Exception as e:
                self.logger.debug(f"Error getting stats for {player.name}: {e}")
            
            # Get player news and injury updates from Yahoo (separate try/except)
            try:
                if player.player_id:
                    news = self.yahoo_client.get_player_news(player.player_id)
                    if news:
                        # Look for injury-related news
                        injury_news = [item for item in news if any(
                            keyword in item['title'].lower() 
                            for keyword in ['injury', 'hurt', 'questionable', 'doubtful', 'out', 'ir']
                        )]
                        
                        if injury_news:
                            # Parse injury status from news
                            status_text = injury_news[0].get('title', '').lower()
                            if 'out' in status_text:
                                status = InjuryStatus.OUT
                            elif 'doubtful' in status_text:
                                status = InjuryStatus.DOUBTFUL
                            elif 'questionable' in status_text:
                                status = InjuryStatus.QUESTIONABLE
                            elif 'ir' in status_text or 'injured reserve' in status_text:
                                status = InjuryStatus.IR
                            else:
                                status = InjuryStatus.QUESTIONABLE
                            
                            player.injury_info = InjuryInfo(
                                player_name=player.name,
                                status=status,
                                description=injury_news[0].get('content', ''),
                                probability_of_playing=0.5 if status == InjuryStatus.QUESTIONABLE else 0.0,
                                last_updated=datetime.now(),
                                source='Yahoo Fantasy'
                            )
            except Exception as e:
                self.logger.debug(f"Error getting news for {player.name}: {e}")
            
            # Get Vegas betting data for player (separate try/except - this is important!)
            try:
                if player.nfl_team:
                    # Try name first, then abbreviation, then city
                    team_name = player.nfl_team.name or player.nfl_team.abbreviation or player.nfl_team.city
                    if team_name:
                        self.logger.info(f"Fetching Vegas odds for {player.name} (team: {team_name})")
                        self.logger.info(f"Fetching Vegas odds for {player.name} ({team_name})")
                        odds_data = self.vegas_api.get_player_odds(player.name, team_name)
                        self.logger.info(f"Vegas API returned data for {player.name}: {bool(odds_data.get('game_lines'))} game lines, {len(odds_data.get('odds', []))} props")
                        
                        # Extract game lines and create/update matchup info
                        game_lines = odds_data.get('game_lines')
                        if game_lines:
                            # Determine if player's team is home or away
                            is_home = game_lines.get('home_team', '').lower() == team_name.lower()
                            
                            # Get opponent team name
                            opponent_name = game_lines.get('away_team', '') if is_home else game_lines.get('home_team', '')
                            
                            # Create a basic opponent Team object (we don't have full details)
                            opponent_team = Team(
                                team_id='',
                                name=opponent_name,
                                abbreviation='',
                                city='',
                                conference='',
                                division=''
                            )
                            
                            # Create or update matchup info with Vegas data
                            if player.matchup:
                                # Update existing matchup
                                player.matchup.spread = game_lines.get('spread')
                                player.matchup.game_total = game_lines.get('total')
                                player.matchup.is_home = is_home
                                player.matchup.opponent_team = opponent_team
                            else:
                                # Create new matchup
                                player.matchup = MatchupInfo(
                                    opponent_team=opponent_team,
                                    opponent_defense_ranking=None,  # Would need separate API call
                                    game_total=game_lines.get('total'),
                                    spread=game_lines.get('spread'),
                                    weather=None,
                                    game_time=None,
                                    is_home=is_home
                                )
                            
                            self.logger.info(f"Updated matchup for {player.name}: spread={game_lines.get('spread')}, total={game_lines.get('total')}")
                        
                        # Store player odds data for potential future use
                        # (could be used to adjust projections based on TD odds, reception props, etc.)
                        player_odds = odds_data.get('odds', [])
                        if player_odds:
                            self.logger.info(f"Found {len(player_odds)} betting props for {player.name}")
                    else:
                        self.logger.debug(f"Player {player.name} has no team name, skipping Vegas API")
                else:
                    self.logger.debug(f"Player {player.name} has no nfl_team data, skipping Vegas API")
            except Exception as e:
                self.logger.warning(f"Error fetching Vegas odds for {player.name}: {e}", exc_info=True)
    
    def _find_replacement_player(self, injured_player, available_players: List, week: int):
        """Find a suitable replacement for an injured player."""
        # Get players of the same position
        same_position_players = [
            p for p in available_players 
            if p.position == injured_player.position
        ]
        
        if not same_position_players:
            return None
        
        # Evaluate and rank replacement options
        scores = []
        for player in same_position_players:
            score = self.evaluator.evaluate_player(player, week)
            scores.append((score, player))
        
        # Sort by score and return the best option
        scores.sort(key=lambda x: x[0].total_score, reverse=True)
        return scores[0][1] if scores else None
    
    def _log_optimization_decision(self, result, week: int):
        """Log the optimization decision."""
        decision = DecisionLog(
            timestamp=datetime.now(),
            week=week,
            season=2024,
            decision_type="lineup_optimization",
            description=f"Optimized lineup with {len(result.changes_made)} changes",
            players_involved=[change['new_player'] for change in result.changes_made],
            reasoning=result.reasoning,
            confidence=result.confidence,
            was_executed=False
        )
        storage.save_decision(decision)
    
    def _update_decision_outcome(self, result, outcome: str):
        """Update the outcome of a decision."""
        # This would update the most recent decision in the database
        # Implementation depends on how you want to track decision outcomes
        pass
    
    def _suggest_waiver_pickups(self, current_roster: List, available_players: List, week: int):
        """Suggest waiver wire pickups."""
        suggestions = self.optimizer.suggest_waiver_pickups(
            current_roster, available_players, week
        )
        
        if suggestions:
            self.logger.info("Waiver pickup suggestions:")
            for suggestion in suggestions:
                self.logger.info(
                    f"Consider adding {suggestion['player'].name} "
                    f"(+{suggestion['improvement']:.1f} points) "
                    f"instead of {suggestion['drop_candidate'].name}"
                )

    def _log_lineup_summary(self, lineup: Lineup):
        """Log a concise lineup summary (QB/RB/RB/WR/WR/TE/FLEX/K/DEF)."""
        try:
            order = ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'K', 'DEF']
            slots_by_pos = {}
            for slot in lineup.slots:
                slots_by_pos.setdefault(slot.position.value, []).append(slot)
            summary_rows = []
            used_indices = {'RB': 0, 'WR': 0}
            for pos in order:
                if pos in ['RB', 'WR']:
                    idx = used_indices[pos]
                    slot_list = slots_by_pos.get(pos, [])
                    player_name = slot_list[idx].player.name if idx < len(slot_list) and slot_list[idx].player else '—'
                    used_indices[pos] = idx + 1
                else:
                    slot_list = slots_by_pos.get(pos, [])
                    player_name = slot_list[0].player.name if slot_list and slot_list[0].player else '—'
                summary_rows.append(f"{pos}: {player_name}")
            self.logger.info("Optimized lineup summary:")
            for row in summary_rows:
                self.logger.info(f"  {row}")
        except Exception as e:
            self.logger.warning(f"Failed to log lineup summary: {e}")
    
    def _create_lineup_from_roster(self, roster: List[Player], week: int) -> Lineup:
        """Create a basic lineup from the current roster."""
        try:
            # Create lineup slots based on standard fantasy football positions
            slots = []
            
            # Standard positions
            positions = ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'K', 'DEF']
            
            for pos in positions:
                slot = LineupSlot(position=Position(pos))
                slots.append(slot)
            
            # Create lineup
            lineup = Lineup(
                team_id=self.config.team_id,
                week=week,
                season=2024,
                slots=slots
            )
            
            # Fill slots with current roster players (avoiding duplicates)
            used_player_ids = set()
            
            # First, fill QB, TE, K, DEF positions (unique positions)
            unique_positions = ['QB', 'TE', 'K', 'DEF']
            for pos in unique_positions:
                for player in roster:
                    if (player.is_starting and 
                        player.roster_position != 'BN' and 
                        player.position.value == pos and
                        player.player_id not in used_player_ids):
                        # Find matching slot
                        for slot in slots:
                            if slot.position.value == pos:
                                slot.player = player
                                slot.is_filled = True
                                used_player_ids.add(player.player_id)
                                break
                        break
            
            # Then fill RB positions (can have multiple)
            rb_count = 0
            for player in roster:
                if (player.is_starting and 
                    player.roster_position != 'BN' and 
                    player.position.value == 'RB' and
                    player.player_id not in used_player_ids and
                    rb_count < 2):
                    # Find empty RB slot
                    for slot in slots:
                        if slot.position.value == 'RB' and not slot.is_filled:
                            slot.player = player
                            slot.is_filled = True
                            used_player_ids.add(player.player_id)
                            rb_count += 1
                            break
            
            # Then fill WR positions (can have multiple)
            wr_count = 0
            for player in roster:
                if (player.is_starting and 
                    player.roster_position != 'BN' and 
                    player.position.value == 'WR' and
                    player.player_id not in used_player_ids and
                    wr_count < 2):
                    # Find empty WR slot
                    for slot in slots:
                        if slot.position.value == 'WR' and not slot.is_filled:
                            slot.player = player
                            slot.is_filled = True
                            used_player_ids.add(player.player_id)
                            wr_count += 1
                            break
            
            # Finally fill FLEX position with best remaining RB or WR
            for player in roster:
                if (player.is_starting and 
                    player.roster_position != 'BN' and
                    player.player_id not in used_player_ids and
                    player.position.value in ['RB', 'WR']):
                    # Find FLEX slot
                    for slot in slots:
                        if slot.position.value == 'FLEX' and not slot.is_filled:
                            slot.player = player
                            slot.is_filled = True
                            used_player_ids.add(player.player_id)
                            break
                    break
            
            return lineup
            
        except Exception as e:
            self.logger.error(f"Error creating lineup from roster: {e}")
            # Return empty lineup as fallback
            return Lineup(
                team_id=self.config.team_id,
                week=week,
                season=2024,
                slots=[]
            )
    
    def _get_current_week(self) -> int:
        """Get the current NFL week."""
        # This is a simplified implementation
        # In production, you'd want to get this from the league settings
        return 1
    
    def run_scheduled_tasks(self):
        """Run the scheduled tasks."""
        # Schedule daily optimization
        schedule.every().day.at(self.config.run_daily_at).do(self.run_weekly_optimization)
        
        # Schedule injury checks
        if self.config.check_injuries_hourly:
            schedule.every().hour.do(self.handle_injury_updates)
        
        # Schedule daily maintenance
        schedule.every().day.at("02:00").do(self.run_daily_maintenance)
        
        self.logger.info("Scheduled tasks configured")
        
        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_once(self, week: Optional[int] = None):
        """Run the bot once for immediate execution."""
        return self.run_weekly_optimization(week)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fantasy Football Auto-Lineup Bot")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--week", type=int, help="Specific week to optimize")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled tasks")
    
    args = parser.parse_args()
    
    # Initialize bot
    bot = FantasyFootballBot()
    
    try:
        if args.once:
            # Run once
            success = bot.run_once(args.week)
            sys.exit(0 if success else 1)
        elif args.schedule:
            # Run scheduled tasks
            bot.run_scheduled_tasks()
        else:
            # Default: run once
            success = bot.run_once(args.week)
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
