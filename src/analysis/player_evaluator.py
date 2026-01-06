"""
Player evaluation system for the Fantasy Football Auto-Lineup Bot.
Evaluates players based on projections, matchups, injuries, and other factors.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..data.models import Player, PlayerProjection, InjuryInfo, WeatherInfo, MatchupInfo, Position, InjuryStatus
from ..config.settings import get_config


logger = logging.getLogger(__name__)


@dataclass
class PlayerScore:
    """Player evaluation score with breakdown."""
    player: Player
    total_score: float
    base_projection: float
    matchup_adjustment: float
    injury_adjustment: float
    weather_adjustment: float
    trend_adjustment: float
    confidence: float
    reasoning: str


class PlayerEvaluator:
    """Evaluates players for fantasy football lineup decisions."""
    
    def __init__(self):
        self.config = get_config()
        self.position_weights = self._get_position_weights()
    
    def evaluate_player(self, player: Player, week: int, opponent: Optional[str] = None) -> PlayerScore:
        """Evaluate a player for the given week."""
        try:
            # Base projection
            base_projection = self._get_base_projection(player, week)
            
            # Extract opponent from matchup if not provided
            if not opponent and player.matchup and player.matchup.opponent_team:
                opponent = player.matchup.opponent_team.name
            
            # Matchup adjustment
            matchup_adjustment = self._evaluate_matchup(player, opponent)
            
            # Injury adjustment
            injury_adjustment = self._evaluate_injury_risk(player)
            
            # Weather adjustment
            weather_adjustment = self._evaluate_weather_impact(player)
            
            # Recent performance trend
            trend_adjustment = self._evaluate_trend(player)
            
            # Calculate total score
            total_score = self._calculate_total_score(
                base_projection, matchup_adjustment, injury_adjustment,
                weather_adjustment, trend_adjustment
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(player, week)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                player, base_projection, matchup_adjustment, injury_adjustment,
                weather_adjustment, trend_adjustment
            )
            
            return PlayerScore(
                player=player,
                total_score=total_score,
                base_projection=base_projection,
                matchup_adjustment=matchup_adjustment,
                injury_adjustment=injury_adjustment,
                weather_adjustment=weather_adjustment,
                trend_adjustment=trend_adjustment,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error evaluating player {player.name}: {e}")
            # Return a default low score
            return PlayerScore(
                player=player,
                total_score=0.0,
                base_projection=0.0,
                matchup_adjustment=0.0,
                injury_adjustment=0.0,
                weather_adjustment=0.0,
                trend_adjustment=0.0,
                confidence=0.0,
                reasoning=f"Error in evaluation: {e}"
            )
    
    def _get_base_projection(self, player: Player, week: int) -> float:
        """Get base projection for the player."""
        # Check for existing projection
        latest_projection = player.get_latest_projection()
        if latest_projection and latest_projection.week == week:
            return latest_projection.projected_points
        
        # Fallback to recent average (prefer this over position average)
        recent_average = player.get_average_points(weeks=4)
        if recent_average > 0:
            # Use recent average, but ensure it's reasonable for the position
            position_avg = self._get_position_average(player.position)
            # If recent average is significantly below position average, 
            # it might be due to injury or poor performance, so use a blend
            if recent_average < position_avg * 0.5:
                return max(recent_average, position_avg * 0.6)
            return recent_average
        
        # Fallback to intelligent position-based scoring
        return self._get_intelligent_fallback_score(player)
    
    def _evaluate_matchup(self, player: Player, opponent: Optional[str]) -> float:
        """Evaluate matchup strength."""
        if not player.matchup or not opponent:
            return 0.0
        
        adjustment = 0.0
        
        # Opponent defense ranking
        if player.matchup.opponent_defense_ranking:
            ranking = player.matchup.opponent_defense_ranking
            if ranking <= 10:  # Top 10 defense
                adjustment -= 2.0
            elif ranking <= 20:  # Average defense
                adjustment -= 0.5
            elif ranking >= 25:  # Poor defense
                adjustment += 1.0
        
        # Game total (higher total = more scoring potential)
        # Capped to prevent overriding player quality
        if player.matchup.game_total:
            total = player.matchup.game_total
            if total >= 50:
                adjustment += 1.0  # Reduced from 1.5
            elif total >= 45:
                adjustment += 0.3  # Reduced from 0.5
            elif total <= 40:
                adjustment -= 0.5  # Reduced from 1.0
        
        # Spread (favorable spread = positive game script)
        if player.matchup.spread:
            spread = player.matchup.spread
            if player.matchup.is_home:
                # Home team favored
                if spread > 3:
                    adjustment += 0.3  # Reduced from 0.5
                elif spread < -3:
                    adjustment -= 0.5  # Reduced from 1.0
            else:
                # Away team
                if spread < -3:
                    adjustment += 0.3  # Reduced from 0.5
                elif spread > 3:
                    adjustment -= 0.5  # Reduced from 1.0
        
        # Cap total matchup adjustment to prevent it from overriding player quality
        # Maximum adjustment is ±2.0 points (which becomes ±6.0 after weighting)
        return max(-2.0, min(2.0, adjustment))
    
    def _evaluate_injury_risk(self, player: Player) -> float:
        """Evaluate injury risk and impact."""
        if not player.injury_info:
            return 0.0
        
        adjustment = 0.0
        status = player.injury_info.status
        
        if status == InjuryStatus.OUT:
            adjustment = -50.0  # Should not be started
        elif status == InjuryStatus.DOUBTFUL:
            adjustment = -10.0
        elif status == InjuryStatus.QUESTIONABLE:
            if player.injury_info.probability_of_playing:
                prob = player.injury_info.probability_of_playing
                if prob < 0.5:
                    adjustment = -5.0
                elif prob < 0.75:
                    adjustment = -2.0
                else:
                    adjustment = -0.5
            else:
                adjustment = -3.0
        elif status == InjuryStatus.IR:
            adjustment = -50.0
        
        return adjustment
    
    def _evaluate_weather_impact(self, player: Player) -> float:
        """Evaluate weather impact on player performance."""
        if not player.matchup or not player.matchup.weather:
            return 0.0
        
        weather = player.matchup.weather
        adjustment = 0.0
        
        # Skip weather adjustments for dome games
        if weather.is_dome:
            return 0.0
        
        # Wind impact (affects passing and kicking)
        if weather.wind_speed:
            wind = weather.wind_speed
            if player.position in [Position.QB, Position.K]:
                if wind > 20:
                    adjustment -= 3.0
                elif wind > 15:
                    adjustment -= 1.5
                elif wind > 10:
                    adjustment -= 0.5
        
        # Precipitation impact
        if weather.precipitation_chance:
            precip = weather.precipitation_chance
            if precip > 0.7:
                if player.position in [Position.QB, Position.WR, Position.TE]:
                    adjustment -= 1.0
                elif player.position == Position.K:
                    adjustment -= 2.0
        
        # Temperature impact (extreme cold affects passing)
        if weather.temperature:
            temp = weather.temperature
            if temp < 20 and player.position in [Position.QB, Position.WR, Position.TE]:
                adjustment -= 1.0
        
        return adjustment
    
    def _evaluate_trend(self, player: Player) -> float:
        """Evaluate recent performance trend."""
        trend = player.get_trend(weeks=4)
        
        # Convert trend to adjustment
        if trend > 2.0:  # Strong upward trend
            return 2.0
        elif trend > 1.0:  # Moderate upward trend
            return 1.0
        elif trend > 0.5:  # Slight upward trend
            return 0.5
        elif trend < -2.0:  # Strong downward trend
            return -2.0
        elif trend < -1.0:  # Moderate downward trend
            return -1.0
        elif trend < -0.5:  # Slight downward trend
            return -0.5
        
        return 0.0
    
    def _calculate_total_score(self, base_projection: float, matchup_adjustment: float,
                             injury_adjustment: float, weather_adjustment: float,
                             trend_adjustment: float) -> float:
        """Calculate total evaluation score."""
        # Note: This method is primarily for compatibility with main.py
        # The primary optimization method uses betting data (odds API) via waiver_optimizer.py
        # Decision weights are optional - if all are 0, just use base projection
        total = base_projection
        
        # Only apply weights if they're configured (non-zero)
        if any([self.config.matchup_weight, self.config.injury_weight, 
                self.config.weather_weight, self.config.recent_performance_weight]):
            total += matchup_adjustment * self.config.matchup_weight * 10
            total += injury_adjustment * self.config.injury_weight
            total += weather_adjustment * self.config.weather_weight * 10
            total += trend_adjustment * self.config.recent_performance_weight * 10
        
        return max(0.0, total)  # Ensure non-negative score
    
    def _calculate_confidence(self, player: Player, week: int) -> float:
        """Calculate confidence in the evaluation."""
        confidence = 0.5  # Base confidence
        
        # Recent data availability
        recent_stats = player.get_recent_stats(weeks=4)
        if len(recent_stats) >= 3:
            confidence += 0.2
        elif len(recent_stats) >= 1:
            confidence += 0.1
        
        # Projection availability
        if player.get_latest_projection():
            confidence += 0.2
        
        # Injury clarity
        if player.injury_info:
            if player.injury_info.status in [InjuryStatus.HEALTHY, InjuryStatus.OUT]:
                confidence += 0.1
        
        # Weather data availability
        if player.matchup and player.matchup.weather:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_reasoning(self, player: Player, base_projection: float,
                          matchup_adjustment: float, injury_adjustment: float,
                          weather_adjustment: float, trend_adjustment: float) -> str:
        """Generate human-readable reasoning for the evaluation."""
        reasons = []
        
        # Base projection
        reasons.append(f"Base projection: {base_projection:.1f} points")
        
        # Matchup
        if matchup_adjustment != 0:
            if matchup_adjustment > 0:
                reasons.append(f"Favorable matchup (+{matchup_adjustment:.1f})")
            else:
                reasons.append(f"Tough matchup ({matchup_adjustment:.1f})")
        
        # Injury
        if injury_adjustment != 0:
            if player.injury_info:
                reasons.append(f"Injury concern: {player.injury_info.status.value} ({injury_adjustment:.1f})")
        
        # Weather
        if weather_adjustment != 0:
            if weather_adjustment > 0:
                reasons.append(f"Favorable weather (+{weather_adjustment:.1f})")
            else:
                reasons.append(f"Weather concern ({weather_adjustment:.1f})")
        
        # Trend
        if trend_adjustment != 0:
            if trend_adjustment > 0:
                reasons.append(f"Positive trend (+{trend_adjustment:.1f})")
            else:
                reasons.append(f"Declining trend ({trend_adjustment:.1f})")
        
        return "; ".join(reasons)
    
    def _get_position_average(self, position: Position) -> float:
        """Get average fantasy points for a position."""
        averages = {
            Position.QB: 18.0,
            Position.RB: 12.0,
            Position.WR: 10.0,
            Position.TE: 8.0,
            Position.K: 8.0,
            Position.DEF: 7.0
        }
        return averages.get(position, 5.0)
    
    def _get_intelligent_fallback_score(self, player: Player) -> float:
        """Get intelligent fallback score based on position averages and general factors."""
        base_score = self._get_position_average(player.position)
        
        # Apply general adjustments based on available data
        # This avoids hardcoding specific player names
        
        # If player has recent stats, use them as a baseline (prefer this over position average)
        if player.stats and player.stats.points > 0:
            # Use recent performance as the primary guide
            recent_performance = player.stats.points
            # If recent performance is significantly different from position average,
            # weight it more heavily (70% recent, 30% position average)
            if abs(recent_performance - base_score) > 2.0:
                base_score = recent_performance * 0.7 + base_score * 0.3
            else:
                # If close to average, use recent performance directly
                base_score = recent_performance
        
        # If player has injury status, adjust accordingly
        if player.injury_info:
            if player.injury_info.status.value in ['OUT', 'IR']:
                base_score = 0.0  # Injured players get 0
            elif player.injury_info.status.value == 'DOUBTFUL':
                base_score *= 0.3  # Severely reduced
            elif player.injury_info.status.value == 'QUESTIONABLE':
                base_score *= 0.7  # Moderately reduced
        
        # Position-specific general adjustments
        if player.position == Position.QB:
            # QBs generally have higher variance, so use a wider range
            base_score = max(8.0, min(25.0, base_score))
        elif player.position == Position.RB:
            # RBs are heavily dependent on game script and touches
            base_score = max(3.0, min(20.0, base_score))
        elif player.position == Position.WR:
            # WRs have moderate variance
            base_score = max(2.0, min(18.0, base_score))
        elif player.position == Position.TE:
            # TEs have lower floor but can have big games
            base_score = max(1.0, min(15.0, base_score))
        elif player.position == Position.K:
            # Kickers are more consistent
            base_score = max(5.0, min(12.0, base_score))
        elif player.position == Position.DEF:
            # Defenses vary widely based on matchup
            base_score = max(2.0, min(20.0, base_score))
        
        return max(0.0, base_score)  # Ensure non-negative
    
    def _get_position_weights(self) -> Dict[Position, float]:
        """Get position-specific evaluation weights."""
        return {
            Position.QB: 1.0,
            Position.RB: 1.0,
            Position.WR: 1.0,
            Position.TE: 1.0,
            Position.K: 0.8,
            Position.DEF: 0.9
        }
    
    def rank_players_by_position(self, players: List[Player], week: int) -> Dict[Position, List[PlayerScore]]:
        """Rank players by position for the given week."""
        rankings = {}
        
        for position in Position:
            position_players = [p for p in players if p.position == position]
            if position_players:
                scores = [self.evaluate_player(p, week) for p in position_players]
                scores.sort(key=lambda x: x.total_score, reverse=True)
                rankings[position] = scores
        
        return rankings
    
    def get_top_players(self, players: List[Player], week: int, count: int = 10) -> List[PlayerScore]:
        """Get top players across all positions."""
        all_scores = [self.evaluate_player(p, week) for p in players]
        all_scores.sort(key=lambda x: x.total_score, reverse=True)
        return all_scores[:count]
