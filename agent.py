import os
import time
import traceback
import random
from datetime import datetime, timedelta, timezone

from config import get_db, POLL_INTERVAL_SECONDS
from models import create_market_price_doc
from polymarket import PolymarketClient
from kalshi import KalshiClient
from arbitrage import find_arbitrage_opportunities, store_arbitrage_opportunities
from position_manager import PositionManager

# -------------------------------
# DEMO MODE FLAG
# -------------------------------
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class ArbitrageAgent:
    """Main agent with prolonged coordination - multi-day position tracking"""

    def __init__(self):
        self.polymarket = PolymarketClient()
        self.kalshi = KalshiClient()
        self.db = get_db()
        self.position_manager = PositionManager()
        self.running = False
        self.api_failure_rate = 0.10
        self.retry_delay = 1
        self.max_retries = 5

        self._resume_from_state()

    def _resume_from_state(self):
        try:
            self.position_manager.log_task(
                "recover",
                "success",
                "Agent restarting - resuming from MongoDB state"
            )

            active_positions = self.position_manager.get_active_positions()
            print(f"🔄 Resuming: Found {len(active_positions)} active positions to monitor")

            recent_tasks = self.position_manager.get_recent_tasks(limit=5)
            if recent_tasks:
                print(
                    f"   Last action: {recent_tasks[0].get('action')} "
                    f"at {recent_tasks[0].get('timestamp')}"
                )

            self.position_manager.calculate_historical_performance()

        except Exception as e:
            print(f"⚠️ Error resuming state: {e}")
            self.position_manager.log_task(
                "recover",
                "failure",
                f"Error resuming state: {str(e)}",
                error=str(e),
            )

    def _simulate_api_failure(self) -> bool:
        return random.random() < self.api_failure_rate

    def _fetch_with_retry(self, fetch_func, platform_name: str, max_retries: int = None):
        max_retries = max_retries or self.max_retries
        delay = self.retry_delay

        for attempt in range(max_retries):
            try:
                if self._simulate_api_failure() and attempt < max_retries - 1:
                    raise Exception(f"Simulated {platform_name} API failure")

                result = fetch_func()
                if result is not None:
                    self.retry_delay = 1
                    return result

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)
                    print(
                        f"⚠️ {platform_name} API error "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    print(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ {platform_name} API failed after {max_retries} attempts")
                    return None

        return None

    def store_market_prices(self, prices: list, platform: str):
        docs = []

        for price_data in prices:
            docs.append(
                create_market_price_doc(
                    market_id=price_data["market_id"],
                    platform=platform,
                    event_name=price_data["event_name"],
                    outcome="yes",
                    price=price_data["yes_price"],
                )
            )
            docs.append(
                create_market_price_doc(
                    market_id=price_data["market_id"],
                    platform=platform,
                    event_name=price_data["event_name"],
                    outcome="no",
                    price=price_data["no_price"],
                )
            )

        if docs:
            try:
                result = self.db.market_prices.insert_many(docs, ordered=False)
                print(f"✅ Stored {len(result.inserted_ids)} price records from {platform}")
            except Exception:
                print(f"⚠️ Duplicate prices detected for {platform} (safe to ignore)")

    # --------------------------------------------------
    # DEMO-SAFE PRICE FETCHING (NO LIVE APIS)
    # --------------------------------------------------
    def fetch_and_store_prices(self, use_dummy_data=False):
        print(f"\n🔄 Fetching prices at {datetime.now(timezone.utc).isoformat()}")

        # FORCE DEMO MODE
        if use_dummy_data or DEMO_MODE:
            print("🎲 DEMO MODE: Using deterministic prices (guaranteed arbitrage)")

            polymarket_prices = [
                {
                    "market_id": "PM_LAKERS_WIN",
                    "event_name": "Lakers vs Celtics",
                    "yes_price": 0.58,
                    "no_price": 0.44,
                }
            ]

            kalshi_prices = [
                {
                    "market_id": "KALSHI_LAKERS_WIN",
                    "event_name": "Lakers vs Celtics",
                    "yes_price": 0.47,
                    "no_price": 0.53,
                }
            ]

            self.store_market_prices(polymarket_prices, "polymarket")
            self.store_market_prices(kalshi_prices, "kalshi")

            return polymarket_prices, kalshi_prices

        # REAL API PATH (not used in demo)
        pm_prices = self._fetch_with_retry(
            lambda: self.polymarket.get_all_market_prices(limit=100),
            "Polymarket",
        ) or []

        kalshi_prices = self._fetch_with_retry(
            lambda: self.kalshi.get_all_market_prices(limit=100),
            "Kalshi",
        ) or []

        return pm_prices, kalshi_prices

    def detect_arbitrage(self, pm_prices: list, kalshi_prices: list):
        print("🔍 Detecting arbitrage opportunities...")

        opportunities = find_arbitrage_opportunities(pm_prices, kalshi_prices)

        if opportunities:
            print(f"💰 Found {len(opportunities)} arbitrage opportunities!")
            store_arbitrage_opportunities(opportunities)

            for opp in opportunities[:5]:
                position_id = self.position_manager.create_position_from_opportunity(opp)
                print(f"📍 Created position for: {opp['event_name']}")
                self.position_manager.simulate_order_placement(position_id)
        else:
            print("ℹ️ No arbitrage opportunities found")

    def monitor_positions(self):
        updated = self.position_manager.monitor_positions()
        if updated > 0:
            print(f"📊 Resolved {updated} positions")

    def get_adaptive_poll_interval(self) -> int:
        return max(5, POLL_INTERVAL_SECONDS)

    def run_once(self):
        pm_prices, kalshi_prices = self.fetch_and_store_prices()

        if pm_prices and kalshi_prices:
            self.detect_arbitrage(pm_prices, kalshi_prices)

        self.monitor_positions()

    def run(self):
        self.running = True

        uptime = self.position_manager.get_agent_uptime()
        recovery_count = self.position_manager.get_recovery_count()

        print("\n🚀 Arbitrage Agent - Prolonged Coordination System")
        print("=" * 60)
        print(f"📊 Running for: {uptime['days']} days, {uptime['hours']} hours")
        print(f"📍 Positions tracked: {uptime['positions_tracked']}")
        print(f"♻️ Recovery events: {recovery_count}")
        print(f"🧠 State persistence: MongoDB Atlas")
        print("=" * 60)

        iteration = 0
        try:
            while self.running:
                iteration += 1
                start = time.time()

                print(
                    f"\n[Iteration {iteration}] "
                    f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
                )

                self.run_once()

                sleep_time = max(0, self.get_adaptive_poll_interval() - (time.time() - start))
                print(f"💤 Sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n🛑 Agent stopped by user")

        finally:
            self.running = False
            print("💾 State saved to MongoDB — agent can resume on restart")


if __name__ == "__main__":
    agent = ArbitrageAgent()
    agent.run()
