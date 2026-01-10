# Prolonged Coordination System - Technical Overview

## Architecture

### State Persistence
- **Complete state in MongoDB**: All positions, tasks, and performance metrics
- **Crash-resistant**: Agent can stop and resume without losing context
- **Resume mechanism**: On startup, agent reads MongoDB and continues from last state

### Multi-Day Position Lifecycle

```
Opportunity Detected
    ↓
Position Created (state: "watching")
    ↓
Orders Placed (state: "entered")  [Simulated Step 2]
    ↓
Daily Monitoring (updates days_held)
    ↓
Market Expires
    ↓
State: "expired" + Actual Profit Calculated
    ↓
Performance Metrics Updated
```

### Failure Recovery Flow

1. **API Failure Detected** (10% simulated rate)
2. **Exponential Backoff**: Wait 1s, 2s, 4s, 8s, 16s
3. **Retry up to 5 times**
4. **Log failure to task_log**
5. **Continue with other operations**
6. **Recovery event counted**

### Adaptive Strategy Algorithm

```python
For each market type:
    success_rate = profitable_arbs / opportunities_found
    
    if success_rate > 50%:
        poll_interval = base_interval / 2  # Poll more often
    elif success_rate > 30%:
        poll_interval = base_interval      # Normal
    else:
        poll_interval = base_interval * 2  # Poll less often
```

### Multi-Step Workflow

**Step 1: Detect**
- Agent finds arbitrage opportunity
- Stores in `arbitrage_opportunities` collection
- Creates position in `positions` collection
- Logs to `task_log`

**Step 2: Place Orders** (Simulated)
- After detection, simulates order placement
- Updates position state: `watching` → `entered`
- Logs action to `task_log`

**Step 3: Monitor** (Daily)
- Runs every iteration
- Checks position expiration dates
- Updates `days_held` counter
- Updates `last_checked` timestamp

**Step 4: Resolve**
- When market expires, calculates actual profit
- Updates position state: `entered` → `expired`
- Updates `market_type_performance` metrics
- Logs resolution to `task_log`

## Database Schema

### positions Collection
```javascript
{
  position_id: "uuid",
  event_name: "Will Bitcoin reach $150k by end of 2026?",
  platform_a: "polymarket",
  platform_b: "kalshi",
  amount_bet_a: 45.00,
  amount_bet_b: 52.00,
  entry_price_a: 0.45,
  entry_price_b: 0.52,
  target_profit: 3.09,
  expiration_date: ISODate("2026-12-31"),
  market_type: "Crypto",
  state: "entered",  // watching | entered | expired | profitable | loss
  days_held: 15,
  created_at: ISODate("2026-01-01"),
  last_checked: ISODate("2026-01-16"),
  actual_profit: null,
  resolved_at: null
}
```

### task_log Collection
```javascript
{
  task_id: "uuid",
  action: "detect_arbitrage",  // detect | place_order | monitor | resolve | recover
  status: "success",  // success | failure | retry
  details: "Found 5 opportunities, created 3 positions",
  error: null,
  timestamp: ISODate("2026-01-10T22:00:00Z")
}
```

### market_type_performance Collection
```javascript
{
  _id: "Crypto",
  market_type: "Crypto",
  opportunities_found: 45,
  profitable_arbs: 32,
  avg_profit_pct: 3.2,
  success_rate: 71.1,
  last_updated: ISODate("2026-01-10T22:00:00Z")
}
```

## Recovery Scenarios

### Scenario 1: API Failure During Fetch
```
1. Agent tries to fetch Polymarket data
2. API fails (simulated 10% chance)
3. Exponential backoff: wait 1s, retry
4. Still fails, wait 2s, retry
5. Succeeds on 3rd attempt
6. Task logged: "fetch_data", "retry", "Polymarket API failed, retrying"
7. Agent continues normally
```

### Scenario 2: Agent Crash During Monitoring
```
1. Agent is monitoring 5 active positions
2. System crashes
3. On restart:
   - Reads 5 positions from MongoDB
   - Checks task_log for last action
   - Resumes monitoring from where it left off
   - Logs: "recover", "success", "Resuming from MongoDB state"
4. No data loss, seamless continuation
```

### Scenario 3: Position Expires While Agent Down
```
1. Position expires on Jan 15
2. Agent crashes on Jan 10
3. Agent restarts on Jan 20
4. On restart:
   - Reads expired position from MongoDB
   - Checks expiration_date < now
   - Updates state to "expired"
   - Calculates actual profit
   - Updates performance metrics
5. Position properly resolved despite downtime
```

## Performance Optimization

### Adaptive Polling
- **Successful market types**: Polled more frequently (every 30s)
- **Average market types**: Normal frequency (every 60s)
- **Poor market types**: Polled less frequently (every 120s)
- Reduces unnecessary API calls while focusing on profitable areas

### Index Strategy
- Positions indexed on `(state, last_checked)` for fast active queries
- Positions indexed on `expiration_date` for efficient expiration checks
- Task log indexed on `timestamp` for chronological retrieval
- Market performance indexed on `market_type` for fast lookups

## Monitoring & Observability

### Dashboard Metrics
- **Recovery Events**: Tracks resilience
- **Agent Uptime**: Shows system stability
- **Positions Tracked**: Total positions created
- **Task History**: Complete audit trail
- **Strategy Evolution**: Visualizes adaptation

### Task Log Analysis
- All actions timestamped
- Success/failure rates trackable
- Error patterns identifiable
- Recovery events measurable

## Demo Scenarios

### Show State Persistence
1. Start agent: `python3 agent.py`
2. Let it run for a few iterations
3. Stop agent (Ctrl+C)
4. Restart agent
5. **Show**: Agent resumes, reads positions from MongoDB, continues monitoring

### Show Failure Recovery
1. Agent will randomly fail API calls (10% chance)
2. **Show**: Retry logic, exponential backoff
3. **Show**: Task log entries for retries
4. **Show**: Agent continues despite failures

### Show Adaptive Strategy
1. Run agent long enough to generate performance data
2. **Show**: Strategy Evolution chart
3. **Show**: Different polling frequencies
4. **Show**: Agent focusing on profitable market types

### Show Multi-Day Tracking
1. Create positions with future expiration dates
2. **Show**: Positions table with days_held increasing
3. **Show**: Daily monitoring updates
4. **Show**: Position states transitioning

---

**This system is designed for production-grade reliability and long-term operation.** 🎯

