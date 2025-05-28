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
            WHERE (email = %s AND email IS NOT NULL)
               OR (phoneNumber = %s AND phoneNumber IS NOT NULL)
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

        # Determine primary contact
        primary_contact = None
        for c in contacts:
            if c['linkprecedence'] == 'primary':
                primary_contact = c
                break
        if not primary_contact:
            primary_contact = min(contacts, key=lambda x: x['createdat'])

        primary_id = primary_contact['id']

        secondary_ids = []
        for c in contacts:
            if c['id'] != primary_id:
                if c['linkprecedence'] != 'secondary' or c['linkedid'] != primary_id:
                    cursor.execute("""
                        UPDATE Contact
                        SET linkPrecedence = 'secondary',
                            linkedId = %s,
                            updatedAt = %s
                        WHERE id = %s
                    """, (primary_id, now, c['id']))
                secondary_ids.append(c['id'])
        conn.commit()

        # Check if new info provided (new email or phone)
        existing_emails = {c['email'] for c in contacts if c['email']}
        existing_phones = {c['phonenumber'] for c in contacts if c['phonenumber']}

        has_new_info = (
            (email and email not in existing_emails) or
            (phone and phone not in existing_phones)
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
                existing_emails.add(email)
            if phone:
                existing_phones.add(phone)

        final_emails = list(existing_emails)
        final_phones = list(existing_phones)

        final_emails.sort(key=lambda x: x != primary_contact['email'])
        final_phones.sort(key=lambda x: x != primary_contact['phonenumber'])

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
