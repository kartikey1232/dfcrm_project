from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import math

load_dotenv("config/.env")
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

def simulate_recovery(account_id, days=30):
    print(f"\n🔄 Trust Recovery Simulation — {account_id}")
    print(f"   Simulating {days} days of clean behavior")
    print("=" * 55)
    print(f"{'Day':<6} {'Contamination':<16} {'Drift':<10} {'Zone':<12}")
    print("-" * 55)

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $id})
            RETURN a.contamination_score as contamination,
                   a.drift_score as drift,
                   a.zone as zone
        """, id=account_id)
        record = result.single()
        if not record:
            print("Account not found")
            return

    contamination = record["contamination"] or 0.6
    drift = 0.05  # simulate clean behavior

    zone_history = []

    for day in range(0, days + 1, 3):
        if drift < 0.2:
            new_contamination = contamination * math.exp(-0.1 * day)
        else:
            new_contamination = max(contamination * 0.95, 0.3)

        new_contamination = round(max(new_contamination, 0.0), 4)

        if new_contamination >= 0.75:
            zone = "Critical 🔴"
        elif new_contamination >= 0.45:
            zone = "Exposed  🟡"
        else:
            zone = "Clean    🟢"

        zone_history.append({"day": day, "contamination": new_contamination, "zone": zone})
        print(f"Day {day:<4} {new_contamination:<16.4f} {drift:<10.4f} {zone}")

    clean_day = next((z["day"] for z in zone_history if "Clean" in z["zone"]), None)
    if clean_day:
        print(f"\n✅ Account recovered to Clean zone on Day {clean_day}")
    else:
        print(f"\n⚠️  Account did not fully recover within {days} days")

    print("\n📋 Recovery requires BOTH conditions:")
    print("   1. Time passing (exponential decay)")
    print("   2. Drift staying below 0.2 (normal behavior)")

    return zone_history

def simulate_no_recovery(account_id, days=30):
    print(f"\n❌ No Recovery Scenario — behavior stays abnormal")
    print("=" * 55)
    print(f"{'Day':<6} {'Contamination':<16} {'Drift':<10} {'Zone'}")
    print("-" * 55)

    contamination = 0.6
    for day in range(0, days + 1, 3):
        new_contamination = round(max(contamination * 0.95, 0.3), 4)
        zone = "Exposed  🟡" if new_contamination >= 0.45 else "Clean    🟢"
        print(f"Day {day:<4} {new_contamination:<16.4f} {'0.75 (high)':<10} {zone}")

    print("\n❌ Account stuck in Exposed — abnormal behavior blocks recovery")

if __name__ == "__main__":
    # Use a known exposed account
    simulate_recovery("ACC00548", days=30)
    simulate_no_recovery("ACC00548", days=30)
    driver.close()