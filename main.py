from flask import Flask, request, abort
import os
import smtplib
import threading
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv('API_KEY')
EMAIL = os.getenv('EMAIL')
EMAIL_PASS = os.getenv('EMAIL_PASS')

def send_email(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Raport zilnic activități copil'
    msg['From'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

def send_verification_email(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Cod de verificare adresă de email'
    msg['From'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

def send_verification_password(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Cod pentru resetarea parolei'
    msg['From'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

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
        message = "Copilul a realizat azi: " + "\n-" + "\n- ".join(activities)
        threading.Thread(target=send_email, args=(email_parent, message)).start()

    elif email_type == "verification":
        code = data.get("code")
        message = f"Codul de verificare al emailului este: {code}."
        threading.Thread(target=send_verification_email, args=(email_parent, message)).start()

    elif email_type == "verification_password":
        code = data.get("code")
        message = f"Codul pentru resetarea parolei este: {code}."
        threading.Thread(target=send_verification_password, args=(email_parent, message)).start()

    else:
        abort(403)

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
