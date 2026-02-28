from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import math
from datetime import datetime

load_dotenv("config/.env")

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

# ---------- CONFIG ----------
ALPHA = 0.6   # weight for structural contamination (hop distance)
BETA  = 0.4   # weight for behavioral drift

HOP_SCORES = {
    1: 1.0,
    2: 0.6,
    3: 0.3,
    4: 0.1
}

ZONE_THRESHOLDS = {
    "Critical": 0.75,
    "Exposed":  0.45,
    "Clean":    0.0
}

RECOVERY_LAMBDA = 0.1  # decay rate per day of clean behavior
# ----------------------------

def get_hop_distance(account_id):
    """
    Find shortest hop distance from this account
    to any confirmed fraud account via transactions.
    Returns integer 1-4, or None if no connection found.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH path = shortestPath(
                (a:Account {account_id: $account_id})-[:SENT|RECEIVED*..8]-(f:Account)
            )
            WHERE f.is_fraud = true
            AND a.account_id <> f.account_id
            RETURN length(path) as hops
            ORDER BY hops ASC
            LIMIT 1
        """, account_id=account_id)

        record = result.single()
        if not record:
            return None

        hops = record["hops"]
        # Normalize path length to hop count
        # Each transaction hop = 2 relationships (SENT + RECEIVED)
        hop_count = math.ceil(hops / 2)
        return min(hop_count, 4)

def compute_contamination_score(hop_distance, drift_score):
    """
    Core formula:
    Risk(v) = alpha * ContaminationScore(hops) + beta * DriftScore(v)
    """
    if hop_distance is None:
        structural_score = 0.0
    else:
        structural_score = HOP_SCORES.get(hop_distance, 0.05)

    risk = (ALPHA * structural_score) + (BETA * drift_score)
    return round(min(risk, 1.0), 4)

def classify_zone(risk_score):
    """Classify account into a risk zone based on score"""
    if risk_score >= ZONE_THRESHOLDS["Critical"]:
        return "Critical"
    elif risk_score >= ZONE_THRESHOLDS["Exposed"]:
        return "Exposed"
    else:
        return "Clean"

def apply_recovery(current_contamination, drift_score, days_clean):
    """
    Trust recovery mechanism.
    Account can only recover if BOTH:
    1. Time has passed since last fraud connection
    2. Behavioral drift is low (account acting normally)
    """
    if drift_score > 0.2:
        # Behavior still abnormal - hold contamination, no recovery
        return max(current_contamination * 0.95, 0.3)

    # Exponential decay if behavior is clean
    decayed = current_contamination * math.exp(-RECOVERY_LAMBDA * days_clean)
    return round(max(decayed, 0.0), 4)

def update_account_risk(account_id, drift_score):
    """
    Full pipeline for one account:
    1. Get hop distance to fraud
    2. Compute risk score
    3. Classify zone
    4. Save back to Neo4j
    """
    hop_distance = get_hop_distance(account_id)
    risk_score = compute_contamination_score(hop_distance, drift_score)
    zone = classify_zone(risk_score)

    with driver.session() as session:
        session.run("""
            MATCH (a:Account {account_id: $account_id})
            SET a.contamination_score = $risk_score,
                a.zone = $zone,
                a.hop_distance = $hop_distance,
                a.last_updated = $last_updated
        """, account_id=account_id,
             risk_score=risk_score,
             zone=zone,
             hop_distance=hop_distance,
             last_updated=datetime.now().isoformat())

    return {
        "account_id": account_id,
        "hop_distance": hop_distance,
        "drift_score": drift_score,
        "risk_score": risk_score,
        "zone": zone
    }

def run_full_contamination_pass():
    """
    Run contamination scoring across all non-fraud accounts.
    Uses stored drift_score from each node.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account)
            WHERE a.is_fraud = false
            RETURN a.account_id as account_id,
                   coalesce(a.drift_score, 0.0) as drift_score
        """)
        accounts = [{"account_id": r["account_id"],
                     "drift_score": r["drift_score"]} for r in result]

    print(f"\n🔄 Running contamination pass on {len(accounts)} accounts...\n")

    zone_counts = {"Critical": 0, "Exposed": 0, "Clean": 0}

    for i, acc in enumerate(accounts):
        result = update_account_risk(acc["account_id"], acc["drift_score"])
        zone_counts[result["zone"]] += 1

        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(accounts)}...")

    print(f"\n✅ Contamination pass complete")
    print(f"   🔴 Critical : {zone_counts['Critical']}")
    print(f"   🟡 Exposed  : {zone_counts['Exposed']}")
    print(f"   🟢 Clean    : {zone_counts['Clean']}")

def test_specific_accounts():
    """Test contamination on specific accounts to verify logic"""
    print("\n🧪 Testing contamination on specific accounts...\n")

    # Test a known fraud account neighbor
    test_cases = [
        ("ACC00247", 0.8),   # fraud account itself - high drift
        ("ACC00247", 0.05),  # same account, low drift
    ]

    for account_id, mock_drift in test_cases:
        hop = get_hop_distance(account_id)
        risk = compute_contamination_score(hop, mock_drift)
        zone = classify_zone(risk)
        print(f"Account : {account_id}")
        print(f"Hops    : {hop}")
        print(f"Drift   : {mock_drift}")
        print(f"Risk    : {risk}")
        print(f"Zone    : {zone}")
        print()

def simulate_temporal_risk(steps=10, decay_rate=0.1, signal_probability=0.2, drift_threshold=0.6, accounts=None, plot=False, sample_accounts=5, random_seed=42):
    """
    Time-based risk simulation with decay and re-scoring.
    If accounts is None, pulls all non-fraud accounts from the graph and uses stored drift_score.
    When a new fraud signal appears in a step, recompute risk using DFCRM formula.
    Otherwise, apply multiplicative decay: new_risk = prev_risk * (1 - decay_rate).
    Returns a pandas DataFrame with risk over time for each account.
    """
    import random
    random.seed(random_seed)
    try:
        import pandas as pd
    except Exception:
        pd = None
    results = []
    if accounts is None:
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Account)
                WHERE coalesce(a.is_fraud, false) = false
                RETURN a.account_id as account_id,
                       coalesce(a.drift_score, 0.0) as base_drift
            """)
            accounts = [{"account_id": r["account_id"], "base_drift": r["base_drift"]} for r in result]
        enriched = []
        for acc in accounts:
            hop = get_hop_distance(acc["account_id"])
            base_risk = compute_contamination_score(hop, acc["base_drift"])
            enriched.append({
                "account_id": acc["account_id"],
                "hop_distance": hop,
                "base_drift": acc["base_drift"],
                "risk0": base_risk
            })
        accounts = enriched
    else:
        enriched = []
        for acc in accounts:
            hop = acc.get("hop_distance")
            if hop is None:
                hop = get_hop_distance(acc["account_id"])
            base_drift = acc.get("base_drift", acc.get("drift_score", 0.0))
            base_risk = acc.get("risk0")
            if base_risk is None:
                base_risk = compute_contamination_score(hop, base_drift)
            enriched.append({
                "account_id": acc["account_id"],
                "hop_distance": hop,
                "base_drift": base_drift,
                "risk0": base_risk
            })
        accounts = enriched
    for acc in accounts:
        prev_risk = acc["risk0"]
        results.append({
            "account_id": acc["account_id"],
            "step": 0,
            "risk_score": round(prev_risk, 4),
            "zone": classify_zone(prev_risk),
            "drift_score": acc["base_drift"],
            "signal": True
        })
        for t in range(1, steps + 1):
            base = acc["base_drift"]
            signal = (base >= drift_threshold) or (random.random() < signal_probability)
            if signal:
                drift_t = max(base, min(1.0, base + random.uniform(0.2, 0.6)))
                risk_t = compute_contamination_score(acc["hop_distance"], drift_t)
            else:
                risk_t = prev_risk * (1.0 - decay_rate)
            risk_t = round(risk_t, 4)
            results.append({
                "account_id": acc["account_id"],
                "step": t,
                "risk_score": risk_t,
                "zone": classify_zone(risk_t),
                "drift_score": base,
                "signal": signal
            })
            prev_risk = risk_t
    if plot:
        try:
            import matplotlib.pyplot as plt
            if pd is None:
                raise RuntimeError("pandas not available for plotting")
            df = pd.DataFrame(results)
            unique_accounts = list({r["account_id"] for r in results})
            random.shuffle(unique_accounts)
            to_plot = unique_accounts[:max(1, sample_accounts)]
            plt.figure(figsize=(8, 5))
            for acc_id in to_plot:
                sub = df[df["account_id"] == acc_id]
                plt.plot(sub["step"], sub["risk_score"], label=acc_id)
            plt.axhline(ZONE_THRESHOLDS["Critical"], color="r", linestyle="--", alpha=0.6)
            plt.axhline(ZONE_THRESHOLDS["Exposed"], color="y", linestyle="--", alpha=0.6)
            plt.xlabel("Step")
            plt.ylabel("Risk")
            plt.title("Temporal Risk Evolution")
            plt.legend()
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Plotting skipped: {e}")
    if pd is not None:
        return pd.DataFrame(results)
    return results

if __name__ == "__main__":
    test_specific_accounts()
    run_full_contamination_pass()
    driver.close()
