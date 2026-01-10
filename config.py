"""Configuration and MongoDB connection setup"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "arbitrage_hunter")

# API configuration
POLYMARKET_API_URL = os.getenv("POLYMARKET_API_URL", "https://clob.polymarket.com")
KALSHI_API_URL = os.getenv("KALSHI_API_URL", "https://api.kalshi.com/trade-api/v2")
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")
KALSHI_API_SECRET = os.getenv("KALSHI_API_SECRET", "")

# Load Kalshi RSA key from file if not in env and secret looks like base64 (old format)
if not KALSHI_API_SECRET or (KALSHI_API_SECRET and not KALSHI_API_SECRET.startswith('-----BEGIN')):
    rsa_key_path = os.path.join(os.path.dirname(__file__), "kalshi_rsa_key.pem")
    if os.path.exists(rsa_key_path):
        try:
            with open(rsa_key_path, "r") as f:
                file_key = f.read().strip()
                # Use file key if env doesn't have a valid key, or if env has base64 encoded version
                if not KALSHI_API_SECRET or (KALSHI_API_SECRET and len(KALSHI_API_SECRET) > 1000):
                    KALSHI_API_SECRET = file_key
        except Exception as e:
            print(f"⚠️ Warning: Could not load Kalshi RSA key from file: {e}")

# Agent configuration
POLL_INTERVAL_SECONDS = 60

# MongoDB client
_client = None
_db = None


def get_db():
    """Get MongoDB database instance"""
    global _db
    if _db is None:
        client = get_client()
        _db = client[DATABASE_NAME]
        _setup_indexes(_db)
    return _db


def get_client():
    """Get MongoDB client instance"""
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            _client.admin.command('ping')
            print("✅ Connected to MongoDB successfully")
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    return _client


def _setup_indexes(db):
    """Create indexes for better query performance"""
    # Market prices indexes
    db.market_prices.create_index([("market_id", 1), ("platform", 1), ("timestamp", -1)])
    db.market_prices.create_index([("event_name", 1), ("timestamp", -1)])
    db.market_prices.create_index([("timestamp", -1)])
    
    # Arbitrage opportunities indexes
    db.arbitrage_opportunities.create_index([("opportunity_id", 1)], unique=True)
    db.arbitrage_opportunities.create_index([("status", 1), ("detected_at", -1)])
    db.arbitrage_opportunities.create_index([("detected_at", -1)])
    
    # Positions indexes
    db.positions.create_index([("position_id", 1)], unique=True)
    db.positions.create_index([("created_at", -1)])
    db.positions.create_index([("state", 1), ("last_checked", -1)])
    db.positions.create_index([("expiration_date", 1)])
    
    # Task log indexes
    db.task_log.create_index([("timestamp", -1)])
    db.task_log.create_index([("action", 1), ("status", 1)])
    
    # Market performance indexes (uses _id as market_type, already indexed)
    try:
        db.market_type_performance.create_index([("market_type", 1)], unique=True)
    except Exception:
        pass  # May already exist with different options
    
    print("✅ Database indexes created")

