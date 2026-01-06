#!/usr/bin/env python3
"""
Simple test script to verify Yahoo Fantasy API connection.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from yahoo_fantasy_api import game, league, team
import yahoo_oauth
import json

def test_yahoo_connection():
    """Test basic Yahoo Fantasy API connection."""
    try:
        print("Testing Yahoo Fantasy API connection...")
        
        # Try to authenticate using yahoo_oauth
        oauth = yahoo_oauth.OAuth2('oauth2.json', 'oauth2.json')
        
        if oauth.token_is_valid():
            print("✅ OAuth token is valid!")
            
            # Test getting available games
            yahoo_game = game.Game(oauth, 'nfl')
            print(f"✅ Connected to Yahoo Fantasy NFL game")
            
            # Test getting leagues
            leagues = yahoo_game.league_ids()
            print(f"✅ Found {len(leagues)} leagues")
            
            # Test specific league
            if leagues:
                league_id = leagues[0]
                yahoo_league = league.League(oauth, league_id)
                print(f"✅ Connected to league: {yahoo_league.name()}")
                
                # Test getting teams
                teams = yahoo_league.teams()
                print(f"✅ Found {len(teams)} teams in league")
                
                return True
        else:
            print("❌ OAuth token is not valid")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Yahoo Fantasy API: {e}")
        return False

if __name__ == "__main__":
    success = test_yahoo_connection()
    if success:
        print("\n🎉 Yahoo Fantasy API connection successful!")
    else:
        print("\n💥 Yahoo Fantasy API connection failed!")
        print("\nTo set up authentication:")
        print("1. Go to https://developer.yahoo.com/apps/")
        print("2. Create a new app")
        print("3. Download the oauth2.json file")
        print("4. Place it in this directory")
