#!/usr/bin/env python3
"""
Test script for FantasyPros web scraper.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.fantasypros_scraper import FantasyProsScraper

def test_fantasypros_scraper():
    """Test the FantasyPros scraper functionality."""
    print("🧪 Testing FantasyPros Web Scraper...")
    print("=" * 50)
    
    scraper = FantasyProsScraper()
    
    # Test getting RB rankings
    print("\n📊 Testing RB Rankings...")
    try:
        rb_rankings = scraper.get_position_rankings('RB', 1)
        print(f"✅ Successfully scraped {len(rb_rankings)} RB rankings")
        
        if rb_rankings:
            print("\n🏃 Top 5 RBs:")
            for i, player in enumerate(rb_rankings[:5]):
                print(f"  {i+1}. {player['name']} - Rank #{player['rank']}")
                if player.get('projections'):
                    points = player['projections'].get('fantasy_points', 0)
                    print(f"     Projected: {points} fantasy points")
        
    except Exception as e:
        print(f"❌ Error getting RB rankings: {e}")
    
    # Test getting QB rankings
    print("\n📊 Testing QB Rankings...")
    try:
        qb_rankings = scraper.get_position_rankings('QB', 1)
        print(f"✅ Successfully scraped {len(qb_rankings)} QB rankings")
        
        if qb_rankings:
            print("\n🏈 Top 5 QBs:")
            for i, player in enumerate(qb_rankings[:5]):
                print(f"  {i+1}. {player['name']} - Rank #{player['rank']}")
                if player.get('projections'):
                    points = player['projections'].get('fantasy_points', 0)
                    print(f"     Projected: {points} fantasy points")
        
    except Exception as e:
        print(f"❌ Error getting QB rankings: {e}")
    
    # Test getting WR rankings
    print("\n📊 Testing WR Rankings...")
    try:
        wr_rankings = scraper.get_position_rankings('WR', 1)
        print(f"✅ Successfully scraped {len(wr_rankings)} WR rankings")
        
        if wr_rankings:
            print("\n🎯 Top 5 WRs:")
            for i, player in enumerate(wr_rankings[:5]):
                print(f"  {i+1}. {player['name']} - Rank #{player['rank']}")
                if player.get('projections'):
                    points = player['projections'].get('fantasy_points', 0)
                    print(f"     Projected: {points} fantasy points")
        
    except Exception as e:
        print(f"❌ Error getting WR rankings: {e}")
    
    # Test getting all rankings
    print("\n📊 Testing All Position Rankings...")
    try:
        all_rankings = scraper.get_all_rankings(1)
        total_players = sum(len(rankings) for rankings in all_rankings.values())
        print(f"✅ Successfully scraped {total_players} total players across all positions")
        
        for position, rankings in all_rankings.items():
            print(f"  {position}: {len(rankings)} players")
        
    except Exception as e:
        print(f"❌ Error getting all rankings: {e}")
    
    print("\n🎉 FantasyPros Scraper Test Complete!")

if __name__ == "__main__":
    test_fantasypros_scraper()

