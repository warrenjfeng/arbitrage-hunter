"""Polymarket API client"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
from config import POLYMARKET_API_URL


class PolymarketClient:
    """Client for fetching data from Polymarket"""
    
    def __init__(self):
        self.base_url = POLYMARKET_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ArbitrageHunter/1.0"
        })
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Rate limiting: 0.5 seconds between requests
    
    def _rate_limit(self):
        """Simple rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def fetch_markets(self, limit: int = 100) -> List[Dict]:
        """
        Fetch active markets from Polymarket
        
        Uses the CLOB API to get market information. For arbitrage, we want
        markets that are currently accepting orders, even if some are resolved.
        """
        try:
            self._rate_limit()
            
            # Try Gamma API first for better active market filtering
            try:
                gamma_url = "https://gamma-api.polymarket.com/markets"
                response = self.session.get(
                    gamma_url, 
                    params={"active": "true", "limit": limit * 2}, 
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data[:limit]
                    elif isinstance(data, dict) and "data" in data:
                        return data["data"][:limit]
            except:
                pass  # Fall back to CLOB API
            
            # Fallback: Use CLOB API
            url = f"{self.base_url}/markets"
            params = {"limit": min(limit * 3, 1000)}  # Fetch more to find active ones
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Handle response format: {"data": [...], "next_cursor": "...", ...}
            if isinstance(data, dict) and "data" in data:
                all_markets = data["data"]
            elif isinstance(data, list):
                all_markets = data
            else:
                return []
            
            # Filter for markets that are accepting orders (currently tradeable)
            # We'll accept markets that are active and accepting orders, even if closed
            # (some markets may be resolved but still have orderbooks)
            open_markets = []
            for m in all_markets:
                # Prioritize markets that are clearly open
                if (m.get("active", False) 
                    and not m.get("archived", False)
                    and m.get("accepting_orders") is True):
                    open_markets.append(m)
                elif (m.get("active", False) 
                      and not m.get("closed", False)
                      and not m.get("archived", False)):
                    # Also include active, non-closed markets
                    open_markets.append(m)
                    
                if len(open_markets) >= limit:
                    break
            
            # If we still don't have enough, relax further (for testing)
            if len(open_markets) < limit // 2:
                for m in all_markets:
                    if (m.get("active", False) and not m.get("archived", False)
                        and m not in open_markets):
                        open_markets.append(m)
                        if len(open_markets) >= limit:
                            break
            
            return open_markets
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Polymarket markets: {e}")
            # Fallback: try alternative endpoint or return sample data for testing
            return self._fetch_markets_fallback()
    
    def _fetch_markets_fallback(self) -> List[Dict]:
        """Fallback method using Gamma API or sample data"""
        try:
            # Try Gamma API as alternative
            gamma_url = "https://gamma-api.polymarket.com/markets"
            self._rate_limit()
            response = self.session.get(gamma_url, params={"active": "true"}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return data[:100]
            elif isinstance(data, dict) and "data" in data:
                return data["data"][:100]
        except:
            pass
        
        # Return empty list if all fails
        return []
    
    def parse_market_data(self, market: Dict) -> Optional[Dict]:
        """
        Parse a Polymarket market object into our standard format
        
        Returns: {
            'market_id': str,
            'event_name': str,
            'yes_price': float,
            'no_price': float
        } or None
        """
        try:
            # Handle if market is a string (shouldn't happen, but be safe)
            if not isinstance(market, dict):
                return None
            
            # Polymarket market structure varies, handle common formats
            market_id = (
                str(market.get("id", "")) or 
                str(market.get("market_id", "")) or 
                str(market.get("_id", "")) or
                str(market.get("condition_id", "")) or
                str(market.get("conditionId", ""))
            )
            
            # Extract question/event name
            event_name = (
                market.get("question") or 
                market.get("title") or 
                market.get("name") or 
                market.get("description", "")
            )
            
            if not event_name or not market_id:
                return None
            
            # Extract prices - Polymarket uses different formats
            yes_price = None
            no_price = None
            
            # Format 1: Gamma API format with outcomePrices (JSON strings)
            if "outcomePrices" in market:
                import json
                try:
                    prices_str = market.get("outcomePrices", "[]")
                    outcomes_str = market.get("outcomes", "[]")
                    if isinstance(prices_str, str):
                        prices = json.loads(prices_str)
                        outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
                    else:
                        prices = prices_str
                        outcomes = outcomes_str
                    
                    for i, outcome in enumerate(outcomes):
                        if i < len(prices):
                            price_val = float(prices[i]) if prices[i] else 0.0
                            if outcome.lower() in ["yes", "y"]:
                                yes_price = price_val
                            elif outcome.lower() in ["no", "n"]:
                                no_price = price_val
                except (json.JSONDecodeError, ValueError, IndexError):
                    pass
            
            # Format 2: CLOB API format with tokens array
            if (yes_price is None or no_price is None) and "tokens" in market:
                if isinstance(market["tokens"], list):
                    for token in market["tokens"]:
                        if isinstance(token, dict):
                            outcome = token.get("outcome", "")
                            price = float(token.get("price", token.get("lastPrice", 0)))
                            
                            outcome_lower = outcome.lower().strip()
                            if outcome_lower in ["yes", "y"]:
                                yes_price = price
                            elif outcome_lower in ["no", "n"]:
                                no_price = price
                    
                    # If still no Yes/No but have exactly 2 tokens, use them as binary
                    if yes_price is None and no_price is None and len(market["tokens"]) == 2:
                        yes_price = float(market["tokens"][0].get("price", 0))
                        no_price = float(market["tokens"][1].get("price", 0))
            
            # Format 3: Direct outcome arrays (if exists)
            if (yes_price is None or no_price is None) and "outcomes" in market:
                outcomes = market["outcomes"]
                if isinstance(outcomes, list):
                    for outcome in outcomes:
                        if isinstance(outcome, dict):
                            if outcome.get("name", "").lower() in ["yes", "y"]:
                                yes_price = float(outcome.get("price", 0))
                            elif outcome.get("name", "").lower() in ["no", "n"]:
                                no_price = float(outcome.get("price", 0))
            
            # Format 4: Direct price fields
            if yes_price is None or no_price is None:
                yes_price = market.get("yesPrice") or market.get("yes_price")
                no_price = market.get("noPrice") or market.get("no_price")
                
                if yes_price is not None:
                    yes_price = float(yes_price)
                if no_price is not None:
                    no_price = float(no_price)
            
            # If still no prices, skip this market
            if yes_price is None or no_price is None:
                return None
            
            # Normalize prices to 0-1 range
            total = yes_price + no_price
            if total > 0:
                yes_price = yes_price / total
                no_price = no_price / total
            else:
                return None
            
            return {
                "market_id": str(market_id),
                "event_name": event_name.strip(),
                "yes_price": round(yes_price, 4),
                "no_price": round(no_price, 4)
            }
            
        except Exception as e:
            print(f"⚠️ Error parsing Polymarket market: {e}")
            return None
    
    def get_all_market_prices(self, limit: int = 100) -> List[Dict]:
        """Get all market prices in our standard format"""
        markets = self.fetch_markets(limit=limit)
        prices = []
        
        for market in markets:
            parsed = self.parse_market_data(market)
            if parsed:
                prices.append(parsed)
        
        return prices

