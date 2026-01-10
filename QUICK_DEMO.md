# 🚀 Quick Demo - 30 Second Start

## Start the Demo (Choose One)

### Option 1: One Command
```bash
./start_demo.sh
```

### Option 2: Two Commands
```bash
python3 generate_dummy_data.py && python3 app.py
```

## Then...

**Open your browser to: http://localhost:5000**

That's it! 🎉

## What You'll See

- **4 Stat Cards**: Active opportunities, 24h total, avg profit, top profit
- **Arbitrage Table**: All opportunities with profit calculations
- **Market Prices Table**: Recent price snapshots
- **Auto-refresh**: Updates every 30 seconds

## Demo Talking Points

1. "This is a real-time arbitrage detection system"
2. "It monitors Polymarket and Kalshi for price discrepancies"
3. "When probabilities add up to less than 100%, we guarantee profit"
4. "Example: 45% + 52% = 97%, giving us 3% guaranteed return"
5. "The system runs continuously, detecting new opportunities every 60 seconds"

## If You Need Fresh Data

```bash
python3 generate_dummy_data.py
# Refresh browser
```

## Troubleshooting

**Port 5000 in use?**
```bash
lsof -ti:5000 | xargs kill -9
python3 app.py
```

**No data showing?**
```bash
python3 generate_dummy_data.py
```

---

**You're all set! Good luck with your demo! 🎯**

