from flask import Flask, request, abort
# flask => se ocupa cu gestionarea datelor pe server
# request => este obiectul ce reprezinta cererea HTTP facuta din Godot
# abort => opreste executia in caz ca apare ceva eroare
import os
import smtplib
# smtplib => asigura trimiterea emailului
# Simple Mail Transfer Protocol
from email.mime.text import MIMEText
# obiect ce contine continutul mailului, mime => mai multe elemente gen imagini, pdf, etc
# text este practic pentru ca trimitem text
# MimeText transforma textul in obiect pe care il poate trimite smtplib
from dotenv import load_dotenv
# dontev se ocupa cu citirea datelor din .env => environmental variables
# env => securitate, variabilele nu sunt in cod
load_dotenv()
app = Flask(__name__)
# intializeaza serverul
API_KEY = os.getenv('API_KEY')
EMAIL = os.getenv('EMAIL')
EMAIL_PASS = os.getenv('EMAIL_PASS')
# preia date din env
def send_email(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Raport zilnic activități copil'
    msg['From'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        # seteaza canalul la sll=> securizat
        # portul si host-ul sunt din reference de la gmail
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

def send_verification_email(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Cod de verificare adresă de email'
    msg['from'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

def send_verification_password(to, message):
    msg = MIMEText(message)
    msg['Subject'] = 'Cod pentru resetarea parolei'
    msg['from'] = EMAIL
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL, EMAIL_PASS)
        server.send_message(msg)

@app.route("/trimite", methods=["POST"])
# atunci cand requestul este dat in zona /trimite din url, se permite doat Post
# restul de tip get etc nu sunt acceptate de server => SECURITATE
def get_data():
    # headers sunt metadata, chestii suplimentare trimise de cine face cererea http
    # in cazul acest godot, arata cine ce vrea sa faca pe server
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {API_KEY}":
        abort(403)
    # se verifica o cheie => SECURITATE
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Invalid JSON"}, 400
    # extrage data transmisa in godot
    email_parent = data.get("email")
    email_type = data.get("type")
    if email_type == "daily":
        activities = data.get("activitati", [])
        message = "Copilul a realizat azi: " + "\n-" + "\n- ".join(activities)
        send_email(email_parent, message)
    elif email_type == "verification":
        code = data.get("code")
        message = f"Codul de verificare al emailului este: {code}."
        send_verification_email(email_parent, message)
    elif email_type == "verification_password":
        code = data.get("code")
        message = f"Codul pentru resetarea parolei este: {code}."
        send_verification_password(email_parent, message)
    else:
        abort(403)
    return {"status": "ok"}
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
