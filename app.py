from flask import Flask, request, jsonify
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

        # Step 1: Fetch all contacts with matching email or phoneNumber
        cursor.execute("""
            SELECT * FROM Contact
            WHERE email = %s OR phoneNumber = %s
        """, (email, phone))
        contacts = cursor.fetchall()

        if not contacts:
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

        all_contact_ids = {c['id'] for c in contacts}
        emails = set(c['email'] for c in contacts if c['email'])
        phones = set(c['phoneNumber'] for c in contacts if c['phoneNumber'])

        primary_contact = min(contacts, key=lambda c: c['createdat'])
        primary_id = primary_contact['id']

        secondary_ids = []
        now = datetime.utcnow()

        for contact in contacts:
            if contact['id'] != primary_id:
                if contact['linkprecedence'] != 'secondary' or contact['linkedid'] != primary_id:
                    cursor.execute("""
                        UPDATE Contact
                        SET linkPrecedence = 'secondary',
                            linkedId = %s,
                            updatedAt = %s
                        WHERE id = %s
                    """, (primary_id, now, contact['id']))
                secondary_ids.append(contact['id'])

        conn.commit()

        final_emails = list({c['email'] for c in contacts if c['email']})
        final_phones = list({c['phoneNumber'] for c in contacts if c['phoneNumber']})

        final_emails.sort(key=lambda x: x != primary_contact['email'])
        final_phones.sort(key=lambda x: x != primary_contact['phoneNumber'])

        cursor.close()
        conn.close()

        return jsonify({
            "contact": {
                "primaryContatctId": primary_id,
                "emails": final_emails,
                "phoneNumbers": final_phones,
                "secondaryContactIds": secondary_ids
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

