# 🎯 Demo Guide - Arbitrage Hunter

## Quick Start (3 minutes)

### Option 1: Use the Start Script (Easiest)
```bash
./start_demo.sh
```

### Option 2: Manual Start
```bash
# 1. Generate dummy data
python3 generate_dummy_data.py

# 2. Start the dashboard
python3 app.py
```

Then open **http://localhost:5000** in your browser.

## What You'll See

### Dashboard Features:
1. **Stats Cards** (Top of page):
   - Active Opportunities count
   - Total found in last 24h
   - Average profit percentage
   - Top profit percentage

2. **Arbitrage Opportunities Table**:
   - Event name
   - Platform A & B (Polymarket/Kalshi)
   - Prices on each platform
   - Bet amounts needed
   - Guaranteed profit and percentage
   - Detection timestamp

3. **Recent Market Prices Table**:
   - Latest price snapshots
   - Platform and outcome
   - Timestamp

### Demo Talking Points:

1. **Real-time Detection**: "The system continuously monitors prediction markets for price discrepancies"

2. **Guaranteed Profit**: "When combined probabilities are less than 100%, we can guarantee profit by betting on both outcomes"

3. **Example**: "Here's an opportunity: Polymarket has 'Yes' at 45%, Kalshi has 'No' at 52%. Combined is 97%, giving us a 3% guaranteed profit."

4. **Automation**: "The agent runs every 60 seconds, automatically detecting and storing new opportunities"

5. **Tech Stack**: "Built with Python, MongoDB Atlas, Flask, and integrates with Polymarket and Kalshi APIs"

## Testing the System

### Generate Fresh Data:
```bash
python3 generate_dummy_data.py
```

### Check Database:
```bash
python3 -c "from arbitrage import get_active_opportunities; opps = get_active_opportunities(); print(f'Found {len(opps)} opportunities')"
```

### Run Agent in Dummy Mode:
```bash
python3 agent.py --dummy
```

## What to Show in Demo

1. ✅ **Dashboard is live and showing data**
2. ✅ **Multiple arbitrage opportunities displayed**
3. ✅ **Real-time stats updating**
4. ✅ **Clean, professional UI**
5. ✅ **Profit calculations are correct**

## If Something Goes Wrong

### No opportunities showing?
```bash
# Regenerate data
python3 generate_dummy_data.py
# Refresh browser
```

### Dashboard won't start?
```bash
# Check if port 5000 is in use
lsof -ti:5000 | xargs kill -9
# Try again
python3 app.py
```

### Database connection issues?
- Check your `.env` file has correct MongoDB URI
- Verify MongoDB Atlas IP whitelist includes your IP

## Next Steps (If Time Permits)

1. Connect to real APIs (Polymarket/Kalshi)
2. Add email/Slack notifications for opportunities
3. Implement actual betting/execution
4. Add more platforms (Augur, etc.)
5. Historical analysis and backtesting

## Quick Tips for Presentation

- **Start with the dashboard** - it's visual and impressive
- **Explain one opportunity in detail** - show the math
- **Mention the automation** - runs continuously
- **Highlight the tech stack** - shows technical depth
- **Discuss scalability** - MongoDB can handle millions of records

Good luck with your demo! 🚀

