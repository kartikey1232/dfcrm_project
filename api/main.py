from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from datetime import datetime
from engine.drift import compute_drift_score, save_drift_score
from engine.contamination import update_account_risk

load_dotenv("config/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

app = FastAPI(
    title="DFCRM - Dynamic Fraud Contamination & Recovery Model",
    description="Real-time fraud risk scoring using behavioral fingerprinting and graph contamination",
    version="1.0.0"
)

# ---------- REQUEST MODELS ----------

class TransactionEvent(BaseModel):
    sender_id: str
    receiver_id: str
    amount: float
    hour: int  # 0-23

# ---------- ENDPOINTS ----------

@app.get("/")
def root():
    return {"message": "DFCRM API is running", "version": "1.0.0"}

@app.get("/account/{account_id}")
def get_account(account_id: str):
    """Get full risk profile for an account"""
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})
            RETURN a.account_id as account_id,
                   a.name as name,
                   a.zone as zone,
                   a.is_fraud as is_fraud,
                   a.contamination_score as contamination_score,
                   a.drift_score as drift_score,
                   a.hop_distance as hop_distance,
                   a.amount_mean as amount_mean,
                   a.daily_velocity as daily_velocity,
                   a.fingerprint_updated_at as fingerprint_updated_at,
                   a.last_updated as last_updated
        """, account_id=account_id)

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Account not found")

        return dict(record)

@app.get("/zone/{zone}")
def get_accounts_by_zone(zone: str):
    """Get all accounts in a specific zone: Critical, Exposed, or Clean"""
    if zone not in ["Critical", "Exposed", "Clean"]:
        raise HTTPException(status_code=400, detail="Zone must be Critical, Exposed, or Clean")

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {zone: $zone})
            RETURN a.account_id as account_id,
                   a.name as name,
                   a.contamination_score as contamination_score,
                   a.drift_score as drift_score,
                   a.hop_distance as hop_distance
            ORDER BY a.contamination_score DESC
            LIMIT 100
        """, zone=zone)

        accounts = [dict(r) for r in result]
        return {"zone": zone, "count": len(accounts), "accounts": accounts}

@app.get("/stats")
def get_stats():
    """Get zone distribution across the entire network"""
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account)
            RETURN a.zone as zone, count(a) as count
        """)
        zones = {r["zone"]: r["count"] for r in result}

        fraud_result = session.run("""
            MATCH (a:Account {is_fraud: true})
            RETURN count(a) as fraud_count
        """)
        fraud_count = fraud_result.single()["fraud_count"]

    return {
        "total_accounts": sum(zones.values()),
        "confirmed_fraud": fraud_count,
        "zone_distribution": zones,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/transaction")
def process_transaction(event: TransactionEvent):
    """
    Process a new transaction in real time.
    Updates drift score and risk zone for the sender.
    """
    # Verify sender exists
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})
            RETURN count(a) as exists
        """, account_id=event.sender_id)
        if result.single()["exists"] == 0:
            raise HTTPException(status_code=404, detail="Sender account not found")

        # Get recent transaction count for velocity
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})-[:SENT]->(t:Transaction)
            WHERE t.timestamp >= $cutoff
            RETURN count(t) as recent_count
        """, account_id=event.sender_id,
             cutoff=(datetime.now().replace(hour=0, minute=0)).isoformat())
        recent_count = result.single()["recent_count"] + 1

    # Compute drift for sender
    new_txn = {
        "amount": event.amount,
        "hour": event.hour,
        "recent_count": recent_count
    }

    drift_score = compute_drift_score(event.sender_id, new_txn)
    save_drift_score(event.sender_id, drift_score)

    # Recompute full risk with new drift
    risk_result = update_account_risk(event.sender_id, drift_score)

    return {
        "sender_id": event.sender_id,
        "receiver_id": event.receiver_id,
        "amount": event.amount,
        "drift_score": drift_score,
        "risk_score": risk_result["risk_score"],
        "zone": risk_result["zone"],
        "hop_distance": risk_result["hop_distance"],
        "processed_at": datetime.now().isoformat()
    }

@app.get("/fraud-neighbors/{account_id}")
def get_fraud_neighbors(account_id: str):
    """Find all fraud accounts within 3 hops of this account"""
    with driver.session() as session:
        result = session.run("""
            MATCH path = shortestPath(
                (a:Account {account_id: $account_id})-[:SENT|RECEIVED*..6]-(f:Account)
            )
            WHERE f.is_fraud = true
            AND a.account_id <> f.account_id
            RETURN f.account_id as fraud_account,
                   length(path) as path_length
            ORDER BY path_length ASC
            LIMIT 10
        """, account_id=account_id)

        neighbors = [{"fraud_account": r["fraud_account"],
                      "hops": r["path_length"] // 2} for r in result]

    return {
        "account_id": account_id,
        "fraud_neighbors": neighbors,
        "count": len(neighbors)
    }