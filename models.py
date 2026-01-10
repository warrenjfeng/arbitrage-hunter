"""MongoDB models and data structures"""
from datetime import datetime
from typing import Optional
import uuid


def create_market_price_doc(market_id: str, platform: str, event_name: str, 
                            outcome: str, price: float, timestamp: Optional[datetime] = None):
    """Create a market price document"""
    return {
        "_id": f"{platform}_{market_id}_{outcome}_{int((timestamp or datetime.utcnow()).timestamp())}",
        "market_id": market_id,
        "platform": platform,
        "event_name": event_name,
        "outcome": outcome,
        "price": price,
        "timestamp": timestamp or datetime.utcnow()
    }


def create_arbitrage_opportunity_doc(event_name: str, platform_a: str, platform_a_price: float,
                                     platform_b: str, platform_b_price: float,
                                     profit_percentage: float, bet_amount_a: float,
                                     bet_amount_b: float, opportunity_id: Optional[str] = None):
    """Create an arbitrage opportunity document"""
    return {
        "_id": opportunity_id or str(uuid.uuid4()),
        "opportunity_id": opportunity_id or str(uuid.uuid4()),
        "event_name": event_name,
        "platform_a": platform_a,
        "platform_a_price": platform_a_price,
        "platform_b": platform_b,
        "platform_b_price": platform_b_price,
        "profit_percentage": profit_percentage,
        "bet_amount_a": bet_amount_a,
        "bet_amount_b": bet_amount_b,
        "detected_at": datetime.utcnow(),
        "status": "active"
    }


def create_position_doc(event_name: str, platform_a: str, platform_b: str,
                        amount_bet_a: float, amount_bet_b: float,
                        price_a: float, price_b: float,
                        target_profit: float, expiration_date: datetime,
                        market_type: str, position_id: Optional[str] = None):
    """Create a multi-day position tracking document"""
    return {
        "_id": position_id or str(uuid.uuid4()),
        "position_id": position_id or str(uuid.uuid4()),
        "event_name": event_name,
        "platform_a": platform_a,
        "platform_b": platform_b,
        "amount_bet_a": amount_bet_a,
        "amount_bet_b": amount_bet_b,
        "entry_price_a": price_a,
        "entry_price_b": price_b,
        "target_profit": target_profit,
        "expiration_date": expiration_date,
        "market_type": market_type,
        "state": "watching",  # watching, entered, expired, profitable, loss
        "days_held": 0,
        "created_at": datetime.utcnow(),
        "last_checked": datetime.utcnow(),
        "actual_profit": None,
        "resolved_at": None
    }


def create_task_log_doc(action: str, status: str, details: str = "",
                        error: Optional[str] = None, task_id: Optional[str] = None):
    """Create a task log entry for state persistence"""
    return {
        "_id": task_id or str(uuid.uuid4()),
        "task_id": task_id or str(uuid.uuid4()),
        "action": action,  # detect, place_order, monitor, resolve, recover
        "status": status,  # success, failure, retry
        "details": details,
        "error": error,
        "timestamp": datetime.utcnow()
    }


def create_market_performance_doc(market_type: str, opportunities_found: int,
                                  profitable_arbs: int, avg_profit_pct: float):
    """Create/update market type performance tracking"""
    return {
        "_id": market_type,
        "market_type": market_type,
        "opportunities_found": opportunities_found,
        "profitable_arbs": profitable_arbs,
        "avg_profit_pct": avg_profit_pct,
        "success_rate": (profitable_arbs / opportunities_found * 100) if opportunities_found > 0 else 0,
        "last_updated": datetime.utcnow()
    }

