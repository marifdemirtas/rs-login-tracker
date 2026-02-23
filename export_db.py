import psycopg2
import csv

DB_URL = "your_external_database_url_here"

def export():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT username, password, condition, netid, used FROM credentials WHERE used = TRUE")
    rows = cur.fetchall()
    
    with open('results_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'password', 'condition', 'netid', 'used'])
        writer.writerows(rows)
        
    print(f"Exported {len(rows)} assigned rows to results_export.csv")
    cur.close()
    conn.close()

if __name__ == "__main__":
    export()