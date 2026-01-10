# Arbitrage Hunter 🎯 - Prolonged Coordination System

**Real-time arbitrage detection agent with multi-day position tracking, state persistence, and adaptive strategies.**

## 🚀 Key Features

### Prolonged Coordination System

This agent is designed to run **continuously for days/weeks**, with complete state persistence in MongoDB. The system can crash and resume seamlessly, tracking positions over extended periods until markets resolve.

#### 1. **Multi-Day Position Tracking**
- Creates positions when arbitrage opportunities are detected
- Tracks entry prices, bet amounts, target profit, and expiration dates
- Monitors positions daily until market resolution
- Position states: `watching` → `entered` → `expired`/`profitable`/`loss`

#### 2. **Failure Recovery & State Persistence**
- **MongoDB stores complete context** - agent can crash and resume seamlessly
- `task_log` collection tracks all actions with timestamps
- On restart, agent reads state and resumes monitoring positions
- Simulated API failures (10% chance) with exponential backoff retry logic
- Recovery events are logged and displayed on dashboard

#### 3. **Adaptive Strategy Over Time**
- Tracks performance by market type (Sports, Politics, Crypto, Tech, Economic)
- Stores `market_type_performance` metrics in MongoDB
- Agent adapts polling frequency based on historical success rates
- Strategy Evolution chart shows which market types perform best
- Automatically polls successful market types more frequently

#### 4. **Multi-Step Workflow**
Each opportunity goes through a resumable workflow:

1. **Step 1: Detect** → Store opportunity in MongoDB
2. **Step 2: Place Orders** → Simulate order placement, update position state
3. **Step 3: Monitor** → Daily monitoring until market resolves
4. **Step 4: Resolve** → Calculate actual profit, update performance metrics

All steps are logged and can be resumed if the agent crashes.

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/arbitrage_hunter?retryWrites=true&w=majority
DATABASE_NAME=arbitrage_hunter
POLYMARKET_API_URL=https://clob.polymarket.com
KALSHI_API_URL=https://api.kalshi.com/trade-api/v2
KALSHI_API_KEY=your_key_here
KALSHI_API_SECRET=your_secret_here  # Or store RSA key in kalshi_rsa_key.pem
```

### 3. Generate Demo Data

```bash
python3 generate_dummy_data.py
```

### 4. Start the Agent

```bash
python3 agent.py
```

The agent will:
- Resume from MongoDB state if restarting
- Fetch prices with retry logic (handles API failures)
- Detect arbitrage and create positions
- Monitor positions daily
- Adapt strategy based on performance

### 5. View Dashboard

```bash
python3 app.py
```

Open http://localhost:5000

## Dashboard Features

### Stat Cards
- **Active Opportunities**: Current arbitrage opportunities
- **Found in Last 24h**: Total opportunities detected today
- **Avg Profit %**: Average profit across opportunities
- **Top Profit %**: Best opportunity profit percentage
- **Total Profit Captured**: Cumulative profit if all historical positions were taken
- **Recovery Events**: Number of times agent successfully resumed after crashes

### Agent Status Section
- **Agent Uptime**: Days and hours the agent has been running
- **Positions Tracked**: Total positions created over time
- **State Persistence**: MongoDB connection status

### Strategy Evolution Chart
- Bar chart showing success rates by market type
- Average profit % by category
- Agent uses this data to adjust polling frequency

### Active Positions Table
- Multi-day position tracking
- Shows position state (watching/entered/expired)
- Days held and days until expiration
- Target profit amounts

### Task History Log
- All agent actions with timestamps
- Success/failure status
- Error details for debugging
- Recovery events tracked

### Profit Chart
- 24-hour profit % trend
- Updates every 30 seconds

## MongoDB Collections

1. **market_prices** - All price snapshots with timestamps
2. **arbitrage_opportunities** - Detected arbitrage opportunities
3. **positions** - Multi-day position tracking (NEW)
   - Entry prices, bet amounts, target profit
   - State machine: watching → entered → expired/profitable/loss
   - Days held, expiration dates
4. **task_log** - Action log for state persistence (NEW)
   - Timestamp, action, status, error details
   - Enables crash recovery
5. **market_type_performance** - Adaptive strategy data (NEW)
   - Performance metrics by market type
   - Success rates, average profits
   - Used for adaptive polling

## How Prolonged Coordination Works

### State Persistence
- All state stored in MongoDB (positions, tasks, performance)
- Agent can be stopped and restarted without losing context
- On restart, agent:
  1. Reads active positions from MongoDB
  2. Checks task_log for last actions
  3. Resumes monitoring from where it left off
  4. Updates performance metrics

### Multi-Day Monitoring
- Positions are created when opportunities are detected
- Agent monitors positions daily (checks expiration, updates state)
- Positions transition through states automatically
- When markets expire, actual profit is calculated and stored

### Adaptive Strategy
- Agent tracks which market types have better arbitrage rates
- Calculates success rates: `profitable_arbs / opportunities_found`
- Adjusts polling frequency:
  - High success rate (>50%): Poll 2x more frequently
  - Medium (30-50%): Normal frequency
  - Low (<30%): Poll less frequently
- Strategy Evolution chart visualizes performance

### Failure Recovery
- 10% simulated API failure rate (configurable)
- Exponential backoff retry: 1s, 2s, 4s, 8s, 16s
- All failures logged to task_log
- Agent continues with other operations if one API fails
- Recovery events tracked and displayed

## Example Workflow

1. **Agent detects arbitrage** → Creates opportunity in MongoDB
2. **Position created** → State: "watching", expiration: 45 days
3. **Order placement simulated** → State: "entered"
4. **Daily monitoring** → Checks if expired, updates days_held
5. **Market expires** → State: "expired", actual_profit calculated
6. **Performance updated** → Market type metrics recalculated
7. **Strategy adapts** → Polling frequency adjusted based on success

If agent crashes at any step, it resumes from MongoDB state on restart.

## Testing

```bash
# Test setup
python3 test_setup.py

# Test with dummy data
python3 agent.py --dummy

# View dashboard
python3 app.py
```

## Project Structure

```
arbitrage_hunter/
├── agent.py              # Main agent with prolonged coordination
├── app.py                # Dashboard with all new sections
├── position_manager.py   # Multi-day position tracking (NEW)
├── arbitrage.py          # Arbitrage detection logic
├── config.py             # MongoDB & API configuration
├── kalshi.py             # Kalshi API client
├── models.py             # MongoDB document models (updated)
├── polymarket.py         # Polymarket API client
├── generate_dummy_data.py # Demo data generator (2026-2028 markets)
├── test_setup.py         # Setup verification
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Key Improvements Over Simple Agent

✅ **State Persistence**: Survives crashes, resumes seamlessly  
✅ **Multi-Day Tracking**: Monitors positions over weeks  
✅ **Adaptive Strategy**: Learns and optimizes over time  
✅ **Failure Recovery**: Handles API failures gracefully  
✅ **Complete Workflow**: Multi-step process with checkpoints  
✅ **Performance Analytics**: Tracks which strategies work best  

## Demo Highlights

- **"This agent runs continuously for days/weeks"**
- **"MongoDB stores complete context - agent can crash and resume seamlessly"**
- **"Agent learns which market types are most profitable and adapts strategy"**
- **"All positions are tracked until market resolution"**
- **"Recovery events show robust error handling"**

## Next Steps

- [ ] Add email/Slack notifications for high-value opportunities
- [ ] Implement actual order placement APIs
- [ ] Add more platforms (Augur, etc.)
- [ ] Historical backtesting analysis
- [ ] Machine learning for market type prediction

---

**Built for hackathon - Prolonged Coordination System** 🚀
