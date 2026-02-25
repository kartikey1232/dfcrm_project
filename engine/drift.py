from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import numpy as np
from datetime import datetime, timedelta

load_dotenv("config/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

def get_fingerprint(account_id):
    """Load stored fingerprint from Neo4j node"""
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})
            RETURN a.hour_vector as hour_vector,
                   a.amount_mean as amount_mean,
                   a.amount_std as amount_std,
                   a.daily_velocity as daily_velocity,
                   a.counterparty_weekly as counterparty_weekly,
                   a.device_count as device_count
        """, account_id=account_id)

        record = result.single()
        if not record or record["amount_mean"] is None:
            return None

        return {
            "hour_vector": record["hour_vector"],
            "amount_mean": record["amount_mean"],
            "amount_std": record["amount_std"],
            "daily_velocity": record["daily_velocity"],
            "counterparty_weekly": record["counterparty_weekly"],
            "device_count": record["device_count"]
        }

def get_recent_transactions(account_id, hours=24):
    """Get transactions from the last N hours"""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})-[:SENT]->(t:Transaction)
            WHERE t.timestamp >= $cutoff
            RETURN t.amount as amount, t.timestamp as timestamp
        """, account_id=account_id, cutoff=cutoff)

        return [{"amount": r["amount"], "timestamp": r["timestamp"]} for r in result]

def compute_time_drift(fingerprint, new_transaction_hour):
    """How unusual is this transaction hour for this account?"""
    hour_vector = fingerprint["hour_vector"]
    if not hour_vector or len(hour_vector) != 24:
        return 0.5  # neutral if no data

    prob = hour_vector[new_transaction_hour]
    # Low probability hour = high drift
    time_drift = 1.0 - prob
    return round(time_drift, 4)

def compute_amount_drift(fingerprint, new_amount):
    """How far is this amount from the account's normal range?"""
    mean = fingerprint["amount_mean"]
    std = fingerprint["amount_std"]

    if std < 1:
        std = 1.0

    z_score = abs(new_amount - mean) / std
    # Normalize: z=0 means no drift, z=5+ means extreme drift
    amount_drift = min(z_score / 5.0, 1.0)
    return round(amount_drift, 4)

def compute_velocity_drift(fingerprint, recent_transaction_count):
    """Is this account transacting much faster than usual?"""
    baseline_daily = fingerprint["daily_velocity"]

    # For low-velocity accounts, single transactions are normal
    # Only flag when recent count is significantly above baseline
    if baseline_daily < 0.5:
        # Account rarely transacts - need at least 3 txns today to flag
        if recent_transaction_count <= 2:
            return 0.0
        else:
            velocity_drift = min((recent_transaction_count - 2) / 8.0, 1.0)
    else:
        ratio = recent_transaction_count / baseline_daily
        velocity_drift = min((ratio - 1) / 4.0, 1.0)
        velocity_drift = max(velocity_drift, 0.0)

    return round(velocity_drift, 4)

def compute_drift_score(account_id, new_transaction):
    """
    Master function: compute overall drift score for an account
    given a new incoming transaction.

    new_transaction = {
        "amount": float,
        "hour": int (0-23),
        "recent_count": int (txns in last 24h including this one)
    }

    Returns drift score between 0.0 (no drift) and 1.0 (extreme drift)
    """
    fingerprint = get_fingerprint(account_id)

    if fingerprint is None:
        # No fingerprint yet, return neutral score
        return 0.5

    time_drift = compute_time_drift(fingerprint, new_transaction["hour"])
    amount_drift = compute_amount_drift(fingerprint, new_transaction["amount"])
    velocity_drift = compute_velocity_drift(fingerprint, new_transaction["recent_count"])

    # Weighted combination
    # Amount drift weighted highest - most reliable signal
    drift_score = (
        0.3 * time_drift +
        0.4 * amount_drift +
        0.3 * velocity_drift
    )

    return round(drift_score, 4)

def save_drift_score(account_id, drift_score):
    """Write drift score back to the account node"""
    with driver.session() as session:
        session.run("""
            MATCH (a:Account {account_id: $account_id})
            SET a.drift_score = $drift_score
        """, account_id=account_id, drift_score=drift_score)

def test_drift_scenarios():
    """
    Test drift engine against real accounts using
    simulated transactions to verify it works correctly
    """
    print("\n🧪 Testing drift engine...\n")

    # Pick a known fraud account
    test_account = "ACC00247"
    fingerprint = get_fingerprint(test_account)

    if not fingerprint:
        print("❌ No fingerprint found")
        return

    print(f"📋 Fingerprint for {test_account}:")
    print(f"   Amount mean : ${fingerprint['amount_mean']}")
    print(f"   Amount std  : ${fingerprint['amount_std']}")
    print(f"   Daily velocity : {fingerprint['daily_velocity']}")
    print()

    # Scenario 1: Normal transaction (should have LOW drift)
    normal_txn = {
        "amount": fingerprint["amount_mean"],  # exactly average amount
        "hour": 14,                             # middle of day
        "recent_count": 1                       # only 1 txn today
    }
    score1 = compute_drift_score(test_account, normal_txn)
    print(f"✅ Scenario 1 - Normal transaction:")
    print(f"   Amount: ${normal_txn['amount']} | Hour: {normal_txn['hour']}:00")
    print(f"   Drift Score: {score1} (expect LOW < 0.3)\n")

    # Scenario 2: Suspicious transaction (should have HIGH drift)
    suspicious_txn = {
        "amount": fingerprint["amount_mean"] * 10,  # 10x normal amount
        "hour": 3,                                    # 3am
        "recent_count": 15                            # 15 txns today vs normal ~0.16
    }
    score2 = compute_drift_score(test_account, suspicious_txn)
    print(f"🚨 Scenario 2 - Suspicious transaction:")
    print(f"   Amount: ${suspicious_txn['amount']} | Hour: {suspicious_txn['hour']}:00")
    print(f"   Drift Score: {score2} (expect HIGH > 0.6)\n")

    # Scenario 3: Moderate drift
    moderate_txn = {
        "amount": fingerprint["amount_mean"] * 3,  # 3x normal
        "hour": 22,                                  # late night
        "recent_count": 4
    }
    score3 = compute_drift_score(test_account, moderate_txn)
    print(f"⚠️  Scenario 3 - Moderate drift:")
    print(f"   Amount: ${moderate_txn['amount']} | Hour: {moderate_txn['hour']}:00")
    print(f"   Drift Score: {score3} (expect MEDIUM 0.3-0.6)\n")

    print("✅ Drift engine test complete")

if __name__ == "__main__":
    test_drift_scenarios()
    driver.close()