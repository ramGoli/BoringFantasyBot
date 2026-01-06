#!/usr/bin/env python3
"""
Test script for enhanced Yahoo Fantasy API client.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.auth_manager import YahooAuthManager
from src.api.yahoo_client import YahooFantasyClient

def test_enhanced_yahoo_client():
    """Test the enhanced Yahoo client functionality."""
    print("🧪 Testing Enhanced Yahoo Fantasy API Client...")
    print("=" * 60)
    
    try:
        # Initialize authentication
        print("\n🔐 Initializing authentication...")
        auth_manager = YahooAuthManager()
        
        # Initialize Yahoo client
        print("📡 Initializing Yahoo client...")
        yahoo_client = YahooFantasyClient()
        yahoo_client.authenticate(auth_manager)
        yahoo_client.initialize_league()
        
        print("✅ Yahoo client initialized successfully!")
        
        # Test getting roster
        print("\n👥 Testing roster retrieval...")
        roster = yahoo_client.get_roster()
        print(f"✅ Retrieved {len(roster)} players from roster")
        
        if roster:
            print("\n🏃 Current roster:")
            for i, player in enumerate(roster[:10]):  # Show first 10
                status = "STARTING" if player.is_starting else "BENCH"
                print(f"  {i+1}. {player.name} ({player.position.value}) - {status}")
        
        # Test getting Yahoo projections
        print("\n📊 Testing Yahoo projections...")
        projections = yahoo_client.get_player_projections(1)  # Week 1
        print(f"✅ Retrieved {len(projections)} player projections")
        
        if projections:
            print("\n🎯 Projections for Week 1:")
            for proj in projections[:5]:  # Show first 5
                print(f"  {proj.player_name}: {proj.projected_points:.1f} points")
        
        # Test getting league settings
        print("\n⚙️ Testing league settings...")
        settings = yahoo_client.get_league_settings()
        print(f"✅ League: {settings.name}")
        print(f"   Season: {settings.season}")
        print(f"   Positions: {sum(settings.roster_positions.values())} roster spots")
        
        # Test getting available players
        print("\n🆓 Testing available players...")
        available = yahoo_client.get_available_players('RB', 10)  # Top 10 RBs
        print(f"✅ Retrieved {len(available)} available RB players")
        
        if available:
            print("\n🏃 Top available RBs:")
            for i, player in enumerate(available[:5]):
                print(f"  {i+1}. {player.name} ({player.position.value})")
        
        # Test getting weekly matchup
        print("\n🏆 Testing weekly matchup...")
        matchup = yahoo_client.get_weekly_matchup(1)  # Week 1
        if matchup:
            print(f"✅ Week 1 matchup found")
            print(f"   Opponent: {matchup.get('opponent', {}).get('name', 'Unknown')}")
        else:
            print("ℹ️ No matchup data available for Week 1")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_yahoo_client()
    sys.exit(0 if success else 1)
