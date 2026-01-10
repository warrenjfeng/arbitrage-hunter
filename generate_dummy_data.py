"""Generate dummy data for demo purposes"""
import random
from datetime import datetime, timedelta
from config import get_db
from models import (
    create_market_price_doc,
    create_arbitrage_opportunity_doc,
    create_position_doc
)

# Sample event names for realistic demo - 2026-2028 forward-looking markets
POLITICAL_EVENTS = [
    "Will the Republican Party win control of the Senate in 2026 midterms?",
    "Will Kamala Harris be the Democratic nominee for 2028 Presidential Election?",
    "Will there be a third-party candidate in the 2028 Presidential Election?",
    "Will the House flip to Democratic control in 2026?",
    "Will a woman be elected President in 2028?",
    "Will there be a contested 2028 Presidential Election?",
]

SPORTS_EVENTS = [
    "Will the Warriors win the 2026 NBA Championship?",
    "Will the Chiefs win the 2027 Super Bowl?",
    "Will the US qualify for the 2026 World Cup?",
    "Will LeBron James win another NBA championship by 2027?",
    "Will the Lakers make the 2026 NBA Finals?",
    "Will a European team win the 2026 World Cup?",
    "Will the Patriots make the 2026 NFL Playoffs?",
    "Will the Warriors win the 2027 NBA Championship?",
]

TECH_EVENTS = [
    "Will Bitcoin reach $150k by end of 2026?",
    "Will Ethereum reach $10k by end of 2026?",
    "Will OpenAI release GPT-6 by Q3 2027?",
    "Will Apple release a foldable iPhone by 2027?",
    "Will Tesla achieve full self-driving by 2026?",
    "Will Google's Gemini surpass GPT-5 by 2027?",
    "Will there be a major AI breakthrough in 2026?",
    "Will Amazon stock reach $250 by end of 2026?",
    "Will SpaceX successfully land on Mars by 2027?",
    "Will quantum computing achieve commercial viability by 2027?",
]

ECONOMIC_EVENTS = [
    "Will the Fed cut rates below 3% by end of 2026?",
    "Will there be a recession in 2026?",
    "Will the S&P 500 reach 6000 by end of 2026?",
    "Will inflation drop below 2% by Q2 2026?",
    "Will unemployment rise above 5% in 2026?",
    "Will the US enter a recession in 2027?",
    "Will gold reach $3000/oz by end of 2026?",
    "Will the dollar index fall below 100 in 2026?",
]

SAMPLE_EVENTS = POLITICAL_EVENTS + SPORTS_EVENTS + TECH_EVENTS + ECONOMIC_EVENTS


def categorize_event(event_name):
    """Categorize event by keywords"""
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


def generate_dummy_market_prices(num_events=20):
    """Generate dummy market prices for both platforms with expiration dates"""
    db = get_db()
    
    print(f"📊 Generating dummy market prices for {num_events} events...")
    
    # Distribute events across categories
    num_per_category = max(1, num_events // 4)
    events = []
    events.extend(random.sample(POLITICAL_EVENTS, min(num_per_category, len(POLITICAL_EVENTS))))
    events.extend(random.sample(SPORTS_EVENTS, min(num_per_category, len(SPORTS_EVENTS))))
    events.extend(random.sample(TECH_EVENTS, min(num_per_category, len(TECH_EVENTS))))
    events.extend(random.sample(ECONOMIC_EVENTS, min(num_per_category, len(ECONOMIC_EVENTS))))
    
    # Fill remaining slots randomly
    remaining = num_events - len(events)
    if remaining > 0:
        all_events = list(set(SAMPLE_EVENTS) - set(events))
        events.extend(random.sample(all_events, min(remaining, len(all_events))))
    
    events = events[:num_events]
    docs = []
    
    # Generate expiration dates (7-365 days from now)
    base_date = datetime.utcnow()
    
    for event_name in events:
        # Generate slightly different prices on each platform to create arbitrage opportunities
        # Polymarket prices
        pm_yes = round(random.uniform(0.40, 0.60), 4)
        pm_no = round(1.0 - pm_yes, 4)
        
        # Kalshi prices (different from Polymarket to create arbs)
        kalshi_yes = round(random.uniform(0.40, 0.60), 4)
        kalshi_no = round(1.0 - kalshi_yes, 4)
        
        # Create market IDs
        pm_market_id = f"pm_{hash(event_name) % 100000}"
        kalshi_market_id = f"kal_{hash(event_name) % 100000}"
        
        # Generate expiration date (7-365 days from now)
        days_until_expiry = random.randint(7, 365)
        expiration_date = base_date + timedelta(days=days_until_expiry)
        
        # Store Polymarket prices
        docs.append(create_market_price_doc(
            market_id=pm_market_id,
            platform="polymarket",
            event_name=event_name,
            outcome="yes",
            price=pm_yes
        ))
        docs.append(create_market_price_doc(
            market_id=pm_market_id,
            platform="polymarket",
            event_name=event_name,
            outcome="no",
            price=pm_no
        ))
        
        # Store Kalshi prices
        docs.append(create_market_price_doc(
            market_id=kalshi_market_id,
            platform="kalshi",
            event_name=event_name,
            outcome="yes",
            price=kalshi_yes
        ))
        docs.append(create_market_price_doc(
            market_id=kalshi_market_id,
            platform="kalshi",
            event_name=event_name,
            outcome="no",
            price=kalshi_no
        ))
    
    try:
        result = db.market_prices.insert_many(docs, ordered=False)
        print(f"✅ Inserted {len(result.inserted_ids)} price records")
        return events
    except Exception as e:
        if "duplicate" in str(e).lower():
            print(f"⚠️ Some prices already exist (duplicate keys)")
        else:
            print(f"❌ Error inserting prices: {e}")
        return events


def generate_dummy_arbitrage_opportunities(events):
    """Generate dummy arbitrage opportunities with varied profit percentages"""
    db = get_db()
    
    print(f"💰 Generating arbitrage opportunities...")
    
    opportunities = []
    base_date = datetime.utcnow()
    
    for i, event_name in enumerate(events[:15]):  # Create opportunities for first 15 events
        # Create arbitrage opportunities with varied profit percentages
        # Some high profit (>3%), some medium (1-3%), some low (<1%)
        if i < 5:
            # High profit opportunities (>3%)
            pm_yes = round(random.uniform(0.42, 0.46), 4)
            kalshi_no = round(random.uniform(0.50, 0.54), 4)
        elif i < 10:
            # Medium profit (1-3%)
            pm_yes = round(random.uniform(0.45, 0.49), 4)
            kalshi_no = round(random.uniform(0.48, 0.52), 4)
        else:
            # Low profit (<1%)
            pm_yes = round(random.uniform(0.48, 0.50), 4)
            kalshi_no = round(random.uniform(0.49, 0.51), 4)
        
        combined = pm_yes + kalshi_no
        
        if combined < 1.0:
            profit_pct = ((1.0 - combined) / combined) * 100
            total_investment = 100.0
            bet_a = round(total_investment * pm_yes / combined, 2)
            bet_b = round(total_investment * kalshi_no / combined, 2)
            profit_dollars = round((total_investment / combined) - total_investment, 2)
            
            # Generate expiration date (7-180 days from now)
            days_until_expiry = random.randint(7, 180)
            expiration_date = base_date + timedelta(days=days_until_expiry)
            
            opp = create_arbitrage_opportunity_doc(
                event_name=event_name,
                platform_a="polymarket",
                platform_a_price=pm_yes,
                platform_b="kalshi",
                platform_b_price=kalshi_no,
                profit_percentage=round(profit_pct, 4),
                bet_amount_a=bet_a,
                bet_amount_b=bet_b
            )
            # Add profit and expiration date
            opp["profit"] = profit_dollars
            opp["expiration_date"] = expiration_date
            opp["days_until_expiry"] = days_until_expiry
            opportunities.append(opp)
    
    # Insert opportunities
    inserted = 0
    for opp in opportunities:
        try:
            db.arbitrage_opportunities.update_one(
                {"opportunity_id": opp["opportunity_id"]},
                {"$set": opp},
                upsert=True
            )
            inserted += 1
        except Exception as e:
            print(f"⚠️ Error inserting opportunity: {e}")
    
    print(f"✅ Created {inserted} arbitrage opportunities")
    return opportunities


def clear_old_data():
    """Clear old dummy data (optional)"""
    db = get_db()
    print("🧹 Clearing old data...")
    
    # Clear market prices (optional - comment out if you want to keep data)
    # db.market_prices.delete_many({"platform": {"$in": ["polymarket", "kalshi"]}})
    
    # Mark old opportunities as expired
    cutoff = datetime.utcnow() - timedelta(hours=1)
    result = db.arbitrage_opportunities.update_many(
        {"status": "active", "detected_at": {"$lt": cutoff}},
        {"$set": {"status": "expired"}}
    )
    print(f"   Marked {result.modified_count} old opportunities as expired")


def main():
    """Main function to generate all dummy data"""
    print("=" * 60)
    print("🎲 Generating Dummy Data for Demo")
    print("=" * 60)
    
    # Clear old data (optional)
    clear_old_data()
    
    # Generate market prices
    events = generate_dummy_market_prices(num_events=12)
    
    # Generate arbitrage opportunities
    opportunities = generate_dummy_arbitrage_opportunities(events)
    
    print("\n" + "=" * 60)
    print("✅ Dummy data generation complete!")
    print("=" * 60)
    print(f"   Events: {len(events)}")
    print(f"   Opportunities: {len(opportunities)}")
    print("\n💡 You can now:")
    print("   1. Start the dashboard: python3 app.py")
    print("   2. View opportunities at http://localhost:5000")
    print("   3. Run the agent: python3 agent.py (will use dummy data)")


if __name__ == "__main__":
    main()

