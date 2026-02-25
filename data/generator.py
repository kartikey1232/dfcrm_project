from neo4j import GraphDatabase
from faker import Faker
from dotenv import load_dotenv
import os
import random
import uuid
from datetime import datetime, timedelta

load_dotenv("config/.env")

fake = Faker()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

# ---------- CONFIG ----------
NUM_ACCOUNTS = 500
NUM_DEVICES = 80
NUM_IPS = 100
NUM_TRANSACTIONS = 5000
FRAUD_ACCOUNTS = 10
START_DATE = datetime.now() - timedelta(days=90)
# ----------------------------

def random_timestamp():
    return START_DATE + timedelta(
        seconds=random.randint(0, 90 * 24 * 3600)
    )

def create_accounts(session, account_ids):
    for acc_id in account_ids:
        session.run("""
            MERGE (a:Account {account_id: $account_id})
            SET a.name = $name,
                a.zone = 'Clean',
                a.is_fraud = false,
                a.contamination_score = 0.0,
                a.drift_score = 0.0,
                a.fingerprint_updated_at = null
        """, account_id=acc_id, name=fake.name())
    print(f"✅ {len(account_ids)} accounts created")

def mark_fraud_accounts(session, fraud_ids):
    for acc_id in fraud_ids:
        session.run("""
            MATCH (a:Account {account_id: $account_id})
            SET a.is_fraud = true,
                a.zone = 'Critical',
                a.contamination_score = 1.0
        """, account_id=acc_id)
    print(f"✅ {len(fraud_ids)} accounts marked as fraud")

def create_devices(session, device_ids):
    for dev_id in device_ids:
        session.run("""
            MERGE (d:Device {device_id: $device_id})
            SET d.type = $type
        """, device_id=dev_id, type=random.choice(["mobile", "desktop", "tablet"]))
    print(f"✅ {len(device_ids)} devices created")

def create_ips(session, ip_list):
    for ip in ip_list:
        session.run("""
            MERGE (i:IP {ip_address: $ip_address})
        """, ip_address=ip)
    print(f"✅ {len(ip_list)} IP nodes created")

def link_accounts_to_devices(session, account_ids, device_ids):
    for acc_id in account_ids:
        # Each account uses 1-3 devices
        devices = random.sample(device_ids, k=random.randint(1, 3))
        for dev_id in devices:
            session.run("""
                MATCH (a:Account {account_id: $account_id})
                MATCH (d:Device {device_id: $device_id})
                MERGE (a)-[:USES_DEVICE]->(d)
            """, account_id=acc_id, device_id=dev_id)
    print("✅ Accounts linked to devices")

def link_accounts_to_ips(session, account_ids, ip_list):
    for acc_id in account_ids:
        ips = random.sample(ip_list, k=random.randint(1, 2))
        for ip in ips:
            session.run("""
                MATCH (a:Account {account_id: $account_id})
                MATCH (i:IP {ip_address: $ip_address})
                MERGE (a)-[:USES_IP]->(i)
            """, account_id=acc_id, ip_address=ip)
    print("✅ Accounts linked to IPs")

def create_transactions(session, account_ids):
    for _ in range(NUM_TRANSACTIONS):
        sender = random.choice(account_ids)
        receiver = random.choice(account_ids)
        if sender == receiver:
            continue

        txn_id = str(uuid.uuid4())
        amount = round(random.uniform(10, 15000), 2)
        timestamp = random_timestamp()

        session.run("""
            MATCH (sender:Account {account_id: $sender_id})
            MATCH (receiver:Account {account_id: $receiver_id})
            CREATE (t:Transaction {
                transaction_id: $txn_id,
                amount: $amount,
                timestamp: $timestamp,
                flagged: false
            })
            CREATE (sender)-[:SENT]->(t)
            CREATE (t)-[:RECEIVED]->(receiver)
        """, sender_id=sender, receiver_id=receiver,
             txn_id=txn_id, amount=amount,
             timestamp=timestamp.isoformat())

    print(f"✅ {NUM_TRANSACTIONS} transactions created")

def inject_fraud_patterns(session, fraud_ids, account_ids):
    normal_ids = [a for a in account_ids if a not in fraud_ids]

    # Pattern 1: Circular money flow (3-hop rings)
    for i in range(3):
        a, b, c = random.sample(fraud_ids, 3)
        for sender, receiver in [(a, b), (b, c), (c, a)]:
            txn_id = str(uuid.uuid4())
            session.run("""
                MATCH (s:Account {account_id: $sender_id})
                MATCH (r:Account {account_id: $receiver_id})
                CREATE (t:Transaction {
                    transaction_id: $txn_id,
                    amount: $amount,
                    timestamp: $timestamp,
                    flagged: true
                })
                CREATE (s)-[:SENT]->(t)
                CREATE (t)-[:RECEIVED]->(r)
            """, sender_id=sender, receiver_id=receiver,
                 txn_id=txn_id,
                 amount=round(random.uniform(8000, 15000), 2),
                 timestamp=random_timestamp().isoformat())

    # Pattern 2: Fraud accounts connected to normal accounts (contamination spread)
    for fraud_id in fraud_ids:
        targets = random.sample(normal_ids, k=random.randint(2, 5))
        for target in targets:
            txn_id = str(uuid.uuid4())
            session.run("""
                MATCH (s:Account {account_id: $sender_id})
                MATCH (r:Account {account_id: $receiver_id})
                CREATE (t:Transaction {
                    transaction_id: $txn_id,
                    amount: $amount,
                    timestamp: $timestamp,
                    flagged: false
                })
                CREATE (s)-[:SENT]->(t)
                CREATE (t)-[:RECEIVED]->(r)
            """, sender_id=fraud_id, receiver_id=target,
                 txn_id=txn_id,
                 amount=round(random.uniform(500, 5000), 2),
                 timestamp=random_timestamp().isoformat())

    print("✅ Fraud patterns injected")

def run():
    account_ids = [f"ACC{str(i).zfill(5)}" for i in range(NUM_ACCOUNTS)]
    device_ids = [f"DEV{str(i).zfill(4)}" for i in range(NUM_DEVICES)]
    ip_list = [fake.ipv4() for _ in range(NUM_IPS)]
    fraud_ids = random.sample(account_ids, FRAUD_ACCOUNTS)

    print("\n🚀 Starting data generation...\n")

    with driver.session() as session:
        create_accounts(session, account_ids)
        mark_fraud_accounts(session, fraud_ids)
        create_devices(session, device_ids)
        create_ips(session, ip_list)
        link_accounts_to_devices(session, account_ids, device_ids)
        link_accounts_to_ips(session, account_ids, ip_list)
        create_transactions(session, account_ids)
        inject_fraud_patterns(session, fraud_ids, account_ids)

    print(f"\n✅ Data generation complete")
    print(f"   Accounts : {NUM_ACCOUNTS}")
    print(f"   Fraud    : {FRAUD_ACCOUNTS}")
    print(f"   Devices  : {NUM_DEVICES}")
    print(f"   IPs      : {NUM_IPS}")
    print(f"   Txns     : {NUM_TRANSACTIONS}+")
    print(f"   Fraud IDs: {fraud_ids}")

    driver.close()

if __name__ == "__main__":
    run()