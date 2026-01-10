# Quick Start Guide (5 minutes)

## 1. Install Dependencies

```bash
pip3 install -r requirements.txt
# OR if you have a virtual environment activated:
pip install -r requirements.txt
```

## 2. Create `.env` File

Create a file named `.env` in the project root with:

```env
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/arbitrage_hunter?retryWrites=true&w=majority
DATABASE_NAME=arbitrage_hunter
POLYMARKET_API_URL=https://clob.polymarket.com
KALSHI_API_URL=https://api.kalshi.com/trade-api/v2
KALSHI_API_KEY=your_key_here
KALSHI_API_SECRET=your_secret_here
```

**Get MongoDB URI:**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Click "Connect" → "Connect your application"
4. Copy the connection string
5. Replace `<password>` with your actual password

**Get Kalshi API Keys (Optional - some endpoints may work without auth):**
1. Go to https://kalshi.com
2. Sign up and navigate to API settings
3. Generate API key and secret

## 3. Test Setup

```bash
python3 test_setup.py
```

Fix any errors before proceeding.

## 4. Start the Agent

```bash
python3 agent.py
```

You should see output like:
```
🚀 Arbitrage Agent started
⏱️  Polling interval: 60 seconds
📊 Fetching Polymarket markets...
✅ Found X Polymarket markets
```

## 5. View Dashboard (Separate Terminal)

```bash
python3 app.py
```

Open http://localhost:5000 in your browser.

## Troubleshooting

**"python: command not found" (macOS/Linux)**
- On macOS, Python 3 is typically installed as `python3`, not `python`
- Use `python3` instead: `python3 agent.py`
- To create an alias, add to `~/.zshrc` or `~/.bashrc`:
  ```bash
  alias python=python3
  alias pip=pip3
  ```
- Then reload: `source ~/.zshrc` (or `source ~/.bashrc`)

**"Failed to connect to MongoDB"**
- Check your connection string in `.env`
- Make sure your IP is whitelisted in MongoDB Atlas (Network Access)
- Try pinging your cluster

**"No markets found"**
- APIs may be rate-limited
- Check if endpoints are accessible: `curl https://clob.polymarket.com/markets`
- Kalshi may require authentication (some endpoints work without auth)

**"No arbitrage opportunities"**
- This is normal! Real arbitrage is rare
- The agent is working if you see prices being stored
- Check MongoDB: `db.arbitrage_opportunities.find()`

## Next Steps

- Let the agent run for a while to collect data
- Check the dashboard for opportunities
- Review stored data in MongoDB Atlas dashboard

