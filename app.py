import os
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Render provides the DATABASE_URL environment variable automatically
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route('/ping', methods=['GET'])
def health():
    return "Server is live!", 200

@app.route('/assign_label', methods=['POST'])
def assign_label():
    data = request.json or request.form
    netid = data.get('netid', 'Unknown')
    consent = data.get('consent', '')

    app.logger.info(f"Incoming request -> NetID: {netid} | Consent: {consent}")

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Default response if something goes wrong or no credentials exist
    response_data = {
        "username": "N/A",
        "password": "N/A",
        "status": "error"
    }

    try:
        if "Yes" in consent:
            # Secure, concurrent assignment from yes_labels
            cur.execute("""
                UPDATE yes_labels 
                SET used = TRUE, netid = %s 
                WHERE id = (
                    SELECT id FROM yes_labels 
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
                response_data["status"] = "no_yes_labels_available"
                
        elif "No" in consent:
            # Random assignment from no_labels (no locking, no recording netid)
            # cur.execute("SELECT username, password FROM no_labels ORDER BY RANDOM() LIMIT 1;")

            cur.execute("""
                UPDATE no_labels 
                SET used = TRUE
                WHERE id = (
                    SELECT id FROM no_labels 
                    WHERE used = FALSE 
                    ORDER BY id ASC 
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING username, password;
            """)

            row = cur.fetchone()
            if row:
                response_data = {
                    "username": row['username'],
                    "password": row['password'],
                    "status": "success_no_consent"
                }
            else:
                app.logger.warning(f"WARNING: Ran out of 'No' labels for NetID: {netid}")
                response_data["status"] = "no_no_labels_available"
        else:
            app.logger.warning(f"WARNING: Unrecognized consent value '{consent}' for NetID: {netid}")
            response_data["status"] = "unrecognized_consent_value"

        conn.commit()
    except Exception as e:
        conn.rollback()
        app.logger.error(f"DATABASE ERROR for NetID {netid}: {str(e)}")
    finally:
        cur.close()
        conn.close()

    return jsonify(response_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)