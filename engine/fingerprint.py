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

def get_account_transactions(account_id, days=90):
    """Fetch last N days of transactions for an account"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})-[:SENT]->(t:Transaction)
            WHERE t.timestamp >= $cutoff
            RETURN t.amount as amount,
                   t.timestamp as timestamp,
                   t.transaction_id as txn_id
        """, account_id=account_id, cutoff=cutoff)

        transactions = []
        for record in result:
            transactions.append({
                "amount": record["amount"],
                "timestamp": record["timestamp"],
                "txn_id": record["txn_id"]
            })

        return transactions

def get_counterparty_count(account_id, days=90):
    """How many unique accounts does this account transact with per week"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})-[:SENT]->
                  (t:Transaction)-[:RECEIVED]->(receiver:Account)
            WHERE t.timestamp >= $cutoff
            RETURN count(DISTINCT receiver) as unique_counterparties
        """, account_id=account_id, cutoff=cutoff)

        record = result.single()
        unique = record["unique_counterparties"] if record else 0
        weeks = days / 7
        return round(unique / weeks, 2)

def get_device_count(account_id):
    """How many unique devices does this account use"""
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})-[:USES_DEVICE]->(d:Device)
            RETURN count(d) as device_count
        """, account_id=account_id)

        record = result.single()
        return record["device_count"] if record else 0

def compute_fingerprint(account_id):
    """Compute behavioral fingerprint for one account"""
    transactions = get_account_transactions(account_id)

    if len(transactions) < 3:
        # Not enough history to build fingerprint
        return None

    # --- Hour vector (24 buckets) ---
    hours = []
    for t in transactions:
        try:
            dt = datetime.fromisoformat(str(t["timestamp"]))
            hours.append(dt.hour)
        except:
            hours.append(12)  # default to noon if parse fails

    hour_vector = [0.0] * 24
    for h in hours:
        hour_vector[h] += 1
    total = len(hours)
    hour_vector = [round(c / total, 4) for c in hour_vector]

    # --- Amount stats ---
    amounts = [float(t["amount"]) for t in transactions]
    amount_mean = round(float(np.mean(amounts)), 2)
    amount_std = round(float(np.std(amounts)) + 0.01, 2)  # avoid zero std

    # --- Velocity (transactions per day) ---
    daily_velocity = round(len(transactions) / 90, 4)

    # --- Counterparty weekly average ---
    counterparty_weekly = get_counterparty_count(account_id)

    # --- Device count ---
    device_count = get_device_count(account_id)

    return {
        "account_id": account_id,
        "hour_vector": hour_vector,
        "amount_mean": amount_mean,
        "amount_std": amount_std,
        "daily_velocity": daily_velocity,
        "counterparty_weekly": counterparty_weekly,
        "device_count": device_count,
        "fingerprint_updated_at": datetime.now().isoformat()
    }

def save_fingerprint(fingerprint):
    """Write fingerprint back to the Account node in Neo4j"""
    with driver.session() as session:
        session.run("""
            MATCH (a:Account {account_id: $account_id})
            SET a.hour_vector = $hour_vector,
                a.amount_mean = $amount_mean,
                a.amount_std = $amount_std,
                a.daily_velocity = $daily_velocity,
                a.counterparty_weekly = $counterparty_weekly,
                a.device_count = $device_count,
                a.fingerprint_updated_at = $fingerprint_updated_at
        """, **fingerprint)

def run_all_accounts():
    """Compute and save fingerprints for all accounts"""
    with driver.session() as session:
        result = session.run("MATCH (a:Account) RETURN a.account_id as account_id")
        account_ids = [r["account_id"] for r in result]

    print(f"\n🔍 Computing fingerprints for {len(account_ids)} accounts...\n")

    success = 0
    skipped = 0

    for i, account_id in enumerate(account_ids):
        fingerprint = compute_fingerprint(account_id)
        if fingerprint:
            save_fingerprint(fingerprint)
            success += 1
        else:
            skipped += 1

        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(account_ids)}...")

    print(f"\n✅ Fingerprinting complete")
    print(f"   Computed : {success}")
    print(f"   Skipped  : {skipped} (insufficient history)")

if __name__ == "__main__":
    run_all_accounts()
    driver.close()