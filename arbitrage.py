"""Arbitrage detection and bet sizing logic"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from config import get_db
from models import create_arbitrage_opportunity_doc


def calculate_arbitrage(yes_price_a: float, no_price_b: float, 
                       yes_price_b: float, no_price_a: float,
                       total_investment: float = 100.0) -> Optional[Dict]:
    """
    Calculate arbitrage opportunity between two platforms
    
    Args:
        yes_price_a: Yes price on platform A (0-1)
        no_price_b: No price on platform B (0-1) 
        yes_price_b: Yes price on platform B (0-1)
        no_price_a: No price on platform A (0-1)
        total_investment: Total amount to invest (default $100)
    
    Returns:
        Dict with arbitrage details or None if no arbitrage
        Note: platform_a and platform_b will be set by caller
    """
    # Check both directions: A yes + B no, and B yes + A no
    
    # Direction 1: Bet Yes on A, No on B
    combined_prob_1 = yes_price_a + no_price_b
    profit_1 = None
    bet_a_1 = None
    bet_b_1 = None
    if combined_prob_1 < 1.0:
        # Guaranteed profit
        # If we bet $X on A Yes and $Y on B No:
        # X / yes_price_a = Y / no_price_b = payout
        # X + Y = total_investment
        # Solving: X = total_investment * yes_price_a / (yes_price_a + no_price_b)
        bet_a_1 = total_investment * yes_price_a / combined_prob_1
        bet_b_1 = total_investment * no_price_b / combined_prob_1
        payout = bet_a_1 / yes_price_a
        profit_1 = payout - total_investment
        profit_pct_1 = (profit_1 / total_investment) * 100
    else:
        profit_pct_1 = None
    
    # Direction 2: Bet Yes on B, No on A
    combined_prob_2 = yes_price_b + no_price_a
    profit_2 = None
    bet_b_2 = None
    bet_a_2 = None
    if combined_prob_2 < 1.0:
        bet_b_2 = total_investment * yes_price_b / combined_prob_2
        bet_a_2 = total_investment * no_price_a / combined_prob_2
        payout = bet_b_2 / yes_price_b
        profit_2 = payout - total_investment
        profit_pct_2 = (profit_2 / total_investment) * 100
    else:
        profit_pct_2 = None
    
    # Choose the better arbitrage opportunity
    # Note: platform_a and platform_b will be set by the caller based on actual platforms
    if profit_pct_1 is not None and (profit_pct_2 is None or profit_pct_1 > profit_pct_2):
        return {
            "platform_a_outcome": "yes",
            "platform_a_price": yes_price_a,
            "platform_b_outcome": "no",
            "platform_b_price": no_price_b,
            "bet_amount_a": round(bet_a_1, 2),
            "bet_amount_b": round(bet_b_1, 2),
            "total_investment": total_investment,
            "guaranteed_payout": round(bet_a_1 / yes_price_a, 2),
            "profit": round(profit_1, 2),
            "profit_percentage": round(profit_pct_1, 4),
            "combined_probability": round(combined_prob_1, 4)
        }
    elif profit_pct_2 is not None:
        return {
            "platform_a_outcome": "yes",
            "platform_a_price": yes_price_b,
            "platform_b_outcome": "no",
            "platform_b_price": no_price_a,
            "bet_amount_a": round(bet_b_2, 2),
            "bet_amount_b": round(bet_a_2, 2),
            "total_investment": total_investment,
            "guaranteed_payout": round(bet_b_2 / yes_price_b, 2),
            "profit": round(profit_2, 2),
            "profit_percentage": round(profit_pct_2, 4),
            "combined_probability": round(combined_prob_2, 4)
        }
    
    return None


def find_arbitrage_opportunities(polymarket_prices: List[Dict], 
                                 kalshi_prices: List[Dict]) -> List[Dict]:
    """
    Find arbitrage opportunities by matching events across platforms
    
    Args:
        polymarket_prices: List of {market_id, event_name, yes_price, no_price}
        kalshi_prices: List of {market_id, event_name, yes_price, no_price}
    
    Returns:
        List of arbitrage opportunity dictionaries
    """
    opportunities = []
    
    # Create lookup by event name (normalized)
    def normalize_name(name: str) -> str:
        """Normalize event name for matching"""
        return name.lower().strip().replace("'", "").replace('"', "")
    
    kalshi_lookup = {normalize_name(p["event_name"]): p for p in kalshi_prices}
    
    # Match Polymarket events with Kalshi events
    for pm_market in polymarket_prices:
        normalized_name = normalize_name(pm_market["event_name"])
        
        if normalized_name in kalshi_lookup:
            kalshi_market = kalshi_lookup[normalized_name]
            
            # Check for arbitrage
            arb = calculate_arbitrage(
                yes_price_a=pm_market["yes_price"],
                no_price_b=kalshi_market["no_price"],
                yes_price_b=kalshi_market["yes_price"],
                no_price_a=pm_market["no_price"]
            )
            
            if arb and arb["profit_percentage"] > 0:
                # Determine which platform is which based on which direction was better
                # Check if direction 1 (PM yes + Kalshi no) or direction 2 (Kalshi yes + PM no) was better
                # Direction 1: arb["platform_a_price"] == pm_market["yes_price"]
                # Direction 2: arb["platform_a_price"] == kalshi_market["yes_price"]
                
                # If platform_a_price matches PM yes price, then direction 1 was chosen
                if abs(arb["platform_a_price"] - pm_market["yes_price"]) < 0.001:
                    # Direction 1: Bet Yes on Polymarket, No on Kalshi
                    arb["platform_a"] = "polymarket"
                    arb["platform_b"] = "kalshi"
                    arb["platform_a_outcome"] = "yes"
                    arb["platform_b_outcome"] = "no"
                    # bet_amount_a already goes to platform_a (PM), bet_amount_b to platform_b (Kalshi) - correct!
                else:
                    # Direction 2: Bet Yes on Kalshi, No on Polymarket
                    arb["platform_a"] = "kalshi"
                    arb["platform_b"] = "polymarket"
                    arb["platform_a_outcome"] = "yes"
                    arb["platform_b_outcome"] = "no"
                    # In calculate_arbitrage for direction 2, bet_amount_a = bet_b_2 (goes to Kalshi Yes) ✓
                    # and bet_amount_b = bet_a_2 (goes to PM No) ✓
                    # So the bet amounts are already correct for this platform assignment!
                
                arb["event_name"] = pm_market["event_name"]  # Use original name
                opportunities.append(arb)
    
    return opportunities


def store_arbitrage_opportunities(opportunities: List[Dict]):
    """Store arbitrage opportunities in MongoDB"""
    db = get_db()
    
    # First, mark old opportunities as expired (older than 5 minutes)
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    db.arbitrage_opportunities.update_many(
        {"status": "active", "detected_at": {"$lt": cutoff_time}},
        {"$set": {"status": "expired"}}
    )
    
    # Store new opportunities
    for opp in opportunities:
        doc = create_arbitrage_opportunity_doc(
            event_name=opp["event_name"],
            platform_a=opp["platform_a"],
            platform_a_price=opp["platform_a_price"],
            platform_b=opp["platform_b"],
            platform_b_price=opp["platform_b_price"],
            profit_percentage=opp["profit_percentage"],
            bet_amount_a=opp["bet_amount_a"],
            bet_amount_b=opp["bet_amount_b"]
        )
        
        # Update or insert
        db.arbitrage_opportunities.update_one(
            {"opportunity_id": doc["opportunity_id"]},
            {"$set": doc},
            upsert=True
        )


def get_active_opportunities(limit: int = 50) -> List[Dict]:
    """Get active arbitrage opportunities"""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    
    opportunities = list(db.arbitrage_opportunities.find({
        "status": "active",
        "detected_at": {"$gte": cutoff_time}
    }).sort("profit_percentage", -1).limit(limit))
    
    # Convert ObjectId to string for JSON serialization and ensure all fields exist
    for opp in opportunities:
        opp["_id"] = str(opp["_id"])
        opp["detected_at"] = opp["detected_at"].isoformat()
        
        # Ensure profit field exists
        if "profit" not in opp or opp.get("profit") == 0:
            total_investment = opp.get("bet_amount_a", 0) + opp.get("bet_amount_b", 0)
            profit_pct = opp.get("profit_percentage", 0) / 100
            if profit_pct > 0:
                opp["profit"] = round(total_investment * profit_pct / (1 + profit_pct), 2)
            else:
                opp["profit"] = 0
        
        # Ensure expiration_date is properly formatted
        if "expiration_date" in opp and isinstance(opp["expiration_date"], datetime):
            opp["expiration_date"] = opp["expiration_date"].isoformat()
        elif "expiration_date" not in opp:
            # Set a default expiration (30 days from now)
            default_exp = datetime.utcnow() + timedelta(days=30)
            opp["expiration_date"] = default_exp.isoformat()
    
    return opportunities

