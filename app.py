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
            linkedId INTEGER REFERENCES Contact(id),
            linkPrecedence VARCHAR(10) CHECK (linkPrecedence IN ('primary', 'secondary')) NOT NULL,
            createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deletedAt TIMESTAMP DEFAULT NULL
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_table_if_not_exists()

@app.route('/')
def home():
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

        cursor.execute("""
            SELECT * FROM Contact
            WHERE email = %s OR phoneNumber = %s
        """, (email, phone))
        contacts = cursor.fetchall()

        now = datetime.utcnow()

        if not contacts:
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

        has_new_info = (
            (email and email not in emails) or
            (phone and phone not in phones)
        )

        if has_new_info:
            cursor.execute("""
                INSERT INTO Contact (email, phoneNumber, linkPrecedence, linkedId, createdAt, updatedAt)
                VALUES (%s, %s, 'secondary', %s, %s, %s)
                RETURNING id
            """, (email, phone, primary_id, now, now))
            new_secondary_id = cursor.fetchone()['id']
            conn.commit()
            secondary_ids.append(new_secondary_id)
            if email:
                emails.add(email)
            if phone:
                phones.add(phone)

        final_emails = list(emails)
        final_phones = list(phones)
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
    app.run(host='0.0.0.0', port=5432, debug=True)
