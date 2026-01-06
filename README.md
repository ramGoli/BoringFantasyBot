# Fantasy Football Auto-Lineup Bot

A Python application that automatically optimizes and manages your Yahoo Fantasy Football lineup using **real-time betting data** from The Odds API. The bot analyzes game lines, player props, and betting odds to generate optimal lineups.

## 🚀 Quick Start (5 Minutes)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Yahoo API credentials**
   - Go to [Yahoo Developer Network](https://developer.yahoo.com/apps/)
   - Create a new "Web Application"
   - Set Redirect URI to: `http://localhost:8080/callback`
   - Copy your Client ID and Client Secret

3. **Configure the bot**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your credentials
   ```

4. **Find your League and Team IDs**
   - League ID: Look at your Yahoo Fantasy league URL: `https://football.fantasysports.yahoo.com/f1/LEAGUE_ID`
   - Team ID: Click on your team, URL will be: `https://football.fantasysports.yahoo.com/f1/LEAGUE_ID/TEAM_ID`
   - Or run: `python find_league_ids.py` (after authentication)

5. **Get The Odds API Key (Recommended)**
   - Sign up at [The Odds API](https://the-odds-api.com/)
   - Free tier: 500 requests/month
   - Add your API key to `config.yaml` under `external_apis.odds_api_key`

6. **Run the bot**
   ```bash
   # Primary method: Betting-based optimizer
   python waiver_optimizer.py
   
   # Or use the main bot (also supports betting data)
   python -m src.main --once
   ```
   This will open a browser for Yahoo OAuth authentication on first run.

## 📋 Prerequisites

- Python 3.8 or higher
- Yahoo Fantasy Sports account
- Yahoo Developer App credentials (free)
- **The Odds API key** for betting-based optimization (free tier: 500 requests/month) - **Recommended**

## 🎯 Features

### Core Functionality
- **Betting-Based Optimization**: Primary method uses real-time betting data from The Odds API
- **Automated Lineup Optimization**: Intelligent lineup decisions based on betting odds and player props
- **Yahoo Fantasy Integration**: Full API integration for roster management
- **Waiver Wire Management**: Automated pickup suggestions based on betting scores
- **Injury Filtering**: Automatic exclusion of injured/out players from lineups

### Betting Data Analysis
- **Game Lines**: Analyzes spreads and totals to identify high-scoring games
- **Player Props**: TD odds, rushing/receiving yards, receptions, and QB-specific props
- **Betting Score Calculation**: Aggregates all betting signals into a single optimization score
- **Week-Specific Data**: Date-filtered betting data for accurate weekly projections
- **Position-Specific Analysis**: Different scoring for QB, RB, WR, TE based on relevant props

### Automation
- **Scheduled Execution**: Daily/weekly automated runs
- **Injury Monitoring**: Real-time injury updates and replacements
- **Performance Tracking**: Historical decision analysis
- **Dry Run Mode**: Safe testing without making changes

## 📦 Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/fantasyFootball.git
cd fantasyFootball
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Get Yahoo API Credentials

1. Visit [Yahoo Developer Network](https://developer.yahoo.com/apps/)
2. Click "Create an App"
3. Fill in the form:
   - **Application Name**: Fantasy Football Bot (or any name)
   - **Application Type**: Web Application
   - **Redirect URI**: `http://localhost:8080/callback`
   - **Description**: Auto-lineup optimizer for Yahoo Fantasy Football
4. Click "Create App"
5. Copy your **Client ID** and **Client Secret**

### Step 4: Configure the Bot

1. Copy the example configuration:
   ```bash
   cp config.yaml.example config.yaml
   ```

2. Edit `config.yaml` with your settings:
   ```yaml
   # League settings
   league_id: "your_league_id_here"
   team_id: "your_team_id_here"
   
   # Yahoo API credentials
   yahoo_api:
     client_id: "your_yahoo_client_id_here"
     client_secret: "your_yahoo_client_secret_here"
     redirect_uri: "http://localhost:8080/callback"
   
   # Optional: The Odds API (recommended for betting-based optimization)
   external_apis:
     odds_api_key: "your_odds_api_key_here"  # Get from https://the-odds-api.com/
   ```

### Step 5: Find Your League and Team IDs

**Method 1: From Yahoo Fantasy URLs**
- Open your Yahoo Fantasy Football league
- Look at the URL: `https://football.fantasysports.yahoo.com/f1/LEAGUE_ID`
- The number after `/f1/` is your League ID
- Click on your team name
- The URL will be: `https://football.fantasysports.yahoo.com/f1/LEAGUE_ID/TEAM_ID`
- The number after the League ID is your Team ID

**Method 2: Using the Helper Script**
```bash
python find_league_ids.py
```
This will authenticate and show your available leagues and teams.

### Step 6: (Optional) Get The Odds API Key

The Odds API provides betting lines and player props for better lineup optimization:

1. Sign up at [The Odds API](https://the-odds-api.com/)
2. Free tier includes 500 requests/month
3. Copy your API key
4. Add it to `config.yaml` under `external_apis.odds_api_key`

## 🎮 Usage

### First-Time Setup

Run the bot for the first time to authenticate:
```bash
python -m src.main --once
```

This will:
1. Open your browser for Yahoo OAuth authentication
2. Ask you to authorize the application
3. Save authentication tokens for future use

### Regular Usage

#### Run Once (Manual)
```bash
python -m src.main --once
```

#### Run for Specific Week
```bash
python -m src.main --once --week 5
```

#### Run Scheduled Tasks (Automated)
```bash
python -m src.main --schedule
```

This will run the bot on a schedule (default: daily at 8:00 AM).

### Betting-Optimized Lineup Tool

The `waiver_optimizer.py` script uses real-time betting odds to optimize your lineup:

**Run for current week:**
```bash
python waiver_optimizer.py
```

**Run for a specific week:**
```bash
WEEK_OVERRIDE=9 python waiver_optimizer.py
```

**What it does:**
1. Fetches your current Yahoo Fantasy roster
2. Gets betting data (game lines, player props) from The Odds API
3. Calculates betting scores for each player
4. Filters out injured/non-starting players
5. Generates optimal lineup
6. Suggests waiver wire pickups

**Example Output:**
```
🏆 OPTIMAL STARTING LINEUP:
------------------------------
QB:  Patrick Mahomes (Score: +3)
RB1: De'Von Achane (Score: +29)
RB2: Jonathan Taylor (Score: +40)
WR1: Davante Adams (Score: +20)
WR2: Xavier Worthy (Score: +3)
FLEX: Saquon Barkley (RB) (Score: +0)
TE:  Hunter Henry (Score: +30)
K:   Tyler Loop (Score: -1)
DEF: Philadelphia (Score: +0)
```

### Auto-Submit Lineup

Use `auto_submit_lineup.py` to automatically submit the optimal lineup:
```bash
python auto_submit_lineup.py
```

This will:
1. Analyze all players
2. Generate optimal lineup
3. Show you what will be submitted
4. Ask for confirmation
5. Submit to Yahoo Fantasy

## ⚙️ Configuration

### Basic Settings (`config.yaml`)

```yaml
# User preferences
risk_tolerance: "medium"  # conservative, medium, aggressive
auto_submit: true         # Automatically submit lineup changes
dry_run_mode: false       # Set to true to preview without making changes

# League settings
league_id: "your_league_id"
team_id: "your_team_id"

# Automation settings
run_daily_at: "08:00"     # Time to run daily optimization
backup_before_games: true
waiver_wire_management: true
```

### Risk Tolerance Levels

- **Conservative**: Prioritizes consistency and high-confidence players
- **Medium**: Balances upside and reliability (recommended)
- **Aggressive**: Maximizes potential upside, accepts higher variance

## 🔧 How It Works

### 1. Data Collection
The bot gathers data from:
- **Yahoo Fantasy API**: Current roster, player stats, league settings, injury status
- **The Odds API**: Real-time game lines (spreads, totals) and player props (TD odds, yardage lines, receptions)
- **Betting Data**: Primary optimization method using Vegas odds and player props

### 2. Betting Score Calculation
Each player receives a betting score based on:
- **Game Totals**: Higher totals = more scoring opportunities (+3 for ≥50, +1 for ≥45, -2 for ≤40)
- **Spreads**: Favorite teams get bonus points (+2 for favorites with spread >3 or <-3)
- **TD Odds**: Players with negative odds (TD favorites) get +3, contenders (<200 odds) get +1
- **Yardage Props**: Higher rushing/receiving lines = higher scores
- **Reception Props**: High reception expectations (≥6) get +2 points
- **QB-Specific Props**: Additional scoring for passing TDs, yards, completions, attempts

### 3. Lineup Optimization
The bot optimizes lineups by:
- **Betting Scores**: Selecting players with highest betting scores for each position
- **Position Requirements**: Meeting league roster requirements (QB, 2RB, 2WR, FLEX, TE, K, DEF)
- **Injury Filtering**: Automatically excludes injured/non-starting players
- **Best Available**: Fills all required positions with highest-scoring available players

### 4. Decision Execution
- **Dry Run Mode**: Preview changes without submitting
- **Auto-Submit**: Automatically apply optimized lineups
- **Manual Override**: Review and approve changes
- **Rollback**: Revert to previous lineup if needed

## 📁 Project Structure

```
fantasyFootball/
├── src/
│   ├── api/
│   │   ├── yahoo_client.py          # Yahoo API wrapper
│   │   ├── external_data.py         # Betting odds, weather, injuries, projections
│   │   ├── auth_manager.py          # OAuth handling
│   │   ├── fantasypros_scraper.py   # FantasyPros web scraper
│   │   └── rotowire_api.py          # Rotowire API client
│   ├── analysis/
│   │   ├── player_evaluator.py      # Player scoring system
│   │   └── lineup_optimizer.py      # Lineup decision engine
│   ├── data/
│   │   ├── models.py               # Data classes
│   │   ├── storage.py              # Database operations
│   │   └── nfl_venues.py            # NFL venue data
│   ├── config/
│   │   └── settings.py             # Configuration management
│   └── main.py                     # Main application
├── waiver_optimizer.py             # Betting-optimized lineup tool
├── auto_submit_lineup.py           # Auto-submit optimal lineup
├── find_league_ids.py              # Helper to find league/team IDs
├── tests/                          # Unit tests
├── requirements.txt                # Dependencies
├── config.yaml.example             # Configuration template
└── README.md                       # This file
```

## 🧪 Testing

Test your setup with these scripts:

```bash
# Test Yahoo connection
python test_yahoo_enhanced.py

# Test FantasyPros scraper
python test_fantasypros.py

# Test simple auth
python test_simple_auth.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Yahoo API credentials in `config.yaml`
   - Check that redirect URI matches Yahoo app settings
   - Clear `tokens.json` and re-authenticate: `rm tokens.json`

2. **League/Team ID Issues**
   - Verify IDs are correct in configuration
   - Ensure you have access to the specified league
   - Check that the season is active
   - Use `python find_league_ids.py` to find your IDs

3. **API Rate Limiting**
   - Bot includes built-in rate limiting
   - Increase delays in configuration if needed
   - Check Yahoo API status

4. **External Data Failures**
   - Bot continues with available data
   - Check API keys for external services
   - Review logs for specific error messages

5. **No Betting Data Available**
   - Verify The Odds API key is set in `config.yaml`
   - Check API quota (free tier: 500 requests/month)
   - Clear cache: `python -c "from src.api.external_data import VegasAPI; VegasAPI().clear_cache()"`
   - Wait a few hours if Week 9+ odds aren't posted yet

### Logs and Debugging

- **Log File**: `fantasy_bot.log` (configurable location)
- **Log Level**: Adjust in `config.yaml`
- **Database**: `fantasy_bot.db` for data inspection
- **Cache**: `cache/` directory for temporary data

## 🔒 Security Best Practices

**IMPORTANT**: Never commit sensitive files to version control!

- ✅ `config.yaml` is in `.gitignore` - never commit it
- ✅ `tokens.json` is in `.gitignore` - contains OAuth tokens
- ✅ `oauth2.json` is in `.gitignore` - contains API credentials
- ✅ Keep your API keys private
- ✅ Don't share your league/team IDs publicly
- ✅ Review changes before auto-submitting lineups

## 📊 API Integration

### Yahoo Fantasy Sports API
- **Authentication**: OAuth2 with automatic token refresh
- **Rate Limiting**: Built-in request throttling
- **Error Handling**: Graceful API failure recovery
- **Caching**: Local data caching to minimize requests

### External Data Sources
- **The Odds API**: Game lines (spreads, totals) and player props (TD odds, yardage lines, receptions)
- **ESPN Fantasy API**: Primary projection source (free, official data)
- **Injury Reports**: Player availability status from Yahoo
- **Backup Projections**: CBS Sports, NFL.com, NumberFire
- **Weather Data**: Optional, comes from Rotowire API (paid subscription) - not required for bot to function

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please ensure compliance with:
- Yahoo Fantasy Sports Terms of Service
- Your league's rules and regulations
- Applicable laws and regulations

The developers are not responsible for any consequences of using this bot, including but not limited to:
- League rule violations
- Account suspensions
- Financial losses
- Disputes with league members

Use at your own risk and always review decisions before applying them to your team.

## 📚 Additional Resources

- [Yahoo Developer Network](https://developer.yahoo.com/)
- [The Odds API Documentation](https://the-odds-api.com/liveapi/guides/v4/)
- [Yahoo Fantasy Sports API Documentation](https://developer.yahoo.com/fantasysports/guide/)

## 💬 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Open an issue on GitHub
4. Check the documentation

---

**Happy Fantasy Football Season! 🏈**
