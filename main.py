import os
import threading
import smtplib
from email.mime.text import MIMEText
from flask import Flask
from supabase import create_client, Client
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configurare
load_dotenv()
app = Flask(__name__)
scheduler = APScheduler()
# Variabile de mediu
EMAIL_SENDER = os.getenv("EMAIL")  # Adresa ta de Gmail
EMAIL_PASS = os.getenv("EMAIL_PASS")  # Parola de aplicație Google (16 caractere)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
ACTIVITIES = ["trezire", "ex1", "masa_dimineata", "masa_pranz", "ex2", "masa_seara", "culcare"]


def send_via_smtp(to, subject, message):
    """Trimite email folosind serverul SMTP Gmail"""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = to

    try:
        # Ne conectăm la serverul Gmail pe portul 465 (SSL)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASS)
            server.send_message(msg)
            print(f"Email trimis cu succes la {to}")
    except Exception as e:
        print(f"Eroare SMTP către {to}: {e}")


def get_parent_email(parent_id):
    try:
        user_data = supabase.auth.admin.get_user_by_id(parent_id)
        return user_data.user.email
    except Exception as e:
        print(f"Eroare Supabase Auth: {e}")
        return None


def check_midtime_alerts():
    children_res = supabase.table("children").select("*").execute()
    progres_res = supabase.table("progres_copil").select("*").execute()
    progres_dict = {p['connection_code']: p for p in progres_res.data}
    now = datetime.now()

    for child in children_res.data:
        code = child.get("connection_code")
        parent_id = child.get("parent_id")
        child_progres = progres_dict.get(code)

        if not child_progres or not parent_id:
            continue

        email_parinte = get_parent_email(parent_id)
        if not email_parinte:
            continue

        for activity in ACTIVITIES:
            time_val = child.get(activity)
            if not time_val: continue

            try:
                start_time = datetime.strptime(time_val[:5], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                alert_time = start_time + timedelta(minutes=4)
                end_interval = start_time + timedelta(minutes=7)

                if alert_time <= now < end_interval:
                    if child_progres.get(activity) == 0:
                        nume_afisare = {
                            "trezire": "pregatirea de dimineata",
                            "ex1": "exercitiile de dimineata",
                            "masa_dimineata": "masa de dimineata",
                            "masa_pranz": "masa de pranz",
                            "ex2": "exercitiile de dupa amiaza",
                            "masa_seara": "masa de seara",
                            "culcare": "pregatirea de somn"
                        }.get(activity, activity)

                        mesaj = f"Copilul inca nu a inceput {nume_afisare}, activitate setata pentru ora {time_val[:5]}."
                        # Folosim funcția SMTP în thread
                        threading.Thread(target=send_via_smtp, args=(email_parinte, "Alertă activitate", mesaj)).start()
            except:
                continue

        time_verificare = child.get("verificare")
        if time_verificare:
            try:
                v_start = datetime.strptime(time_verificare[:5], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                v_end = v_start + timedelta(minutes=7)

                if v_start <= now < v_end:
                    realizate = []
                    nerealizate = []
                    mapping = {
                        "trezire": "pregatirea de dimineata", "ex1": "exercitiile de dimineata",
                        "masa_dimineata": "masa de dimineata", "masa_pranz": "masa de pranz",
                        "ex2": "exercitiile de dupa amiaza", "masa_seara": "masa de seara",
                        "culcare": "pregatirea de somn"
                    }
                    for act in ACTIVITIES:
                        nume = mapping.get(act, act)
                        if child_progres.get(act) == 1:
                            realizate.append(nume)
                        else:
                            nerealizate.append(nume)

                    msg_raport = "Bună ziua! A venit ora de verificare.\n\n"
                    msg_raport += " Realizate:\n- " + ("\n- ".join(realizate) if realizate else "Niciuna")
                    msg_raport += "\n\n Nerealizate:\n- " + (
                        "\n- ".join(nerealizate) if nerealizate else "Toate au fost făcute!")

                    # Folosim funcția SMTP în thread
                    threading.Thread(target=send_via_smtp, args=(email_parinte, "Raport Zilnic", msg_raport)).start()
            except:
                pass


# Inițializare scheduler (în afara main pentru a fi sigur că pornește pe Render)
if not scheduler.running:
    scheduler.init_app(app)
    scheduler.add_job(id='check_alerts', func=check_midtime_alerts, trigger='interval', minutes=1)
    scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
@app.route('/')
def home():
    return "OK", 200
