"""
Lineup optimization engine for the Fantasy Football Auto-Lineup Bot.
Makes intelligent lineup decisions based on player evaluations and league rules.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from copy import deepcopy

from ..data.models import Player, Lineup, LineupSlot, Position, RiskLevel
from .player_evaluator import PlayerEvaluator, PlayerScore
from ..config.settings import get_config


logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of lineup optimization."""
    optimized_lineup: Lineup
    total_projected_points: float
    changes_made: List[Dict[str, any]]
    reasoning: str
    confidence: float
    risk_level: RiskLevel


class LineupOptimizer:
    """Optimizes fantasy football lineups based on player evaluations."""
    
    def __init__(self):
        self.config = get_config()
        self.evaluator = PlayerEvaluator()
    
    def optimize_lineup(self, current_lineup: Lineup, available_players: List[Player], 
                       week: int) -> OptimizationResult:
        """Optimize the current lineup for the given week."""
        try:
            # Evaluate all available players
            player_scores = self._evaluate_all_players(available_players, week)
            
            # Create a copy of the current lineup for optimization
            optimized_lineup = deepcopy(current_lineup)
            
            # Track changes made
            changes_made = []
            
            # Optimize each position
            for slot in optimized_lineup.slots:
                current_player = slot.player
                best_player = self._find_best_player_for_position(
                    slot.position, player_scores, optimized_lineup
                )
                
                if best_player and best_player != current_player:
                    # Make the change
                    old_player = slot.player
                    slot.player = best_player
                    slot.is_filled = True
                    
                    changes_made.append({
                        'position': slot.position.value,
                        'old_player': old_player.name if old_player else 'Empty',
                        'new_player': best_player.name,
                        'score_improvement': self._get_score_improvement(old_player, best_player, player_scores)
                    })
            
            # Calculate total projected points
            total_points = self._calculate_total_projected_points(optimized_lineup, player_scores)
            
            # Determine risk level
            risk_level = self._assess_risk_level(optimized_lineup, player_scores)
            
            # Generate reasoning
            reasoning = self._generate_optimization_reasoning(changes_made, player_scores)
            
            # Calculate confidence
            confidence = self._calculate_optimization_confidence(optimized_lineup, player_scores)
            
            return OptimizationResult(
                optimized_lineup=optimized_lineup,
                total_projected_points=total_points,
                changes_made=changes_made,
                reasoning=reasoning,
                confidence=confidence,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error optimizing lineup: {e}")
            # Return current lineup unchanged
            return OptimizationResult(
                optimized_lineup=current_lineup,
                total_projected_points=0.0,
                changes_made=[],
                reasoning=f"Error in optimization: {e}",
                confidence=0.0,
                risk_level=RiskLevel.HIGH
            )
    
    def _evaluate_all_players(self, players: List[Player], week: int) -> Dict[str, PlayerScore]:
        """Evaluate all available players and return scores."""
        scores = {}
        for player in players:
            score = self.evaluator.evaluate_player(player, week)
            scores[player.player_id] = score
        return scores
    
    def _find_best_player_for_position(self, position: Position, player_scores: Dict[str, PlayerScore],
                                     current_lineup: Lineup) -> Optional[Player]:
        """Find the best available player for a specific position."""
        # Get all players eligible for this position
        eligible_players = []
        used_player_ids = self._get_used_player_ids(current_lineup)
        
        for player_id, score in player_scores.items():
            player = score.player
            # Skip if player is already used in the lineup
            if player.player_id in used_player_ids:
                continue
                
            if (player.position == position or 
                position in player.eligible_positions or
                self._can_play_flex(player, position, current_lineup)):
                eligible_players.append(score)
        
        if not eligible_players:
            return None
        
        # Sort by score and apply risk tolerance
        eligible_players.sort(key=lambda x: x.total_score, reverse=True)
        
        # Apply risk tolerance filtering
        if self.config.risk_tolerance == "conservative":
            # Prefer players with higher confidence
            eligible_players.sort(key=lambda x: (x.confidence, x.total_score), reverse=True)
        elif self.config.risk_tolerance == "aggressive":
            # Prefer players with higher upside (higher scores regardless of confidence)
            pass  # Already sorted by total_score
        
        # Return the best player
        return eligible_players[0].player if eligible_players else None
    
    def _get_used_player_ids(self, lineup: Lineup) -> Set[str]:
        """Get set of player IDs already used in the lineup."""
        used_ids = set()
        for slot in lineup.slots:
            if slot.player and slot.player.player_id:
                used_ids.add(slot.player.player_id)
        return used_ids
    
    def _can_play_flex(self, player: Player, position: Position, lineup: Lineup) -> bool:
        """Check if a player can play in a FLEX position."""
        if position not in [Position.FLEX, Position.SUPER_FLEX]:
            return False
        
        # Check if player is eligible for FLEX
        if position == Position.FLEX:
            return player.position in [Position.RB, Position.WR, Position.TE]
        elif position == Position.SUPER_FLEX:
            return player.position in [Position.QB, Position.RB, Position.WR, Position.TE]
        
        return False
    
    def _get_score_improvement(self, old_player: Optional[Player], new_player: Player,
                             player_scores: Dict[str, PlayerScore]) -> float:
        """Calculate the score improvement from a player change."""
        old_score = 0.0
        if old_player and old_player.player_id in player_scores:
            old_score = player_scores[old_player.player_id].total_score
        
        new_score = 0.0
        if new_player.player_id in player_scores:
            new_score = player_scores[new_player.player_id].total_score
        
        return new_score - old_score
    
    def _calculate_total_projected_points(self, lineup: Lineup, 
                                        player_scores: Dict[str, PlayerScore]) -> float:
        """Calculate total projected points for the lineup."""
        total = 0.0
        for slot in lineup.slots:
            if slot.player and slot.player.player_id in player_scores:
                total += player_scores[slot.player.player_id].total_score
        return total
    
    def _assess_risk_level(self, lineup: Lineup, player_scores: Dict[str, PlayerScore]) -> RiskLevel:
        """Assess the risk level of the optimized lineup."""
        if not lineup.slots:
            return RiskLevel.HIGH
        
        # Calculate average confidence
        confidences = []
        for slot in lineup.slots:
            if slot.player and slot.player.player_id in player_scores:
                confidences.append(player_scores[slot.player.player_id].confidence)
        
        if not confidences:
            return RiskLevel.HIGH
        
        avg_confidence = sum(confidences) / len(confidences)
        
        # Count players with low confidence
        low_confidence_count = sum(1 for c in confidences if c < 0.6)
        low_confidence_ratio = low_confidence_count / len(confidences)
        
        # Determine risk level
        if avg_confidence >= 0.8 and low_confidence_ratio <= 0.2:
            return RiskLevel.LOW
        elif avg_confidence >= 0.6 and low_confidence_ratio <= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    def _generate_optimization_reasoning(self, changes_made: List[Dict], 
                                       player_scores: Dict[str, PlayerScore]) -> str:
        """Generate reasoning for the optimization decisions."""
        if not changes_made:
            return "No changes needed - current lineup is optimal"
        
        reasons = []
        total_improvement = 0.0
        
        for change in changes_made:
            improvement = change['score_improvement']
            total_improvement += improvement
            
            if improvement > 0:
                reasons.append(
                    f"Upgraded {change['position']}: {change['old_player']} → "
                    f"{change['new_player']} (+{improvement:.1f} points)"
                )
            else:
                reasons.append(
                    f"Changed {change['position']}: {change['old_player']} → "
                    f"{change['new_player']} ({improvement:.1f} points)"
                )
        
        summary = f"Total improvement: {total_improvement:.1f} points"
        return f"{summary}; {'; '.join(reasons)}"
    
    def _calculate_optimization_confidence(self, lineup: Lineup, 
                                         player_scores: Dict[str, PlayerScore]) -> float:
        """Calculate confidence in the optimization result."""
        if not lineup.slots:
            return 0.0
        
        # Calculate weighted average confidence based on projected points
        total_points = 0.0
        weighted_confidence = 0.0
        
        for slot in lineup.slots:
            if slot.player and slot.player.player_id in player_scores:
                score = player_scores[slot.player.player_id]
                total_points += score.total_score
                weighted_confidence += score.total_score * score.confidence
        
        if total_points == 0:
            return 0.0
        
        return weighted_confidence / total_points
    
    def optimize_with_constraints(self, current_lineup: Lineup, available_players: List[Player],
                                week: int, constraints: Dict) -> OptimizationResult:
        """Optimize lineup with additional constraints."""
        # Apply constraints to available players
        filtered_players = self._apply_constraints(available_players, constraints)
        
        # Run normal optimization with filtered players
        return self.optimize_lineup(current_lineup, filtered_players, week)
    
    def _apply_constraints(self, players: List[Player], constraints: Dict) -> List[Player]:
        """Apply constraints to filter available players."""
        filtered_players = players.copy()
        
        # Apply minimum confidence constraint
        if 'min_confidence' in constraints:
            min_confidence = constraints['min_confidence']
            filtered_players = [
                p for p in filtered_players
                if self.evaluator.evaluate_player(p, 1).confidence >= min_confidence
            ]
        
        # Apply position constraints
        if 'required_positions' in constraints:
            required_positions = constraints['required_positions']
            filtered_players = [
                p for p in filtered_players
                if p.position in required_positions
            ]
        
        # Apply team constraints (avoid too many players from same team)
        if 'max_players_per_team' in constraints:
            max_per_team = constraints['max_players_per_team']
            team_counts = {}
            for p in filtered_players:
                team = p.nfl_team.abbreviation
                team_counts[team] = team_counts.get(team, 0) + 1
            
            # This is a simplified approach - in production you'd want more sophisticated
            # team balancing logic
            
        return filtered_players
    
    def suggest_waiver_pickups(self, current_roster: List[Player], available_players: List[Player],
                             week: int, max_suggestions: int = 5) -> List[Dict]:
        """Suggest waiver wire pickups with smart position-based logic."""
        # Evaluate all available players
        player_scores = self._evaluate_all_players(available_players, week)
        
        # Get current roster scores
        roster_scores = {}
        for player in current_roster:
            score = self.evaluator.evaluate_player(player, week)
            roster_scores[player.player_id] = score
        
        # Group roster players by position
        roster_by_position = {}
        for player in current_roster:
            pos = player.position.value
            if pos not in roster_by_position:
                roster_by_position[pos] = []
            roster_by_position[pos].append((player, roster_scores[player.player_id]))
        
        # Define required positions and their counts
        required_positions = {
            'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'K': 1, 'DEF': 1
        }
        
        suggestions = []
        
        # For each position, find potential improvements
        for position, required_count in required_positions.items():
            if position not in roster_by_position:
                continue
                
            # Get current players in this position
            current_players = roster_by_position[position]
            
            # Find available players in the same position
            available_in_position = [
                (player_id, score) for player_id, score in player_scores.items()
                if score.player.position.value == position
            ]
            
            # Sort current players by score (worst first)
            current_players.sort(key=lambda x: x[1].total_score)
            
            # For each current player, see if there's a better replacement
            for current_player, current_score in current_players:
                # Skip if this would leave us with too few players in this position
                if len(current_players) <= required_count:
                    continue
                    
                # Find better available players in the same position
                for available_player_id, available_score in available_in_position:
                    if available_score.total_score > current_score.total_score:
                        improvement = available_score.total_score - current_score.total_score
                        
                        # Only suggest if improvement is significant (more than 2 points)
                        if improvement > 2.0:
                            suggestions.append({
                                'player': available_score.player,
                                'projected_points': available_score.total_score,
                                'improvement': improvement,
                                'reasoning': f"Better {position} option (+{improvement:.1f} points)",
                                'drop_candidate': current_player,
                                'position': position
                            })
        
        # Sort by improvement and return top suggestions
        suggestions.sort(key=lambda x: x['improvement'], reverse=True)
        return suggestions[:max_suggestions]
    
    def validate_lineup(self, lineup: Lineup, league_settings) -> Tuple[bool, List[str]]:
        """Validate that a lineup meets league requirements."""
        errors = []
        
        # Check required positions
        required_positions = league_settings.roster_positions
        position_counts = {}
        
        for slot in lineup.slots:
            if slot.player:
                pos = slot.player.position.value
                position_counts[pos] = position_counts.get(pos, 0) + 1
        
        for position, required_count in required_positions.items():
            actual_count = position_counts.get(position, 0)
            if actual_count < required_count:
                errors.append(f"Missing {required_count - actual_count} {position} player(s)")
            elif actual_count > required_count:
                errors.append(f"Too many {position} players ({actual_count} vs {required_count})")
        
        # Check for empty required slots
        for slot in lineup.slots:
            if slot.is_required and not slot.is_filled:
                errors.append(f"Empty required slot: {slot.position.value}")
        
        return len(errors) == 0, errors
