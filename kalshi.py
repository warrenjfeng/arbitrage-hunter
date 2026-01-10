"""Kalshi API client"""
import requests
import time
import base64
import hmac
import hashlib
import os
from typing import List, Dict, Optional
from datetime import datetime
from config import KALSHI_API_URL, KALSHI_API_KEY, KALSHI_API_SECRET


class KalshiClient:
    """Client for fetching data from Kalshi"""
    
    def __init__(self):
        self.base_url = KALSHI_API_URL
        self.api_key = KALSHI_API_KEY
        self.api_secret = KALSHI_API_SECRET
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 0.5
    
    def _rate_limit(self):
        """Simple rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _generate_signature(self, method: str, path: str, timestamp: str, body: str = "") -> str:
        """
        Generate signature for Kalshi API authentication
        
        Kalshi uses RSA private key for signing. The secret should be either:
        1. A path to an RSA private key file (.pem)
        2. The RSA private key content itself
        """
        if not self.api_key or not self.api_secret:
            return ""
        
        try:
            message = f"{timestamp}{method}{path}{body}".encode('utf-8')
            
            # Check if api_secret is a file path or the key content
            if os.path.exists(self.api_secret):
                # It's a file path
                with open(self.api_secret, 'r') as f:
                    key_content = f.read()
            elif self.api_secret.startswith('-----BEGIN'):
                # It's the key content directly
                key_content = self.api_secret
            else:
                # Try base64 decode (old format)
                try:
                    key_content = base64.b64decode(self.api_secret).decode('utf-8')
                except:
                    key_content = self.api_secret
            
            # Try RSA signing using cryptography library if available
            try:
                from cryptography.hazmat.primitives import serialization, hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                from cryptography.hazmat.backends import default_backend
                
                # Load the private key
                private_key = serialization.load_pem_private_key(
                    key_content.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                
                # Sign the message
                signature = private_key.sign(
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return base64.b64encode(signature).decode('utf-8')
            except ImportError:
                # Fallback: try using pycryptodome or pycrypto if available
                try:
                    from Crypto.PublicKey import RSA
                    from Crypto.Signature import pkcs1_15
                    from Crypto.Hash import SHA256
                    
                    key = RSA.import_key(key_content)
                    h = SHA256.new(message)
                    signature = pkcs1_15.new(key).sign(h)
                    return base64.b64encode(signature).decode('utf-8')
                except ImportError:
                    # Last resort: use HMAC with a hash of the key (won't work for real auth)
                    print("⚠️ Warning: cryptography library not installed. Install with: pip install cryptography")
                    print("   Attempting HMAC fallback (may not work for actual authentication)")
                    key_hash = hashlib.sha256(key_content.encode('utf-8')).digest()
                    signature = hmac.new(key_hash[:32], message, hashlib.sha256).digest()
                    return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"⚠️ Warning: Kalshi signature generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def fetch_markets(self, limit: int = 100) -> List[Dict]:
        """
        Fetch active markets from Kalshi
        
        Uses Kalshi REST API v2
        """
        try:
            self._rate_limit()
            
            # Kalshi API endpoint for markets
            path = "/markets"
            method = "GET"
            url = f"{self.base_url}{path}"
            
            params = {
                "limit": limit,
                "status": "open"  # Only open markets
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add authentication if credentials are provided
            if self.api_key and self.api_secret:
                timestamp = str(int(time.time() * 1000))  # Kalshi uses milliseconds
                signature = self._generate_signature(method, path, timestamp, "")
                if signature:  # Only add auth headers if signature was generated
                    headers.update({
                        "KALSHI-ACCESS-KEY": self.api_key,
                        "KALSHI-ACCESS-SIGNATURE": signature,
                        "KALSHI-ACCESS-TIMESTAMP": timestamp
                    })
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            # If auth fails, try public endpoint
            if response.status_code == 401:
                print("⚠️ Kalshi authentication failed, trying public endpoint...")
                # Some endpoints might be public, try without auth
                response = self.session.get(url, params=params, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            # Handle different possible response formats
            if isinstance(data, list):
                markets = data[:limit]
            elif isinstance(data, dict):
                markets = data.get("markets", data.get("data", []))[:limit]
            else:
                markets = []
            
            return markets
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Kalshi markets: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text[:200]}")
            # Return empty list on error
            return []
    
    def parse_market_data(self, market: Dict) -> Optional[Dict]:
        """
        Parse a Kalshi market object into our standard format
        
        Returns: {
            'market_id': str,
            'event_name': str,
            'yes_price': float,
            'no_price': float
        } or None
        """
        try:
            market_id = market.get("ticker") or market.get("market_id") or market.get("event_ticker", "")
            
            # Extract question/event name
            event_name = (
                market.get("title") or 
                market.get("question") or 
                market.get("subtitle") or 
                market.get("event_ticker", "")
            )
            
            if not event_name or not market_id:
                return None
            
            # Extract prices - Kalshi uses yes/no prices directly
            yes_price = market.get("yes_bid", market.get("yes_price"))
            no_price = market.get("no_bid", market.get("no_price"))
            
            # Try alternative field names
            if yes_price is None:
                yes_price = market.get("yes_bid_price")
            if no_price is None:
                no_price = market.get("no_bid_price")
            
            # Convert to float if they're strings
            if isinstance(yes_price, str):
                yes_price = float(yes_price)
            if isinstance(no_price, str):
                no_price = float(no_price)
            
            # If still no prices, try to get from orderbook
            if yes_price is None or no_price is None:
                orderbook = market.get("orderbook", {})
                yes_orderbook = orderbook.get("yes", {})
                no_orderbook = orderbook.get("no", {})
                
                if yes_price is None and yes_orderbook:
                    bids = yes_orderbook.get("bids", [])
                    if bids:
                        yes_price = float(bids[0].get("price", bids[0].get("p", 0)))
                
                if no_price is None and no_orderbook:
                    bids = no_orderbook.get("bids", [])
                    if bids:
                        no_price = float(bids[0].get("price", bids[0].get("p", 0)))
            
            # Normalize prices to 0-1 range (Kalshi prices are typically in cents, so divide by 100)
            if yes_price is not None and yes_price > 1:
                yes_price = yes_price / 100
            if no_price is not None and no_price > 1:
                no_price = no_price / 100
            
            # If we still don't have both prices, skip
            if yes_price is None or no_price is None:
                return None
            
            # Normalize so they sum to 1 (sometimes they don't exactly)
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
            print(f"⚠️ Error parsing Kalshi market: {e}")
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

