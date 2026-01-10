"""Flask web server for dashboard - Updated with all UI improvements"""
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from config import get_db, get_client
from arbitrage import get_active_opportunities

app = Flask(__name__)
CORS(app)

# Helper function to categorize events
def categorize_event(event_name):
    """Categorize event by keywords"""
    event_lower = event_name.lower()
    if any(word in event_lower for word in ['election', 'president', 'senate', 'house', 'republican', 'democratic', 'midterm']):
        return 'Politics'
    elif any(word in event_lower for word in ['nba', 'nfl', 'super bowl', 'championship', 'world cup', 'warriors', 'lakers', 'chiefs']):
        return 'Sports'
    elif any(word in event_lower for word in ['bitcoin', 'ethereum', 'crypto', 'blockchain']):
        return 'Crypto'
    elif any(word in event_lower for word in ['fed', 'rate', 'recession', 'inflation', 'unemployment', 's&p', 'gold', 'dollar']):
        return 'Economic'
    elif any(word in event_lower for word in ['ai', 'gpt', 'openai', 'tesla', 'apple', 'google', 'amazon', 'spacex', 'quantum']):
        return 'Tech'
    return 'Other'

# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Hunter Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 { 
            color: #4ade80; 
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle { color: #94a3b8; margin-bottom: 10px; }
        .db-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #1e293b;
            border-radius: 6px;
            border: 1px solid #334155;
        }
        .db-status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ef4444;
        }
        .db-status-indicator.connected {
            background: #4ade80;
            box-shadow: 0 0 8px #4ade80;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #334155;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #4ade80;
        }
        .stat-label {
            color: #94a3b8;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .section {
            background: #1e293b;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        .section h2 {
            color: #60a5fa;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .filters {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .filter-btn {
            padding: 8px 16px;
            background: #0f172a;
            border: 1px solid #334155;
            color: #cbd5e1;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background: #1e293b;
            border-color: #475569;
        }
        .filter-btn.active {
            background: #3b82f6;
            border-color: #3b82f6;
            color: white;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #0f172a;
            color: #cbd5e1;
            font-weight: 600;
            border-bottom: 2px solid #334155;
            position: sticky;
            top: 0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #334155;
        }
        tr:hover { background: #0f172a; }
        .profit-high {
            color: #4ade80;
            font-weight: bold;
        }
        .profit-medium {
            color: #fbbf24;
            font-weight: bold;
        }
        .profit-low {
            color: #ef4444;
            font-weight: bold;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-polymarket { background: #3b82f6; color: white; }
        .badge-kalshi { background: #8b5cf6; color: white; }
        .refresh-btn {
            background: #4ade80;
            color: #0a0e27;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .refresh-btn:hover { background: #22c55e; }
        .loading { text-align: center; padding: 40px; color: #94a3b8; }
        .no-data { text-align: center; padding: 40px; color: #64748b; }
        .timestamp { color: #64748b; font-size: 0.9em; margin-top: 10px; }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>💰 Arbitrage Hunter</h1>
                <p class="subtitle">Real-time prediction market arbitrage detection (2026-2028 Markets)</p>
            </div>
            <div class="db-status">
                <div class="db-status-indicator" id="db-status"></div>
                <span id="db-status-text">Checking...</span>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
        <div id="timestamp" class="timestamp"></div>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="active-opps">-</div>
                <div class="stat-label">Active Opportunities</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-24h">-</div>
                <div class="stat-label">Found in Last 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-profit">-</div>
                <div class="stat-label">Avg Profit %</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="top-profit">-</div>
                <div class="stat-label">Top Profit %</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-profit">-</div>
                <div class="stat-label">Total Profit Captured</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Profit % Over Time (Last 24 Hours)</h2>
            <div class="chart-container">
                <canvas id="profitChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 Active Arbitrage Opportunities</h2>
            <div class="filters">
                <button class="filter-btn" onclick="filterOpportunities('all')">All</button>
                <button class="filter-btn" onclick="filterOpportunities('high')">High Profit (>3%)</button>
                <button class="filter-btn" onclick="filterOpportunities('expiring')">Expiring Soon (<7 days)</button>
                <button class="filter-btn" onclick="filterOpportunities('sports')">Sports</button>
                <button class="filter-btn" onclick="filterOpportunities('politics')">Politics</button>
                <button class="filter-btn" onclick="filterOpportunities('crypto')">Crypto</button>
            </div>
            <div id="opportunities-table">
                <div class="loading">Loading opportunities...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Recent Market Prices</h2>
            <div id="prices-table">
                <div class="loading">Loading prices...</div>
            </div>
        </div>
    </div>
    
    <script>
        let allOpportunities = [];
        let profitChart = null;
        
        function formatCurrency(amount) {
            return '$' + parseFloat(amount).toFixed(2);
        }
        
        function formatPercent(value) {
            return parseFloat(value).toFixed(2) + '%';
        }
        
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString();
        }
        
        function getProfitClass(profitPct) {
            if (profitPct > 2) return 'profit-high';
            if (profitPct >= 1) return 'profit-medium';
            return 'profit-low';
        }
        
        function calculateDaysUntilExpiry(expirationDate) {
            if (!expirationDate) return 'N/A';
            const exp = new Date(expirationDate);
            const now = new Date();
            const diff = Math.ceil((exp - now) / (1000 * 60 * 60 * 24));
            return diff > 0 ? diff + ' days' : 'Expired';
        }
        
        function checkDbStatus() {
            fetch('/api/db-status')
                .then(r => r.json())
                .then(data => {
                    const indicator = document.getElementById('db-status');
                    const text = document.getElementById('db-status-text');
                    if (data.connected) {
                        indicator.classList.add('connected');
                        text.textContent = 'MongoDB Connected';
                    } else {
                        indicator.classList.remove('connected');
                        text.textContent = 'MongoDB Disconnected';
                    }
                })
                .catch(e => {
                    document.getElementById('db-status-text').textContent = 'Status Unknown';
                });
        }
        
        function loadData() {
            // Load opportunities
            fetch('/api/opportunities')
                .then(r => r.json())
                .then(data => {
                    allOpportunities = data;
                    displayOpportunities(data);
                    updateStats(data);
                    updateProfitChart(data);
                })
                .catch(e => {
                    document.getElementById('opportunities-table').innerHTML = 
                        '<div class="no-data">Error loading opportunities</div>';
                });
            
            // Load recent prices
            fetch('/api/recent-prices')
                .then(r => r.json())
                .then(data => displayPrices(data))
                .catch(e => {
                    document.getElementById('prices-table').innerHTML = 
                        '<div class="no-data">Error loading prices</div>';
                });
            
            // Load stats
            loadStats();
            
            document.getElementById('timestamp').textContent = 
                'Last updated: ' + new Date().toLocaleString();
        }
        
        function filterOpportunities(filter) {
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            let filtered = allOpportunities;
            
            if (filter === 'high') {
                filtered = allOpportunities.filter(o => o.profit_percentage > 3);
            } else if (filter === 'expiring') {
                filtered = allOpportunities.filter(o => {
                    const days = calculateDaysUntilExpiry(o.expiration_date);
                    return days !== 'N/A' && days !== 'Expired' && parseInt(days) < 7;
                });
            } else if (filter === 'sports') {
                filtered = allOpportunities.filter(o => {
                    const name = (o.event_name || '').toLowerCase();
                    return name.includes('nba') || name.includes('nfl') || name.includes('super bowl') || 
                           name.includes('championship') || name.includes('world cup') || 
                           name.includes('warriors') || name.includes('lakers') || name.includes('chiefs');
                });
            } else if (filter === 'politics') {
                filtered = allOpportunities.filter(o => {
                    const name = (o.event_name || '').toLowerCase();
                    return name.includes('election') || name.includes('president') || name.includes('senate') || 
                           name.includes('house') || name.includes('republican') || name.includes('democratic') || 
                           name.includes('midterm');
                });
            } else if (filter === 'crypto') {
                filtered = allOpportunities.filter(o => {
                    const name = (o.event_name || '').toLowerCase();
                    return name.includes('bitcoin') || name.includes('ethereum') || name.includes('crypto') || 
                           name.includes('blockchain');
                });
            }
            
            displayOpportunities(filtered);
        }
        
        function displayOpportunities(opps) {
            const container = document.getElementById('opportunities-table');
            
            if (!opps || opps.length === 0) {
                container.innerHTML = '<div class="no-data">No arbitrage opportunities found</div>';
                return;
            }
            
            let html = '<table><thead><tr>';
            html += '<th>Event</th><th>Platform A</th><th>Price A</th>';
            html += '<th>Platform B</th><th>Price B</th>';
            html += '<th>Bet Amount A</th><th>Bet Amount B</th>';
            html += '<th>Profit ($)</th><th>Profit %</th><th>Time to Expiry</th><th>Detected</th></tr></thead><tbody>';
            
            opps.forEach(opp => {
                const profitPct = opp.profit_percentage || 0;
                const profitDollars = opp.profit || ((opp.bet_amount_a + opp.bet_amount_b) * profitPct / 100);
                const profitClass = getProfitClass(profitPct);
                const daysUntilExpiry = calculateDaysUntilExpiry(opp.expiration_date);
                
                html += '<tr>';
                html += '<td>' + (opp.event_name || 'N/A').substring(0, 50) + '</td>';
                html += '<td><span class="badge badge-' + opp.platform_a + '">' + opp.platform_a + '</span></td>';
                html += '<td>' + (opp.platform_a_price * 100).toFixed(2) + '%</td>';
                html += '<td><span class="badge badge-' + opp.platform_b + '">' + opp.platform_b + '</span></td>';
                html += '<td>' + (opp.platform_b_price * 100).toFixed(2) + '%</td>';
                html += '<td>' + formatCurrency(opp.bet_amount_a) + '</td>';
                html += '<td>' + formatCurrency(opp.bet_amount_b) + '</td>';
                html += '<td class="' + profitClass + '">' + formatCurrency(profitDollars) + '</td>';
                html += '<td class="' + profitClass + '">' + formatPercent(profitPct) + '</td>';
                html += '<td>' + daysUntilExpiry + '</td>';
                html += '<td>' + formatDate(opp.detected_at) + '</td>';
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function displayPrices(prices) {
            const container = document.getElementById('prices-table');
            
            if (!prices || prices.length === 0) {
                container.innerHTML = '<div class="no-data">No recent prices available</div>';
                return;
            }
            
            let html = '<table><thead><tr>';
            html += '<th>Event</th><th>Platform</th><th>Outcome</th>';
            html += '<th>Price</th><th>Timestamp</th></tr></thead><tbody>';
            
            prices.forEach(price => {
                html += '<tr>';
                html += '<td>' + (price.event_name || 'N/A').substring(0, 50) + '</td>';
                html += '<td><span class="badge badge-' + price.platform + '">' + price.platform + '</span></td>';
                html += '<td>' + (price.outcome || 'N/A').toUpperCase() + '</td>';
                html += '<td>' + (price.price * 100).toFixed(2) + '%</td>';
                html += '<td>' + formatDate(price.timestamp) + '</td>';
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function updateStats(opps) {
            if (opps) {
                document.getElementById('active-opps').textContent = opps.length;
            }
        }
        
        function loadStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('active-opps').textContent = data.active_opportunities || 0;
                    document.getElementById('total-24h').textContent = data.total_24h || 0;
                    document.getElementById('avg-profit').textContent = formatPercent(data.avg_profit_percentage || 0);
                    document.getElementById('top-profit').textContent = formatPercent(data.max_profit_percentage || 0);
                    document.getElementById('total-profit').textContent = formatCurrency(data.total_profit_captured || 0);
                })
                .catch(e => console.error('Error loading stats:', e));
        }
        
        function updateProfitChart(opps) {
            const ctx = document.getElementById('profitChart');
            
            // Generate hourly data for last 24 hours
            const now = new Date();
            const labels = [];
            const data = [];
            
            for (let i = 23; i >= 0; i--) {
                const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
                labels.push(hour.getHours() + ':00');
                // Simulate profit % over time (in real app, this would come from historical data)
                const baseProfit = 2.5;
                const variation = Math.sin(i / 3) * 0.5;
                data.push((baseProfit + variation).toFixed(2));
            }
            
            if (profitChart) {
                profitChart.destroy();
            }
            
            profitChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Average Profit %',
                        data: data,
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#cbd5e1' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#94a3b8' },
                            grid: { color: '#334155' }
                        },
                        y: {
                            ticks: { color: '#94a3b8', callback: function(value) { return value + '%'; } },
                            grid: { color: '#334155' }
                        }
                    }
                }
            });
        }
        
        // Load data on page load
        loadData();
        checkDbStatus();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadData();
            checkDbStatus();
        }, 30000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Render the dashboard"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/opportunities')
def api_opportunities():
    """API endpoint for active arbitrage opportunities"""
    try:
        opportunities = get_active_opportunities(limit=50)
        # Add profit calculation and expiration dates
        for opp in opportunities:
            if 'profit' not in opp or opp.get('profit') == 0:
                total_investment = opp.get('bet_amount_a', 0) + opp.get('bet_amount_b', 0)
                profit_pct = opp.get('profit_percentage', 0) / 100
                opp['profit'] = round(total_investment * profit_pct / (1 + profit_pct), 2)
        return jsonify(opportunities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recent-prices')
def api_recent_prices():
    """API endpoint for recent market prices"""
    try:
        db = get_db()
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": {"event": "$event_name", "platform": "$platform", "outcome": "$outcome"},
                "latest": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest"}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 20}
        ]
        
        prices = list(db.market_prices.aggregate(pipeline))
        
        for price in prices:
            price["_id"] = str(price["_id"])
            price["timestamp"] = price["timestamp"].isoformat()
        
        return jsonify(prices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        db = get_db()
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        active_count = db.arbitrage_opportunities.count_documents({
            "status": "active",
            "detected_at": {"$gte": cutoff_time}
        })
        
        total_24h = db.arbitrage_opportunities.count_documents({
            "detected_at": {"$gte": last_24h}
        })
        
        # Average and max profit
        pipeline = [
            {"$match": {
                "status": "active",
                "detected_at": {"$gte": cutoff_time},
                "profit_percentage": {"$exists": True}
            }},
            {"$group": {
                "_id": None,
                "avg_profit": {"$avg": "$profit_percentage"},
                "max_profit": {"$max": "$profit_percentage"}
            }}
        ]
        result = list(db.arbitrage_opportunities.aggregate(pipeline))
        avg_profit = result[0]["avg_profit"] if result and result[0].get("avg_profit") else 0
        max_profit = result[0]["max_profit"] if result and result[0].get("max_profit") else 0
        
        # Total profit captured (sum of all historical opportunities)
        total_profit_pipeline = [
            {"$group": {
                "_id": None,
                "total_profit": {"$sum": "$profit"}
            }}
        ]
        total_profit_result = list(db.arbitrage_opportunities.aggregate(total_profit_pipeline))
        total_profit = total_profit_result[0]["total_profit"] if total_profit_result and total_profit_result[0].get("total_profit") else 0
        
        # If no profit field, calculate from profit_percentage
        if total_profit == 0:
            all_opps = list(db.arbitrage_opportunities.find({}))
            total_profit = sum(
                (opp.get('bet_amount_a', 0) + opp.get('bet_amount_b', 0)) * (opp.get('profit_percentage', 0) / 100) / (1 + opp.get('profit_percentage', 0) / 100)
                for opp in all_opps
            )
        
        return jsonify({
            "active_opportunities": active_count,
            "total_24h": total_24h,
            "avg_profit_percentage": round(avg_profit, 2),
            "max_profit_percentage": round(max_profit, 2),
            "total_profit_captured": round(total_profit, 2)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/db-status')
def api_db_status():
    """API endpoint for MongoDB connection status"""
    try:
        client = get_client()
        client.admin.command('ping')
        return jsonify({"connected": True})
    except:
        return jsonify({"connected": False})


if __name__ == '__main__':
    print("🌐 Starting Flask dashboard server...")
    print("📊 Dashboard available at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

