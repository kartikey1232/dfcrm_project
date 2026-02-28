from engine.fingerprint import run_all_accounts, driver as fp_driver
from engine.contamination import run_full_contamination_pass, simulate_temporal_risk, driver as cont_driver
from datetime import datetime
import os

def run_pipeline():
    print("=" * 50)
    print("  DFCRM - Full Pipeline Run")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    print("\n📌 Step 1: Recompute behavioral fingerprints")
    run_all_accounts()
    fp_driver.close()

    print("\n📌 Step 2: Run contamination + zone classification")
    run_full_contamination_pass()

    print("\n✅ Pipeline complete. Graph is up to date.")

def run_temporal_simulation():
    print("\n📈 Temporal risk simulation\n")
    steps = int(os.getenv("DFCRM_STEPS", "10"))
    decay_rate = float(os.getenv("DFCRM_DECAY", "0.1"))
    signal_prob = float(os.getenv("DFCRM_SIGNAL_PROB", "0.2"))
    drift_threshold = float(os.getenv("DFCRM_DRIFT_THRESHOLD", "0.6"))
    data = simulate_temporal_risk(
        steps=steps,
        decay_rate=decay_rate,
        signal_probability=signal_prob,
        drift_threshold=drift_threshold,
        plot=os.getenv("DFCRM_PLOT", "0") == "1"
    )
    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            summary = data.groupby("step")["risk_score"].mean().round(4)
            print("\nAvg risk by step:")
            print(summary.to_string())
    except Exception:
        pass

if __name__ == "__main__":
    run_pipeline()
    if os.getenv("DFCRM_RUN_TEMPORAL", "0") == "1":
        run_temporal_simulation()
    try:
        cont_driver.close()
    except Exception:
        pass
