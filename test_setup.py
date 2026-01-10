"""Quick test script to verify setup"""
import sys
from config import get_db, get_client
from polymarket import PolymarketClient
from kalshi import KalshiClient
from arbitrage import calculate_arbitrage

def test_mongodb():
    """Test MongoDB connection"""
    print("🔍 Testing MongoDB connection...")
    try:
        db = get_db()
        # Try a simple query
        count = db.market_prices.count_documents({})
        print(f"✅ MongoDB connected! Found {count} existing price records")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

def test_polymarket():
    """Test Polymarket API"""
    print("\n🔍 Testing Polymarket API...")
    try:
        client = PolymarketClient()
        markets = client.fetch_markets(limit=5)
        if markets:
            print(f"✅ Polymarket API working! Found {len(markets)} markets")
            # Try parsing one
            parsed = client.parse_market_data(markets[0])
            if parsed:
                print(f"   Sample market: {parsed['event_name'][:50]}")
                print(f"   Yes: {parsed['yes_price']:.2%}, No: {parsed['no_price']:.2%}")
            return True
        else:
            print("⚠️ Polymarket API returned no markets (may need API key or different endpoint)")
            return False
    except Exception as e:
        print(f"❌ Polymarket API error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_kalshi():
    """Test Kalshi API"""
    print("\n🔍 Testing Kalshi API...")
    try:
        client = KalshiClient()
        markets = client.fetch_markets(limit=5)
        if markets:
            print(f"✅ Kalshi API working! Found {len(markets)} markets")
            # Try parsing one
            parsed = client.parse_market_data(markets[0])
            if parsed:
                print(f"   Sample market: {parsed['event_name'][:50]}")
                print(f"   Yes: {parsed['yes_price']:.2%}, No: {parsed['no_price']:.2%}")
            return True
        else:
            print("⚠️ Kalshi API returned no markets (may need API key)")
            return False
    except Exception as e:
        print(f"❌ Kalshi API error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_arbitrage_logic():
    """Test arbitrage calculation"""
    print("\n🔍 Testing arbitrage calculation...")
    try:
        # Example: PM Yes @ 0.45, Kalshi No @ 0.52 = 0.97 combined (3% arb)
        result = calculate_arbitrage(
            yes_price_a=0.45,  # PM Yes
            no_price_b=0.52,   # Kalshi No
            yes_price_b=0.48,  # Kalshi Yes
            no_price_a=0.55    # PM No
        )
        if result:
            print(f"✅ Arbitrage calculation working!")
            print(f"   Profit: {result['profit_percentage']:.2f}%")
            print(f"   Bet A: ${result['bet_amount_a']:.2f}")
            print(f"   Bet B: ${result['bet_amount_b']:.2f}")
            return True
        else:
            print("❌ No arbitrage detected (expected for these prices)")
            return False
    except Exception as e:
        print(f"❌ Arbitrage calculation error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing Arbitrage Hunter Setup")
    print("=" * 60)
    
    results = []
    results.append(("MongoDB", test_mongodb()))
    results.append(("Polymarket", test_polymarket()))
    results.append(("Kalshi", test_kalshi()))
    results.append(("Arbitrage Logic", test_arbitrage_logic()))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 All tests passed! You're ready to run the agent.")
    else:
        print("\n⚠️ Some tests failed. Check your .env configuration.")
        sys.exit(1)

