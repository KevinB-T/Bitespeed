from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Kvn@852456",
    "database": "bitespeed"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/identify', methods=['POST'])
def identify():
    try:
        data = request.get_json()
        email = data.get("email")
        phone = data.get("phoneNumber")

        if not email and not phone:
            return jsonify({"error": "At least one of email or phoneNumber is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Step 1: Fetch all contacts with matching email or phoneNumber
        cursor.execute("""
            SELECT * FROM Contact
            WHERE email = %s OR phoneNumber = %s
        """, (email, phone))
        contacts = cursor.fetchall()

        if not contacts:
            # No matches, create new primary
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO Contact (email, phoneNumber, linkPrecedence, createdAt, updatedAt)
                VALUES (%s, %s, 'primary', %s, %s)
            """, (email, phone, now, now))
            conn.commit()
            new_id = cursor.lastrowid
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

        # Step 2: Multiple matching contacts
        # Build full list of linked contacts (traversal not needed as per PDF rules: match by email or phone)
        all_contact_ids = {c['id'] for c in contacts}
        emails = set(c['email'] for c in contacts if c['email'])
        phones = set(c['phoneNumber'] for c in contacts if c['phoneNumber'])

        # Step 3: Determine the primary (oldest one)
        primary_contact = min(contacts, key=lambda c: c['createdAt'])
        primary_id = primary_contact['id']

        secondary_ids = []
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # Step 4: Update all others (even primaries) to secondary if not already
        for contact in contacts:
            if contact['id'] != primary_id:
                if contact['linkPrecedence'] != 'secondary' or contact['linkedId'] != primary_id:
                    cursor.execute("""
                        UPDATE Contact
                        SET linkPrecedence = 'secondary',
                            linkedId = %s,
                            updatedAt = %s
                        WHERE id = %s
                    """, (primary_id, now, contact['id']))
                secondary_ids.append(contact['id'])

        conn.commit()

        # Step 5: Collect updated full contact info
        final_emails = list({c['email'] for c in contacts if c['email']})
        final_phones = list({c['phoneNumber'] for c in contacts if c['phoneNumber']})

        # Ensure the primary's values are first in order
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
    app.run(port=5000, debug=True)
