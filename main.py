from engine.fingerprint import run_all_accounts, driver as fp_driver
from engine.contamination import run_full_contamination_pass, driver as cont_driver
from datetime import datetime

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
    cont_driver.close()

    print("\n✅ Pipeline complete. Graph is up to date.")

if __name__ == "__main__":
    run_pipeline()