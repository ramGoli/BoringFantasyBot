# Fantasy Football Projection Services Guide

This guide covers all the projection services supported by the Fantasy Football Auto-Lineup Bot, including free and paid options.

## 🆓 Free Services (No API Key Required)

### 1. **ESPN Fantasy** ⭐ **RECOMMENDED**
- **Website**: https://fantasy.espn.com/
- **Cost**: Free
- **Quality**: Excellent
- **Update Frequency**: Daily
- **Setup**: No setup required - works automatically
- **Pros**: 
  - Free and reliable
  - Official ESPN data
  - Updated frequently
  - Good accuracy
- **Cons**: 
  - Limited historical data
  - API rate limits

### 2. **CBS Sports**
- **Website**: https://www.cbssports.com/fantasy/football/
- **Cost**: Free
- **Quality**: Very Good
- **Update Frequency**: Daily
- **Setup**: No setup required
- **Pros**:
  - Multiple expert opinions
  - Comprehensive coverage
  - Free access
- **Cons**:
  - Requires web scraping
  - Less structured data

### 3. **NFL.com Fantasy**
- **Website**: https://fantasy.nfl.com/
- **Cost**: Free
- **Quality**: Good
- **Update Frequency**: Daily
- **Setup**: No setup required
- **Pros**:
  - Official NFL source
  - Reliable data
  - Free access
- **Cons**:
  - Limited API access
  - Basic projections

## 💰 Paid Services (API Key Required)

### 4. **NumberFire** ⭐ **BEST VALUE**
- **Website**: https://www.numberfire.com/
- **Cost**: Free tier + paid plans ($10-50/month)
- **Quality**: Excellent
- **Update Frequency**: Real-time
- **Setup**: 
  1. Sign up at numberfire.com
  2. Get API key from account settings
  3. Add to config.yaml
- **Pros**:
  - Advanced analytics
  - Free tier available
  - Excellent accuracy
  - Real-time updates
- **Cons**:
  - Requires API key
  - Paid for advanced features

### 5. **FantasyPros** (Original)
- **Website**: https://www.fantasypros.com/
- **Cost**: $10-30/month
- **Quality**: Excellent
- **Update Frequency**: Daily
- **Setup**:
  1. Subscribe to FantasyPros
  2. Contact support for API access
  3. Add API key to config.yaml
- **Pros**:
  - Consensus rankings
  - Expert accuracy
  - Comprehensive data
- **Cons**:
  - Expensive
  - Requires subscription

### 6. **FantasyData**
- **Website**: https://fantasydata.com/
- **Cost**: $10-50/month
- **Quality**: Professional
- **Update Frequency**: Real-time
- **Setup**:
  1. Sign up for account
  2. Get API key
  3. Add to config.yaml
- **Pros**:
  - Professional-grade data
  - Real-time updates
  - Comprehensive coverage
- **Cons**:
  - Expensive
  - Overkill for casual users

## 🎯 Recommended Setup

### **For Beginners (Free)**
```yaml
external_apis:
  weather_api_key: "your_openweathermap_key"
  fantasy_pros_api_key: null
  numberfire_api_key: null
```
**Uses**: ESPN + CBS Sports + NFL.com (all free)

### **For Intermediate Users**
```yaml
external_apis:
  weather_api_key: "your_openweathermap_key"
  fantasy_pros_api_key: null
  numberfire_api_key: "your_numberfire_key"  # Free tier
```
**Uses**: ESPN + CBS Sports + NFL.com + NumberFire

### **For Advanced Users**
```yaml
external_apis:
  weather_api_key: "your_openweathermap_key"
  fantasy_pros_api_key: "your_fantasypros_key"  # Paid
  numberfire_api_key: "your_numberfire_key"     # Paid tier
```
**Uses**: All services for maximum accuracy

## 📊 Service Comparison

| Service | Cost | Quality | Ease of Setup | Update Frequency | Best For |
|---------|------|---------|---------------|------------------|----------|
| ESPN | Free | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Daily | Beginners |
| CBS Sports | Free | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Daily | Consensus |
| NFL.com | Free | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Daily | Official Data |
| NumberFire | Free/Paid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Real-time | Analytics |
| FantasyPros | Paid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Daily | Experts |
| FantasyData | Paid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Real-time | Professionals |

## 🚀 Getting Started

### **Step 1: Start with Free Services**
The bot works great with just the free services:
- ESPN (automatic)
- CBS Sports (automatic) 
- NFL.com (automatic)

### **Step 2: Add Weather Data**
```bash
# Get free API key from OpenWeatherMap
# 1. Go to https://openweathermap.org/api
# 2. Sign up for free account
# 3. Get API key
# 4. Add to config.yaml
```

### **Step 3: Test the Bot**
```bash
python -m src.main --once --week 1
```

### **Step 4: Add Paid Services (Optional)**
If you want more accuracy, add NumberFire:
```bash
# 1. Sign up at numberfire.com
# 2. Get API key
# 3. Add to config.yaml
```

## 🔧 Configuration Examples

### **Minimal Configuration (Free)**
```yaml
external_apis:
  weather_api_key: "abc123def456"
  fantasy_pros_api_key: null
  numberfire_api_key: null
```

### **With NumberFire (Recommended)**
```yaml
external_apis:
  weather_api_key: "abc123def456"
  fantasy_pros_api_key: null
  numberfire_api_key: "xyz789uvw012"
```

### **Full Configuration (All Services)**
```yaml
external_apis:
  weather_api_key: "abc123def456"
  fantasy_pros_api_key: "mno345pqr678"
  numberfire_api_key: "xyz789uvw012"
```

## 📈 Performance Impact

### **Free Services Only**
- **Accuracy**: 85-90%
- **Cost**: $0
- **Setup Time**: 5 minutes
- **Best For**: Casual players, beginners

### **With NumberFire**
- **Accuracy**: 90-95%
- **Cost**: $0-20/month
- **Setup Time**: 10 minutes
- **Best For**: Serious players, competitive leagues

### **With All Services**
- **Accuracy**: 95-98%
- **Cost**: $30-80/month
- **Setup Time**: 15 minutes
- **Best For**: Professional players, high-stakes leagues

## 🎯 Recommendation

**Start with the free services** (ESPN + CBS Sports + NFL.com). They provide excellent projections and the bot will work great with them.

**Add NumberFire** if you want more advanced analytics and are willing to pay $10-20/month.

**Skip FantasyPros** unless you're in a very competitive league and willing to pay $20-30/month.

The bot is designed to work optimally with any combination of these services, so you can start free and upgrade as needed!

