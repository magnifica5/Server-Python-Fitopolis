import os
import threading
import smtplib
from email.mime.text import MIMEText
from supabase import create_client, Client
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
print("am incarcat datele")
EMAIL_SENDER = os.getenv("EMAIL")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("m am conectat ca client supabase")
ACTIVITIES = ["trezire", "ex1", "masa_dimineata", "masa_pranz", "ex2", "masa_seara", "culcare"]


def send_via_smtp(to, subject, message):
    """Trimite email folosind serverul SMTP Gmail"""
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
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
    print(f"[{datetime.now()}] Rulăm check_midtime_alerts...")
    children_res = supabase.table("children").select("*").execute()
    progres_res = supabase.table("progres_copil").select("*").execute()
    progres_dict = {p["connection_code"]: p for p in progres_res.data}
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
                if now.hour == alert_time.hour and now.minute == alert_time.minute:
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

                    threading.Thread(target=send_via_smtp, args=(email_parinte, "Raport Zilnic", msg_raport)).start()
                else:
                    try:
                        response = (
                            supabase.table("children")
                            .update({"check_verificare": False})
                            .eq("connection_code", code)
                            .execute()
                        )
                        if response.data:
                            print("Produs actualizat cu succes:")
                            print(response.data)
                        else:
                            print("Nu s-a găsit niciun produs cu ID-ul specificat sau nu s-au făcut modificări.")
                            print(response.error)  # Afișează erorile, dacă există

                    except Exception as e:
                        print(f"A apărut o eroare: {e}")
            except:
                pass

scheduler = APScheduler()

scheduler.add_job(
    id='check_alerts',
    func=check_midtime_alerts,
    trigger='interval',
    minutes=1
)

try:
    scheduler.start()
    print("APScheduler a pornit cu succes în worker.")
except Exception as e:
    print(f"Eroare la pornirea scheduler-ului: {e}")

# 4. Menținem procesul activ (foarte important pentru Render Background Worker)
import time

while True:
    time.sleep(1)
