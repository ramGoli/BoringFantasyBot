#!/usr/bin/env python3
"""
Script to find your Yahoo Fantasy league and team IDs.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.auth_manager import auth_manager
import requests

def find_league_ids():
    """Find all accessible leagues and teams."""
    try:
        print("🔍 Finding your Yahoo Fantasy leagues...")
        
        # Get access token
        access_token = auth_manager.get_access_token()
        if not access_token:
            print("❌ No valid access token available")
            return
        
        # Create session with token
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'FantasyFootballBot/1.0'
        })
        
        # Get user's games
        games_url = "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl"
        response = session.get(games_url)
        response.raise_for_status()
        
        print("✅ Successfully connected to Yahoo Fantasy API")
        print("\n📋 Your NFL Fantasy Leagues:")
        print("=" * 50)
        
        # Parse the response to find leagues
        # This is a simplified version - you might need to adjust based on actual response
        data = response.text
        print("Raw response preview:")
        print(data[:500] + "..." if len(data) > 500 else data)
        
        print("\n🔧 To find your League ID and Team ID:")
        print("1. Go to your Yahoo Fantasy Football league")
        print("2. Look at the URL: https://football.fantasysports.yahoo.com/f1/LEAGUE_ID")
        print("3. The number after /f1/ is your League ID")
        print("4. Click on your team name")
        print("5. Look at the URL: https://football.fantasysports.yahoo.com/f1/LEAGUE_ID/TEAM_ID")
        print("6. The number after the League ID is your Team ID")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    find_league_ids()

