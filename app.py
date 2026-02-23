import os
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Render provides the DATABASE_URL environment variable automatically
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route('/assign_label', methods=['POST'])
def assign_label():
    # Qualtrics sends data via JSON or Form-Data
    data = request.json or request.form
    netid = data.get('netid', 'Unknown')
    consent = data.get('consent', '')

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Defaults
    response_data = {
        "username": "N/A",
        "password": "N/A",
        "status": "error"
    }

    try:
        # If user consented (e.g., choice contains "Yes")
        if "Yes" in consent:
            # Atomic update: find the first unused row, lock it, and update it in one go.
            # This is 100% thread-safe for 50+ simultaneous users.
            cur.execute("""
                UPDATE credentials 
                SET used = TRUE, netid = %s 
                WHERE id = (
                    SELECT id FROM credentials 
                    WHERE used = FALSE 
                    ORDER BY id ASC 
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING username, password;
            """, (netid,))
            
            row = cur.fetchone()
            if row:
                response_data = {
                    "username": row['username'],
                    "password": row['password'],
                    "status": "success"
                }
            else:
                response_data["status"] = "no_more_labels"
        else:
            response_data["status"] = "no_consent"

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
    finally:
        cur.close()
        conn.close()

    # Qualtrics will read this JSON
    return jsonify(response_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)