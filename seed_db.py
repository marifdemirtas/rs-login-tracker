import psycopg2
import csv
import os

# Get this from your Render Dashboard (External Database URL)
DB_URL = "your_external_database_url_here"

def seed():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Create table based on your CSV structure
    cur.execute("DROP TABLE IF EXISTS credentials;")
    cur.execute("""
        CREATE TABLE credentials (
            id SERIAL PRIMARY KEY,
            username TEXT,
            password TEXT,
            condition TEXT,
            used BOOLEAN DEFAULT FALSE,
            netid TEXT
        );
    """)

    # Load your local CSV (ensure it's named 'labels.csv')
    with open('labels.csv', 'r') as f:
        reader = csv.DictReader(f) # Assumes header: username,password,condition,used
        for row in reader:
            cur.execute("""
                INSERT INTO credentials (username, password, condition, used) 
                VALUES (%s, %s, %s, %s)
            """, (row['username'], row['password'], row['condition'], row['used'].lower() == 'true'))

    conn.commit()
    print("Database seeded successfully!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    seed()