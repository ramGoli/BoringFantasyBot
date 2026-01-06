# Fantasy Football Bot - Deployment Guide

## 🚀 Quick Start Options

### Option 1: GitHub Actions (Recommended for beginners)
**Cost**: Free  
**Setup Time**: 10 minutes  

1. **Push your code to GitHub**
2. **Add secrets to your repository**:
   - Go to Settings → Secrets and variables → Actions
   - Add these secrets:
     - `YAHOO_CLIENT_ID`: Your Yahoo client ID
     - `YAHOO_CLIENT_SECRET`: Your Yahoo client secret
     - `LEAGUE_ID`: Your league ID
     - `TEAM_ID`: Your team ID
3. **The bot will run automatically every Monday at 8 AM EST**

### Option 2: Local Mac (Free)
**Cost**: Free  
**Setup Time**: 5 minutes  

```bash
# Run in background
nohup python -m src.main --schedule > bot.log 2>&1 &

# Check if running
ps aux | grep python

# View logs
tail -f bot.log
```

### Option 3: Heroku ($7-25/month)
**Cost**: $7-25/month  
**Setup Time**: 15 minutes  

1. **Install Heroku CLI**
2. **Create Heroku app**:
   ```bash
   heroku create your-fantasy-bot
   ```
3. **Add buildpack**:
   ```bash
   heroku buildpacks:add heroku/python
   ```
4. **Set environment variables**:
   ```bash
   heroku config:set YAHOO_CLIENT_ID=your_client_id
   heroku config:set YAHOO_CLIENT_SECRET=your_client_secret
   heroku config:set LEAGUE_ID=your_league_id
   heroku config:set TEAM_ID=your_team_id
   ```
5. **Deploy**:
   ```bash
   git push heroku main
   ```

### Option 4: DigitalOcean Droplet ($5-10/month)
**Cost**: $5-10/month  
**Setup Time**: 30 minutes  

1. **Create a Droplet** (Ubuntu 20.04)
2. **SSH into your droplet**:
   ```bash
   ssh root@your-droplet-ip
   ```
3. **Install dependencies**:
   ```bash
   apt update
   apt install python3 python3-pip git screen
   ```
4. **Clone and setup**:
   ```bash
   git clone https://github.com/yourusername/fantasyFootball.git
   cd fantasyFootball
   pip3 install -r requirements.txt
   cp config.yaml.example config.yaml
   # Edit config.yaml with your credentials
   ```
5. **Run in screen session**:
   ```bash
   screen -S fantasy-bot
   python3 -m src.main --schedule
   # Press Ctrl+A, then D to detach
   ```

## 🔧 Configuration

### Environment Variables
Set these in your hosting environment:

```bash
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
LEAGUE_ID=your_league_id
TEAM_ID=your_team_id
WEATHER_API_KEY=your_weather_api_key  # Optional
```

### Schedule Configuration
The bot runs on this schedule by default:
- **Monday 8 AM EST**: Weekly lineup optimization
- **Daily 8 AM EST**: Injury checks and updates
- **Before games**: Final lineup verification

## 📊 Monitoring

### Logs
- **Local**: Check `fantasy_bot.log`
- **Heroku**: `heroku logs --tail`
- **DigitalOcean**: `tail -f bot.log`

### Health Checks
The bot creates these files for monitoring:
- `tokens.json`: OAuth tokens
- `fantasy_bot.db`: SQLite database with decisions
- `fantasy_bot.log`: Application logs

## 🛠️ Troubleshooting

### Common Issues

1. **OAuth Token Expired**
   ```bash
   rm tokens.json
   # Re-run the bot to re-authenticate
   ```

2. **League/Team ID Issues**
   - Verify IDs in Yahoo Fantasy URLs
   - Check config.yaml

3. **API Rate Limits**
   - Bot includes built-in rate limiting
   - Wait 1 second between requests

### Support
- Check logs for error messages
- Verify Yahoo API credentials
- Ensure league is active and accessible

## 💰 Cost Comparison

| Option | Cost | Setup Time | Reliability | Control |
|--------|------|------------|-------------|---------|
| GitHub Actions | Free | 10 min | Medium | Low |
| Local Mac | Free | 5 min | Low | High |
| Heroku | $7-25/mo | 15 min | High | Medium |
| DigitalOcean | $5-10/mo | 30 min | High | High |
| AWS EC2 | $3-15/mo | 45 min | High | High |

## 🎯 Recommendation

**Start with GitHub Actions** - it's free, easy to set up, and perfect for weekly fantasy football optimization. You can always upgrade to a paid service later if you need more frequent runs or better reliability.

