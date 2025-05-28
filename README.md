# 🚀 BiteSpeed Identity Reconciliation API

Welcome to the **BiteSpeed Identity Reconciliation** project! This helps to link together customer identities across multiple purchases, ensuring a personalized and consistent shopping experience.

---

## ⚙️ Tech Stack

* **Backend:** Python (Flask)
* **Database:** PostgreSQL (via `psycopg2`)
* **CORS:** Enabled for cross-origin requests
* **API:** RESTful, JSON-based requests & responses

---

## 📦 Features

#### ✅ Create new customer entries if no match exists.
#### ✅ Link new info to existing customers.
#### ✅ Maintain primary and secondary contacts.
#### ✅ Provide consolidated customer data.

---

## 🌐 API Endpoint

### `POST /identify`

#### Request Body

```json
{
  "email": "george@hillvalley.edu",
  "phoneNumber": "717171"
}
```

#### Response

```json
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["george@hillvalley.edu", "biffsucks@hillvalley.edu"],
    "phoneNumbers": ["717171", "919191"],
    "secondaryContactIds": [2]
  }
}
```


## 🌍 Hosted API

The live hosted endpoint is available at:
👉 **[https://bitespeed-backend-g7rd.onrender.com/](https://bitespeed-backend-g7rd.onrender.com/)**


