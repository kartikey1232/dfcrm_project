from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv("config/.env")

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_driver():
    return GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def create_constraints(driver):
    with driver.session() as session:
        
        # Unique constraints (also auto-create indexes)
        session.run("""
            CREATE CONSTRAINT account_id_unique IF NOT EXISTS
            FOR (a:Account) REQUIRE a.account_id IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS
            FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT device_id_unique IF NOT EXISTS
            FOR (d:Device) REQUIRE d.device_id IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT ip_id_unique IF NOT EXISTS
            FOR (i:IP) REQUIRE i.ip_address IS UNIQUE
        """)

        print("✅ Constraints created")

def create_indexes(driver):
    with driver.session() as session:
        
        # Index for fast zone-based lookups
        session.run("""
            CREATE INDEX account_zone IF NOT EXISTS
            FOR (a:Account) ON (a.zone)
        """)
        
        # Index for fraud flag
        session.run("""
            CREATE INDEX account_fraud IF NOT EXISTS
            FOR (a:Account) ON (a.is_fraud)
        """)
        
        # Index for transaction timestamp
        session.run("""
            CREATE INDEX transaction_timestamp IF NOT EXISTS
            FOR (t:Transaction) ON (t.timestamp)
        """)

        print("✅ Indexes created")

def verify_connection(driver):
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful' as message")
        print(result.single()["message"])

if __name__ == "__main__":
    driver = get_driver()
    verify_connection(driver)
    create_constraints(driver)
    create_indexes(driver)
    driver.close()
    print("\n✅ Schema setup complete")