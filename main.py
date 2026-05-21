from flask import Flask, request, abort
import os
import threading
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv('API_KEY')
EMAIL = os.getenv('EMAIL')
SENDGRID_KEY = os.getenv('SENDGRID_KEY')

def send_via_sendgrid(to, subject, message):
    data = json.dumps({
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Email trimis, status: {response.status}")
    except Exception as e:
        print(f"EROARE SendGrid: {e}")

@app.route("/")
def health():
    return {"status": "ok"}

@app.route("/trimite", methods=["POST"])
def get_data():
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {API_KEY}":
        abort(403)

    data = request.get_json(silent=True)
    if not data:
        return {"error": "Invalid JSON"}, 400

    email_parent = data.get("email")
    email_type = data.get("type")

    if email_type == "daily":
        activities = data.get("activitati", [])
        message = "Copilul a realizat azi: \n- " + "\n- ".join(activities)
        threading.Thread(target=send_via_sendgrid, args=(email_parent, "Raport zilnic activități copil", message)).start()

    elif email_type == "verification":
        code = data.get("code")
        message = f"Codul de verificare al emailului este: {code}."
        threading.Thread(target=send_via_sendgrid, args=(email_parent, "Cod de verificare adresă de email", message)).start()

    elif email_type == "verification_password":
        code = data.get("code")
        message = f"Codul pentru resetarea parolei este: {code}."
        threading.Thread(target=send_via_sendgrid, args=(email_parent, "Cod pentru resetarea parolei", message)).start()

    else:
        abort(403)

    return {"status": "ok"}
def send_via_sendgrid(to, subject, message):
    data = json.dumps({
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Email trimis, status: {response.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"EROARE SendGrid {e.code}: {body}")
    except Exception as e:
        print(f"EROARE generala: {e}")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
