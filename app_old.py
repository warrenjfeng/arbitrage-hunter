"""Flask web server for dashboard"""
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from config import get_db
from arbitrage import get_active_opportunities

app = Flask(__name__)
CORS(app)

# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Hunter Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { 
            color: #4ade80; 
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle { color: #94a3b8; margin-bottom: 30px; }
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
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #0f172a;
            color: #cbd5e1;
            font-weight: 600;
            border-bottom: 2px solid #334155;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #334155;
        }
        tr:hover { background: #0f172a; }
        .profit-positive {
            color: #4ade80;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Arbitrage Hunter</h1>
        <p class="subtitle">Real-time prediction market arbitrage detection</p>
        
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
        </div>
        
        <div class="section">
            <h2>🎯 Active Arbitrage Opportunities</h2>
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
        
        function loadData() {
            // Load opportunities
            fetch('/api/opportunities')
                .then(r => r.json())
                .then(data => {
                    displayOpportunities(data);
                    updateStats(data);
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
            
            document.getElementById('timestamp').textContent = 
                'Last updated: ' + new Date().toLocaleString();
        }
        
        function displayOpportunities(opps) {
            const container = document.getElementById('opportunities-table');
            
            if (!opps || opps.length === 0) {
                container.innerHTML = '<div class="no-data">No active arbitrage opportunities found</div>';
                return;
            }
            
            let html = '<table><thead><tr>';
            html += '<th>Event</th><th>Platform A</th><th>Price A</th>';
            html += '<th>Platform B</th><th>Price B</th>';
            html += '<th>Bet Amount A</th><th>Bet Amount B</th>';
            html += '<th>Profit</th><th>Profit %</th><th>Detected</th></tr></thead><tbody>';
            
            opps.forEach(opp => {
                html += '<tr>';
                html += '<td>' + (opp.event_name || 'N/A').substring(0, 50) + '</td>';
                html += '<td><span class="badge badge-' + opp.platform_a + '">' + opp.platform_a + '</span></td>';
                html += '<td>' + (opp.platform_a_price * 100).toFixed(2) + '%</td>';
                html += '<td><span class="badge badge-' + opp.platform_b + '">' + opp.platform_b + '</span></td>';
                html += '<td>' + (opp.platform_b_price * 100).toFixed(2) + '%</td>';
                html += '<td>' + formatCurrency(opp.bet_amount_a) + '</td>';
                html += '<td>' + formatCurrency(opp.bet_amount_b) + '</td>';
                html += '<td class="profit-positive">' + formatCurrency(opp.profit || 0) + '</td>';
                html += '<td class="profit-positive">' + formatPercent(opp.profit_percentage) + '</td>';
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
            // Update active opportunities count from the data
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
                })
                .catch(e => console.error('Error loading stats:', e));
        }
        
        // Load data on page load
        loadData();
        loadStats();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadData();
            loadStats();
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
        return jsonify(opportunities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recent-prices')
def api_recent_prices():
    """API endpoint for recent market prices"""
    try:
        db = get_db()
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        # Get latest prices for top markets
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
        
        # Convert ObjectId and datetime
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
        
        # Count active opportunities (within last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        active_count = db.arbitrage_opportunities.count_documents({
            "status": "active",
            "detected_at": {"$gte": cutoff_time}
        })
        
        # Count opportunities in last 24h
        last_24h = datetime.utcnow() - timedelta(hours=24)
        total_24h = db.arbitrage_opportunities.count_documents({
            "detected_at": {"$gte": last_24h}
        })
        
        # Average profit percentage for active opportunities
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
        
        return jsonify({
            "active_opportunities": active_count,
            "total_24h": total_24h,
            "avg_profit_percentage": round(avg_profit, 2),
            "max_profit_percentage": round(max_profit, 2)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("🌐 Starting Flask dashboard server...")
    print("📊 Dashboard available at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

