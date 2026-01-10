"""Multi-day position tracking and management"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import get_db
from models import (
    create_position_doc,
    create_task_log_doc,
    create_market_performance_doc
)
try:
    from generate_dummy_data import categorize_event
except ImportError:
    # Fallback if import fails
    def categorize_event(event_name):
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


class PositionManager:
    """Manages multi-day position tracking"""
    
    def __init__(self):
        self.db = get_db()
        self._setup_collections()
    
    def _setup_collections(self):
        """Create indexes for position tracking"""
        try:
            self.db.positions.create_index([("state", 1), ("last_checked", -1)])
        except Exception:
            pass  # Index may already exist
        
        try:
            self.db.positions.create_index([("expiration_date", 1)])
        except Exception:
            pass
        
        try:
            self.db.task_log.create_index([("timestamp", -1)])
        except Exception:
            pass
        
        try:
            # Market type performance uses _id as market_type, which is already unique
            # So we don't need to create another index
            pass
        except Exception:
            pass
    
    def create_position_from_opportunity(self, opportunity: Dict) -> str:
        """Create a position from a detected arbitrage opportunity"""
        try:
            event_name = opportunity["event_name"]
            market_type = categorize_event(event_name)
            
            # Calculate expiration date (default 30 days if not provided)
            expiration_date = opportunity.get("expiration_date")
            if expiration_date:
                if isinstance(expiration_date, str):
                    expiration_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            else:
                expiration_date = datetime.utcnow() + timedelta(days=30)
            
            position = create_position_doc(
                event_name=event_name,
                platform_a=opportunity["platform_a"],
                platform_b=opportunity["platform_b"],
                amount_bet_a=opportunity["bet_amount_a"],
                amount_bet_b=opportunity["bet_amount_b"],
                price_a=opportunity["platform_a_price"],
                price_b=opportunity["platform_b_price"],
                target_profit=opportunity.get("profit", 0),
                expiration_date=expiration_date,
                market_type=market_type
            )
            
            self.db.positions.insert_one(position)
            self.log_task("create_position", "success", f"Created position for {event_name[:50]}")
            
            return position["position_id"]
        except Exception as e:
            self.log_task("create_position", "failure", f"Failed to create position: {str(e)}", error=str(e))
            raise
    
    def get_active_positions(self) -> List[Dict]:
        """Get all active positions (watching or entered)"""
        positions = list(self.db.positions.find({
            "state": {"$in": ["watching", "entered"]}
        }).sort("created_at", -1))
        
        for pos in positions:
            pos["_id"] = str(pos["_id"])
            if isinstance(pos.get("created_at"), datetime):
                pos["created_at"] = pos["created_at"].isoformat()
            if isinstance(pos.get("expiration_date"), datetime):
                pos["expiration_date"] = pos["expiration_date"].isoformat()
            if isinstance(pos.get("last_checked"), datetime):
                pos["last_checked"] = pos["last_checked"].isoformat()
            
            # Calculate days held
            if pos.get("created_at"):
                created = datetime.fromisoformat(pos["created_at"].replace('Z', '+00:00'))
                days_held = (datetime.utcnow() - created.replace(tzinfo=None)).days
                pos["days_held"] = days_held
            
            # Calculate days until expiry
            if pos.get("expiration_date"):
                exp = datetime.fromisoformat(pos["expiration_date"].replace('Z', '+00:00'))
                days_left = (exp.replace(tzinfo=None) - datetime.utcnow()).days
                pos["days_until_expiry"] = max(0, days_left)
        
        return positions
    
    def update_position_state(self, position_id: str, new_state: str, 
                             actual_profit: Optional[float] = None):
        """Update position state (watching → entered → expired/profitable/loss)"""
        update_data = {
            "state": new_state,
            "last_checked": datetime.utcnow()
        }
        
        if actual_profit is not None:
            update_data["actual_profit"] = actual_profit
            update_data["resolved_at"] = datetime.utcnow()
        
        self.db.positions.update_one(
            {"position_id": position_id},
            {"$set": update_data}
        )
        
        self.log_task("update_position", "success", 
                     f"Updated position {position_id} to state {new_state}")
    
    def monitor_positions(self):
        """Monitor all active positions and update states"""
        active_positions = self.db.positions.find({
            "state": {"$in": ["watching", "entered"]}
        })
        
        updated = 0
        for position in active_positions:
            position_id = position["position_id"]
            
            # Check if expired
            expiration_date = position.get("expiration_date")
            if expiration_date:
                if isinstance(expiration_date, datetime):
                    exp_date = expiration_date
                else:
                    exp_date = datetime.fromisoformat(str(expiration_date).replace('Z', '+00:00'))
                
                if datetime.utcnow() > exp_date.replace(tzinfo=None):
                    # Market expired - simulate resolution
                    # In real system, would check actual market outcome
                    actual_profit = position.get("target_profit", 0) * random.uniform(0.8, 1.2)
                    self.update_position_state(position_id, "expired", actual_profit)
                    updated += 1
                    continue
            
            # Update last_checked
            self.db.positions.update_one(
                {"position_id": position_id},
                {"$set": {"last_checked": datetime.utcnow()}}
            )
        
        if updated > 0:
            self.log_task("monitor_positions", "success", f"Updated {updated} expired positions")
        
        return updated
    
    def simulate_order_placement(self, position_id: str):
        """Simulate placing orders on both platforms (Step 2 of workflow)"""
        position = self.db.positions.find_one({"position_id": position_id})
        if not position:
            return False
        
        if position["state"] == "watching":
            # Simulate order placement
            self.update_position_state(position_id, "entered")
            self.log_task("place_orders", "success", 
                         f"Simulated order placement for {position['event_name'][:50]}")
            return True
        return False
    
    def calculate_historical_performance(self):
        """Calculate and update market type performance metrics"""
        pipeline = [
            {"$group": {
                "_id": "$market_type",
                "opportunities_found": {"$sum": 1},
                "profitable_count": {"$sum": {"$cond": [
                    {"$gt": ["$target_profit", 0]}, 1, 0
                ]}},
                "avg_profit": {"$avg": "$target_profit"}
            }}
        ]
        
        results = list(self.db.positions.aggregate(pipeline))
        
        for result in results:
            market_type = result["_id"]
            perf_doc = create_market_performance_doc(
                market_type=market_type,
                opportunities_found=result["opportunities_found"],
                profitable_arbs=result["profitable_count"],
                avg_profit_pct=result.get("avg_profit", 0)
            )
            
            self.db.market_type_performance.update_one(
                {"_id": market_type},
                {"$set": perf_doc},
                upsert=True
            )
    
    def get_market_performance(self) -> List[Dict]:
        """Get market type performance data"""
        perf = list(self.db.market_type_performance.find({}))
        for p in perf:
            p["_id"] = str(p["_id"])
            if isinstance(p.get("last_updated"), datetime):
                p["last_updated"] = p["last_updated"].isoformat()
        return perf
    
    def log_task(self, action: str, status: str, details: str = "", error: Optional[str] = None):
        """Log a task/action for state persistence"""
        log_entry = create_task_log_doc(action, status, details, error)
        try:
            self.db.task_log.insert_one(log_entry)
        except Exception as e:
            print(f"⚠️ Failed to log task: {e}")
    
    def get_recent_tasks(self, limit: int = 50) -> List[Dict]:
        """Get recent task log entries"""
        tasks = list(self.db.task_log.find({}).sort("timestamp", -1).limit(limit))
        for task in tasks:
            task["_id"] = str(task["_id"])
            if isinstance(task.get("timestamp"), datetime):
                task["timestamp"] = task["timestamp"].isoformat()
        return tasks
    
    def get_recovery_count(self) -> int:
        """Count recovery events (task_log entries with action='recover')"""
        return self.db.task_log.count_documents({"action": "recover", "status": "success"})
    
    def get_agent_uptime(self) -> Dict:
        """Calculate agent uptime from task log"""
        first_task = self.db.task_log.find_one({}, sort=[("timestamp", 1)])
        if not first_task:
            return {"days": 0, "hours": 0, "positions_tracked": 0}
        
        start_time = first_task.get("timestamp")
        if isinstance(start_time, datetime):
            uptime = datetime.utcnow() - start_time
        else:
            uptime = timedelta(0)
        
        total_positions = self.db.positions.count_documents({})
        
        return {
            "days": uptime.days,
            "hours": uptime.seconds // 3600,
            "positions_tracked": total_positions
        }

