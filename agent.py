"""Main arbitrage detection agent with prolonged coordination"""
import time
import traceback
import random
from datetime import datetime, timedelta
from config import get_db, POLL_INTERVAL_SECONDS
from models import create_market_price_doc
from polymarket import PolymarketClient
from kalshi import KalshiClient
from arbitrage import find_arbitrage_opportunities, store_arbitrage_opportunities
from position_manager import PositionManager


class ArbitrageAgent:
    """Main agent with prolonged coordination - multi-day position tracking"""
    
    def __init__(self):
        self.polymarket = PolymarketClient()
        self.kalshi = KalshiClient()
        self.db = get_db()
        self.position_manager = PositionManager()
        self.running = False
        self.api_failure_rate = 0.10  # 10% chance of API failure
        self.retry_delay = 1  # Initial retry delay in seconds
        self.max_retries = 5
        
        # Load state on initialization
        self._resume_from_state()
    
    def _resume_from_state(self):
        """Resume agent state from MongoDB on startup"""
        try:
            self.position_manager.log_task("recover", "success", 
                                         "Agent restarting - resuming from MongoDB state")
            
            # Get active positions
            active_positions = self.position_manager.get_active_positions()
            print(f"🔄 Resuming: Found {len(active_positions)} active positions to monitor")
            
            # Get recent tasks
            recent_tasks = self.position_manager.get_recent_tasks(limit=5)
            if recent_tasks:
                print(f"   Last action: {recent_tasks[0].get('action')} at {recent_tasks[0].get('timestamp')}")
            
            # Update market performance metrics
            self.position_manager.calculate_historical_performance()
            
        except Exception as e:
            print(f"⚠️ Error resuming state: {e}")
            self.position_manager.log_task("recover", "failure", 
                                         f"Error resuming state: {str(e)}", error=str(e))
    
    def _simulate_api_failure(self) -> bool:
        """Simulate API failure with 10% chance"""
        return random.random() < self.api_failure_rate
    
    def _fetch_with_retry(self, fetch_func, platform_name: str, max_retries: int = None):
        """Fetch data with exponential backoff retry logic"""
        max_retries = max_retries or self.max_retries
        delay = self.retry_delay
        
        for attempt in range(max_retries):
            try:
                # Simulate API failure
                if self._simulate_api_failure() and attempt < max_retries - 1:
                    raise Exception(f"Simulated {platform_name} API failure")
                
                result = fetch_func()
                if result is not None:
                    # Reset delay on success
                    self.retry_delay = 1
                    return result
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️ {platform_name} API error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"   Retrying in {wait_time}s...")
                    self.position_manager.log_task("fetch_data", "retry",
                                                 f"{platform_name} API failed, retrying in {wait_time}s",
                                                 error=str(e))
                    time.sleep(wait_time)
                else:
                    self.position_manager.log_task("fetch_data", "failure",
                                                 f"{platform_name} API failed after {max_retries} attempts",
                                                 error=str(e))
                    print(f"❌ {platform_name} API failed after {max_retries} attempts")
                    return None
        
        return None
    
    def store_market_prices(self, prices: list, platform: str):
        """Store market prices in MongoDB"""
        try:
            docs = []
            for price_data in prices:
                # Store yes price
                yes_doc = create_market_price_doc(
                    market_id=price_data["market_id"],
                    platform=platform,
                    event_name=price_data["event_name"],
                    outcome="yes",
                    price=price_data["yes_price"]
                )
                docs.append(yes_doc)
                
                # Store no price
                no_doc = create_market_price_doc(
                    market_id=price_data["market_id"],
                    platform=platform,
                    event_name=price_data["event_name"],
                    outcome="no",
                    price=price_data["no_price"]
                )
                docs.append(no_doc)
            
            if docs:
                # Use insert_many with ordered=False to continue on errors
                result = self.db.market_prices.insert_many(docs, ordered=False)
                print(f"✅ Stored {len(result.inserted_ids)} price records from {platform}")
                self.position_manager.log_task("store_prices", "success",
                                             f"Stored {len(result.inserted_ids)} prices from {platform}")
                return len(result.inserted_ids)
        except Exception as e:
            # Handle duplicate key errors gracefully
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                print(f"⚠️ Some duplicate prices from {platform} (already stored)")
            else:
                print(f"❌ Error storing {platform} prices: {e}")
                self.position_manager.log_task("store_prices", "failure",
                                             f"Error storing {platform} prices: {str(e)}",
                                             error=str(e))
                traceback.print_exc()
        return 0
    
    def fetch_and_store_prices(self, use_dummy_data=False):
        """Fetch prices from both platforms with retry logic"""
        print(f"\n🔄 Fetching prices at {datetime.utcnow().isoformat()}")
        self.position_manager.log_task("fetch_prices", "start", "Beginning price fetch cycle")
        
        # Use dummy data if requested (for demo)
        if use_dummy_data:
            print("🎲 Using dummy data for demo...")
            from generate_dummy_data import generate_dummy_market_prices, generate_dummy_arbitrage_opportunities
            events = generate_dummy_market_prices(num_events=10)
            opps = generate_dummy_arbitrage_opportunities(events)
            
            # Create positions from opportunities
            positions_created = 0
            for opp in opps[:8]:  # Create positions for first 8 opportunities
                try:
                    position_id = self.position_manager.create_position_from_opportunity(opp)
                    positions_created += 1
                    # Simulate order placement for some positions
                    if random.random() < 0.6:  # 60% chance
                        time.sleep(0.05)
                        self.position_manager.simulate_order_placement(position_id)
                except Exception as e:
                    print(f"  ⚠️ Failed to create position: {e}")
            
            self.position_manager.log_task("fetch_prices", "success", 
                                         f"Generated dummy data, created {positions_created} positions")
            return [], []
        
        # Fetch Polymarket prices with retry
        pm_prices = self._fetch_with_retry(
            lambda: self.polymarket.get_all_market_prices(limit=100),
            "Polymarket"
        )
        if pm_prices:
            print(f"✅ Found {len(pm_prices)} Polymarket markets")
            self.store_market_prices(pm_prices, "polymarket")
        else:
            pm_prices = []
        
        # Fetch Kalshi prices with retry
        kalshi_prices = self._fetch_with_retry(
            lambda: self.kalshi.get_all_market_prices(limit=100),
            "Kalshi"
        )
        if kalshi_prices:
            print(f"✅ Found {len(kalshi_prices)} Kalshi markets")
            self.store_market_prices(kalshi_prices, "kalshi")
        else:
            kalshi_prices = []
        
        return pm_prices, kalshi_prices
    
    def detect_arbitrage(self, pm_prices: list, kalshi_prices: list):
        """Detect arbitrage opportunities and create positions (Step 1 of workflow)"""
        try:
            print("🔍 Detecting arbitrage opportunities...")
            self.position_manager.log_task("detect_arbitrage", "start", "Beginning arbitrage detection")
            
            opportunities = find_arbitrage_opportunities(pm_prices, kalshi_prices)
            
            if opportunities:
                print(f"💰 Found {len(opportunities)} arbitrage opportunities!")
                
                # Store opportunities
                store_arbitrage_opportunities(opportunities)
                
                # Create positions for new opportunities (Step 1 → Step 2)
                positions_created = 0
                for opp in opportunities[:10]:  # Limit to avoid too many positions
                    try:
                        position_id = self.position_manager.create_position_from_opportunity(opp)
                        positions_created += 1
                        print(f"  📍 Created position for: {opp['event_name'][:50]}")
                        
                        # Simulate order placement after a delay (Step 2)
                        # In real system, this would be actual API calls
                        if random.random() < 0.7:  # 70% chance to "place orders"
                            time.sleep(0.1)  # Simulate delay
                            self.position_manager.simulate_order_placement(position_id)
                    except Exception as e:
                        print(f"  ⚠️ Failed to create position: {e}")
                
                self.position_manager.log_task("detect_arbitrage", "success",
                                             f"Found {len(opportunities)} opportunities, created {positions_created} positions")
                
                # Update market performance
                self.position_manager.calculate_historical_performance()
            else:
                print("ℹ️ No arbitrage opportunities found")
                self.position_manager.log_task("detect_arbitrage", "success", "No opportunities found")
        except Exception as e:
            print(f"❌ Error detecting arbitrage: {e}")
            self.position_manager.log_task("detect_arbitrage", "failure",
                                         f"Error detecting arbitrage: {str(e)}",
                                         error=str(e))
            traceback.print_exc()
    
    def run_once(self, use_dummy_data=False):
        """Run one iteration - multi-step workflow"""
        # Step 1: Fetch prices (with retry logic)
        pm_prices, kalshi_prices = self.fetch_and_store_prices(use_dummy_data=use_dummy_data)
        
        if use_dummy_data:
            print("✅ Dummy data generated and stored")
            # In dummy mode, positions are already created in fetch_and_store_prices
            # Still monitor existing positions (Step 3)
            self.monitor_positions()
            return
        
        # Step 2: Detect arbitrage and create positions (if we have price data)
        if pm_prices and kalshi_prices:
            self.detect_arbitrage(pm_prices, kalshi_prices)
        else:
            print("⚠️ Skipping arbitrage detection - missing price data")
        
        # Step 3: Monitor existing positions (runs every iteration)
        self.monitor_positions()
    
    def monitor_positions(self):
        """Step 3: Monitor positions daily until resolution"""
        try:
            updated = self.position_manager.monitor_positions()
            if updated > 0:
                print(f"📊 Monitored positions: {updated} expired and resolved")
                # Step 4: Update performance metrics
                self.position_manager.calculate_historical_performance()
        except Exception as e:
            print(f"⚠️ Error monitoring positions: {e}")
            self.position_manager.log_task("monitor_positions", "failure",
                                         f"Error monitoring: {str(e)}",
                                         error=str(e))
    
    def get_adaptive_poll_interval(self) -> int:
        """Calculate adaptive poll interval based on market performance"""
        performance = self.position_manager.get_market_performance()
        
        if not performance:
            return POLL_INTERVAL_SECONDS
        
        # Find best performing market type
        best_market = max(performance, key=lambda x: x.get("success_rate", 0))
        best_rate = best_market.get("success_rate", 0)
        
        # If a market type has >50% success rate, poll more frequently
        if best_rate > 50:
            return max(30, POLL_INTERVAL_SECONDS // 2)  # Poll twice as often
        elif best_rate > 30:
            return POLL_INTERVAL_SECONDS
        else:
            return POLL_INTERVAL_SECONDS * 2  # Poll less frequently
    
    def run(self):
        """Run the agent with prolonged coordination - state persists across restarts"""
        self.running = True
        
        # Get uptime info
        uptime = self.position_manager.get_agent_uptime()
        recovery_count = self.position_manager.get_recovery_count()
        
        print("🚀 Arbitrage Agent - Prolonged Coordination System")
        print("=" * 60)
        print(f"📊 Agent Status:")
        print(f"   • Running for: {uptime['days']} days, {uptime['hours']} hours")
        print(f"   • Positions tracked: {uptime['positions_tracked']}")
        print(f"   • Recovery events: {recovery_count}")
        print(f"⏱️  Base polling interval: {POLL_INTERVAL_SECONDS} seconds")
        print(f"🔄 State persistence: MongoDB (survives crashes)")
        print(f"📈 Adaptive strategy: Enabled")
        print("=" * 60)
        print("Press Ctrl+C to stop\n")
        
        iteration = 0
        try:
            while self.running:
                iteration += 1
                start_time = time.time()
                
                try:
                    # Get adaptive interval
                    poll_interval = self.get_adaptive_poll_interval()
                    
                    print(f"\n[Iteration {iteration}] {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Poll interval: {poll_interval}s (adaptive)")
                    
                    self.run_once()
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"❌ Unexpected error in agent loop: {e}")
                    self.position_manager.log_task("agent_loop", "failure",
                                                 f"Error in iteration {iteration}: {str(e)}",
                                                 error=str(e))
                    traceback.print_exc()
                
                # Sleep with adaptive interval
                elapsed = time.time() - start_time
                sleep_time = max(0, poll_interval - elapsed)
                
                if sleep_time > 0:
                    print(f"💤 Sleeping for {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                else:
                    print("⚠️ Warning: Iteration took longer than poll interval!")
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Agent stopped by user")
            self.position_manager.log_task("agent_shutdown", "success", 
                                         f"Agent stopped after {iteration} iterations")
        finally:
            self.running = False
            print("💾 State saved to MongoDB - agent can resume on next start")


if __name__ == "__main__":
    import sys
    use_dummy = "--dummy" in sys.argv or "-d" in sys.argv
    
    agent = ArbitrageAgent()
    
    if use_dummy:
        print("🎲 Running in DUMMY DATA mode for demo")
        print("   Run once with dummy data...")
        agent.run_once(use_dummy_data=True)
        print("\n✅ Dummy data generated! Start the dashboard with: python3 app.py")
    else:
        agent.run()

