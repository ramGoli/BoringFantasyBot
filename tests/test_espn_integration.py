"""
Tests for ESPN API integration.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from src.api.external_data import ESPNProjectionsAPI
from src.data.models import PlayerProjection


class TestESPNIntegration:
    """Test cases for ESPN API integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.espn_api = ESPNProjectionsAPI()
    
    def test_espn_api_initialization(self):
        """Test ESPN API initialization."""
        assert self.espn_api.base_url == "https://fantasy.espn.com/apis/v3/games/ffl"
        assert "FantasyFootballBot" in self.espn_api.session.headers['User-Agent']
    
    @patch('requests.Session.get')
    def test_espn_projection_success(self, mock_get):
        """Test successful ESPN projection retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'leaders': [
                {
                    'player': {
                        'fullName': 'Patrick Mahomes'
                    },
                    'stats': [
                        {
                            'value': 22.5
                        }
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test getting projection
        projection = self.espn_api.get_player_projection('Patrick Mahomes', 'QB', 1)
        
        assert projection is not None
        assert projection.projected_points == 22.5
        assert projection.source == "ESPN"
        assert projection.confidence == 0.75
    
    @patch('requests.Session.get')
    def test_espn_projection_not_found(self, mock_get):
        """Test when player is not found in ESPN data."""
        # Mock response with no matching player
        mock_response = Mock()
        mock_response.json.return_value = {
            'leaders': [
                {
                    'player': {
                        'fullName': 'Josh Allen'
                    },
                    'stats': [
                        {
                            'value': 20.0
                        }
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test getting projection for player not in results
        projection = self.espn_api.get_player_projection('Unknown Player', 'QB', 1)
        
        assert projection is None
    
    @patch('requests.Session.get')
    def test_espn_api_error_handling(self, mock_get):
        """Test ESPN API error handling."""
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")
        
        # Test error handling
        projection = self.espn_api.get_player_projection('Patrick Mahomes', 'QB', 1)
        
        assert projection is None
    
    def test_espn_cache_functionality(self):
        """Test ESPN API caching."""
        # Test cache clearing
        self.espn_api.clear_cache()
        assert len(self.espn_api._cache) == 0
    
    @patch('requests.Session.get')
    def test_espn_multiple_endpoints(self, mock_get):
        """Test that ESPN API tries multiple endpoints."""
        # Mock first endpoint to fail, second to succeed
        mock_response1 = Mock()
        mock_response1.json.side_effect = Exception("First endpoint failed")
        mock_response1.raise_for_status.return_value = None
        
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'players': [
                {
                    'player': {
                        'fullName': 'Patrick Mahomes'
                    },
                    'stats': [
                        {
                            'statSourceId': 1,
                            'value': 22.5
                        }
                    ]
                }
            ]
        }
        mock_response2.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        # Test that second endpoint is tried
        projection = self.espn_api.get_player_projection('Patrick Mahomes', 'QB', 1)
        
        # Should have tried multiple endpoints
        assert mock_get.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__])

