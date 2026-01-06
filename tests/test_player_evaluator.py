"""
Tests for the PlayerEvaluator module.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.data.models import Player, Team, Position, PlayerStats, InjuryInfo, InjuryStatus
from src.analysis.player_evaluator import PlayerEvaluator, PlayerScore


class TestPlayerEvaluator:
    """Test cases for PlayerEvaluator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = PlayerEvaluator()
        
        # Create test team
        self.test_team = Team(
            team_id="TEST",
            name="Test Team",
            abbreviation="TEST",
            city="Test City",
            conference="NFC",
            division="North"
        )
        
        # Create test player
        self.test_player = Player(
            player_id="12345",
            name="Test Player",
            position=Position.QB,
            team=self.test_team,
            nfl_team=self.test_team
        )
    
    def test_evaluate_player_basic(self):
        """Test basic player evaluation."""
        score = self.evaluator.evaluate_player(self.test_player, week=1)
        
        assert isinstance(score, PlayerScore)
        assert score.player == self.test_player
        assert score.total_score >= 0
        assert 0 <= score.confidence <= 1
        assert isinstance(score.reasoning, str)
    
    def test_evaluate_injured_player(self):
        """Test evaluation of injured player."""
        # Add injury info
        self.test_player.injury_info = InjuryInfo(
            status=InjuryStatus.OUT,
            description="Knee injury",
            probability_of_playing=0.0
        )
        
        score = self.evaluator.evaluate_player(self.test_player, week=1)
        
        # Injured player should have very low score
        assert score.total_score < 5.0
        assert "injury" in score.reasoning.lower()
    
    def test_evaluate_player_with_stats(self):
        """Test evaluation of player with historical stats."""
        # Add some stats
        stats = [
            PlayerStats(week=1, season=2024, fantasy_points=20.0),
            PlayerStats(week=2, season=2024, fantasy_points=18.0),
            PlayerStats(week=3, season=2024, fantasy_points=22.0)
        ]
        self.test_player.stats = stats
        
        score = self.evaluator.evaluate_player(self.test_player, week=4)
        
        # Should have higher confidence with stats
        assert score.confidence > 0.5
        assert score.base_projection > 0
    
    def test_get_position_average(self):
        """Test position average calculations."""
        qb_avg = self.evaluator._get_position_average(Position.QB)
        rb_avg = self.evaluator._get_position_average(Position.RB)
        
        assert qb_avg > 0
        assert rb_avg > 0
        assert qb_avg != rb_avg
    
    def test_rank_players_by_position(self):
        """Test ranking players by position."""
        # Create multiple players
        players = [
            Player(player_id="1", name="QB1", position=Position.QB, team=self.test_team, nfl_team=self.test_team),
            Player(player_id="2", name="QB2", position=Position.QB, team=self.test_team, nfl_team=self.test_team),
            Player(player_id="3", name="RB1", position=Position.RB, team=self.test_team, nfl_team=self.test_team)
        ]
        
        rankings = self.evaluator.rank_players_by_position(players, week=1)
        
        assert Position.QB in rankings
        assert Position.RB in rankings
        assert len(rankings[Position.QB]) == 2
        assert len(rankings[Position.RB]) == 1
    
    def test_get_top_players(self):
        """Test getting top players across positions."""
        players = [
            Player(player_id="1", name="Player1", position=Position.QB, team=self.test_team, nfl_team=self.test_team),
            Player(player_id="2", name="Player2", position=Position.RB, team=self.test_team, nfl_team=self.test_team),
            Player(player_id="3", name="Player3", position=Position.WR, team=self.test_team, nfl_team=self.test_team)
        ]
        
        top_players = self.evaluator.get_top_players(players, week=1, count=2)
        
        assert len(top_players) == 2
        assert all(isinstance(score, PlayerScore) for score in top_players)
        # Should be sorted by score
        assert top_players[0].total_score >= top_players[1].total_score


if __name__ == "__main__":
    pytest.main([__file__])

