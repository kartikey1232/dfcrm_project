import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DFCRM Dashboard",
    page_icon="🔴",
    layout="wide"
)

st.title("🔴 DFCRM — Dynamic Fraud Contamination & Recovery Model")
st.markdown("Real-time fraud risk tracking using behavioral fingerprinting and graph contamination")
st.divider()

# ---------- STATS ROW ----------
stats = requests.get(f"{API_URL}/stats").json()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Accounts", stats["total_accounts"])
col2.metric("🔴 Critical", stats["zone_distribution"].get("Critical", 0))
col3.metric("🟡 Exposed", stats["zone_distribution"].get("Exposed", 0))
col4.metric("🟢 Clean", stats["zone_distribution"].get("Clean", 0))

st.divider()

# ---------- TWO COLUMN LAYOUT ----------
left, right = st.columns(2)

# ---------- ACCOUNT LOOKUP ----------
with left:
    st.subheader(" Account Risk Lookup")
    account_id = st.text_input("Enter Account ID", value="ACC00247")

    if st.button("Check Risk"):
        response = requests.get(f"{API_URL}/account/{account_id}")
        if response.status_code == 200:
            data = response.json()

            zone = data.get("zone", "Unknown")
            zone_color = {"Critical": "🔴", "Exposed": "🟡", "Clean": "🟢"}.get(zone, "⚪")

            st.markdown(f"### {zone_color} {zone}")

            c1, c2 = st.columns(2)
            c1.metric("Risk Score", data.get("contamination_score", 0))
            c2.metric("Drift Score", data.get("drift_score", 0))

            c3, c4 = st.columns(2)
            c3.metric("Hop Distance", data.get("hop_distance", "N/A"))
            c4.metric("Is Fraud", "Yes " if data.get("is_fraud") else "No ")

            st.markdown("**Behavioral Fingerprint**")
            st.json({
                "amount_mean": data.get("amount_mean"),
                "daily_velocity": data.get("daily_velocity"),
                "fingerprint_updated_at": data.get("fingerprint_updated_at")
            })

            # Fraud neighbors
            neighbors = requests.get(f"{API_URL}/fraud-neighbors/{account_id}").json()
            if neighbors["count"] > 0:
                st.markdown("**Fraud Neighbors**")
                for n in neighbors["fraud_neighbors"][:5]:
                    st.write(f"→ `{n['fraud_account']}` — {n['hops']} hop(s) away")
        else:
            st.error("Account not found")

# ---------- SIMULATE TRANSACTION ----------
with right:
    st.subheader(" Simulate Real-Time Transaction")
    st.markdown("Send a transaction and watch the risk zone update instantly")

    sim_sender = st.text_input("Sender ID", value="ACC00007")
    sim_receiver = st.text_input("Receiver ID", value="ACC00100")
    sim_amount = st.number_input("Amount ($)", min_value=1.0, value=500.0, step=100.0)
    sim_hour = st.slider("Transaction Hour", 0, 23, 14)

    if st.button("Process Transaction"):
        payload = {
            "sender_id": sim_sender,
            "receiver_id": sim_receiver,
            "amount": sim_amount,
            "hour": sim_hour
        }
        response = requests.post(f"{API_URL}/transaction", json=payload)
        if response.status_code == 200:
            result = response.json()

            zone = result.get("zone", "Unknown")
            zone_color = {"Critical": "🔴", "Exposed": "🟡", "Clean": "🟢"}.get(zone, "⚪")

            st.success("Transaction processed")
            st.markdown(f"### {zone_color} Zone: {zone}")

            r1, r2, r3 = st.columns(3)
            r1.metric("Risk Score", result.get("risk_score"))
            r2.metric("Drift Score", result.get("drift_score"))
            r3.metric("Hops to Fraud", result.get("hop_distance", "N/A"))

            st.markdown("**What this means:**")
            if zone == "Critical":
                st.error(" Block immediately. High structural exposure + abnormal behavior detected.")
            elif zone == "Exposed":
                st.warning(" Increased monitoring. Account is near known fraud or showing drift.")
            else:
                st.success(" Normal behavior. No immediate action required.")
        else:
            st.error(f"Error: {response.text}")

st.divider()

# ---------- ZONE TABLE ----------
st.subheader(" Exposed Accounts")
exposed = requests.get(f"{API_URL}/zone/Exposed").json()
if exposed["accounts"]:
    import pandas as pd
    df = pd.DataFrame(exposed["accounts"])
    st.dataframe(df, use_container_width=True)

st.divider()
st.subheader(" Temporal Risk Simulation")

col_a, col_b, col_c, col_d, col_e = st.columns(5)
steps = col_a.slider("Steps", 5, 20, 10)
decay_rate = col_b.number_input("Decay Rate", min_value=0.01, max_value=0.5, value=0.1, step=0.01, format="%.2f")
signal_prob = col_c.number_input("Signal Probability", min_value=0.0, max_value=1.0, value=0.2, step=0.05, format="%.2f")
drift_thresh = col_d.number_input("Drift Threshold", min_value=0.0, max_value=1.0, value=0.6, step=0.05, format="%.2f")
sample_n = col_e.number_input("Sample Accounts (plot)", min_value=1, max_value=10, value=5, step=1)

if st.button("Run Temporal Simulation"):
    payload = {
        "steps": steps,
        "decay_rate": decay_rate,
        "signal_probability": signal_prob,
        "drift_threshold": drift_thresh,
        "sample_accounts": int(sample_n)
    }
    try:
        resp = requests.post(f"{API_URL}/simulate-temporal", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            avg = data.get("avg_by_step", [])
            import pandas as pd
            avg_df = pd.DataFrame(avg)
            if not avg_df.empty:
                st.markdown("**Average Risk by Step**")
                st.line_chart(avg_df.set_index("step")["risk_score"])
            results = data.get("results", [])
            if results:
                res_df = pd.DataFrame(results)
                ids = res_df["account_id"].unique().tolist()[:sample_n]
                st.markdown("**Sample Account Trajectories**")
                for acc in ids:
                    sub = res_df[res_df["account_id"] == acc].sort_values("step")
                    st.line_chart(sub.set_index("step")["risk_score"], height=200)
            st.success("Simulation complete")
        else:
            st.error(f"Error: {resp.text}")
    except Exception as e:
        st.error(f"Simulation failed: {e}")
