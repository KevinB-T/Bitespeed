from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from datetime import datetime

app = Flask(__name__)
CORS(app)

db_config = {
    "host": "dpg-d0rg1gbe5dus73ftsp0g-a",
    "port": 5432,
    "user": "root",
    "password": "C1MeN2WdV7fXW1fe9hZtCWweoZu1sXXX",
    "database": "bitespeeddb_x9nw"
}

def get_db_connection():
    return psycopg2.connect(**db_config)

def create_table_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Contact (
            id SERIAL PRIMARY KEY,
            phoneNumber VARCHAR(20),
            email VARCHAR(255),
            linkedId INTEGER,
            linkPrecedence VARCHAR(10) CHECK (linkPrecedence IN ('primary', 'secondary')) NOT NULL,
            createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deletedAt TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (linkedId) REFERENCES Contact(id)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_table_if_not_exists()

@app.route('/')
def home():
    # Serve your home page html
    return send_from_directory('templates', 'identify.html')

@app.route('/identify', methods=['POST'])
def identify():
    try:
        data = request.get_json()
        email = data.get("email")
        phone = data.get("phoneNumber")

        if not email and not phone:
            return jsonify({"error": "At least one of email or phoneNumber is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch all contacts with matching email or phoneNumber
        cursor.execute("""
            SELECT * FROM Contact
            WHERE email = %s OR phoneNumber = %s
        """, (email, phone))
        contacts = cursor.fetchall()

        if not contacts:
            # No contacts found - insert a new primary contact
            now = datetime.utcnow()
            cursor.execute("""
                INSERT INTO Contact (email, phoneNumber, linkPrecedence, createdAt, updatedAt)
                VALUES (%s, %s, 'primary', %s, %s)
                RETURNING id
            """, (email, phone, now, now))
            new_id = cursor.fetchone()['id']
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                "contact": {
                    "primaryContatctId": new_id,
                    "emails": [email] if email else [],
                    "phoneNumbers": [phone] if phone else [],
                    "secondaryContactIds": []
                }
            })

        # Find the oldest primary contact among all matched contacts (by createdAt)
        primary_contacts = [c for c in contacts if c['linkprecedence'] == 'primary']
        if not primary_contacts:
            # In rare case no primary found, fallback: treat first contact as primary
            primary_contact = contacts[0]
        else:
            primary_contact = min(primary_contacts, key=lambda c: c['createdat'])

        primary_id = primary_contact['id']
        now = datetime.utcnow()

        # Update any other primary contacts to secondary linking to oldest primary
        for contact in contacts:
            if contact['id'] != primary_id:
                # If not already secondary linked to primary_id, update
                if contact['linkprecedence'] != 'secondary' or contact['linkedid'] != primary_id:
                    cursor.execute("""
                        UPDATE Contact
                        SET linkPrecedence = 'secondary',
                            linkedId = %s,
                            updatedAt = %s
                        WHERE id = %s
                    """, (primary_id, now, contact['id']))

        conn.commit()

        # Fetch all related contacts: primary + secondaries linked to primary
        cursor.execute("""
            SELECT * FROM Contact
            WHERE id = %s OR linkedId = %s
        """, (primary_id, primary_id))
        all_related = cursor.fetchall()

        # Aggregate emails, phones, and secondary ids
        emails = list({c['email'] for c in all_related if c['email']})
        phones = list({c['phoneNumber'] for c in all_related if c['phoneNumber']})
        secondary_ids = [c['id'] for c in all_related if c['id'] != primary_id]

        cursor.close()
        conn.close()

        return jsonify({
            "contact": {
                "primaryContatctId": primary_id,
                "emails": emails,
                "phoneNumbers": phones,
                "secondaryContactIds": secondary_ids
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

