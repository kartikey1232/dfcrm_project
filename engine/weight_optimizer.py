import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

def optimize_weights(accounts):
    """
    Tests every alpha/beta combination in 0.1 increments
    and finds which weights produce the best F1 score.
    """
    results = []

    # Test all combinations where alpha + beta = 1
    for alpha in np.arange(0.1, 1.0, 0.1):
        beta = round(1.0 - alpha, 1)

        predictions = []
        actuals = []

        for acc in accounts:
            structural = acc.get("contamination_score", 0) or 0
            drift = acc.get("drift_score", 0) or 0
            is_fraud = acc.get("is_fraud", False)

            risk = alpha * structural + beta * drift
            predicted = 1 if risk >= 0.75 else 0
            actual = 1 if is_fraud else 0

            predictions.append(predicted)
            actuals.append(actual)

        if sum(predictions) > 0:
            f1 = f1_score(actuals, predictions, zero_division=0)
            precision = sum(1 for p, a in zip(predictions, actuals) if p == 1 and a == 1) / max(sum(predictions), 1)
            recall = sum(1 for p, a in zip(predictions, actuals) if p == 1 and a == 1) / max(sum(actuals), 1)

            results.append({
                "alpha": round(alpha, 1),
                "beta": round(beta, 1),
                "f1_score": round(f1, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4)
            })

    df = pd.DataFrame(results).sort_values("f1_score", ascending=False)
    best = df.iloc[0]

    print("\n📊 Weight Optimization Results")
    print("=" * 50)
    print(df.to_string(index=False))
    print("\n✅ Best weights found:")
    print(f"   Alpha (structural) = {best['alpha']}")
    print(f"   Beta  (behavioral) = {best['beta']}")
    print(f"   F1 Score           = {best['f1_score']}")
    print(f"\n   Current weights (0.6 / 0.4) rank: "
          f"#{df[df['alpha']==0.6].index[0]+1 if len(df[df['alpha']==0.6])>0 else 'N/A'} out of {len(df)}")

    return df, best

if __name__ == "__main__":
    from neo4j import GraphDatabase
    from dotenv import load_dotenv
    import os

    load_dotenv("config/.env")
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account)
            RETURN a.account_id as account_id,
                   a.is_fraud as is_fraud,
                   coalesce(a.contamination_score, 0.0) as contamination_score,
                   coalesce(a.drift_score, 0.0) as drift_score
        """)
        accounts = [dict(r) for r in result]

    driver.close()
    optimize_weights(accounts)