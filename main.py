import os # ma ajuta sa accesez variabilele din .env
import threading # face mai multe actiuni de o data ca sa nu se blocheze cat asteapta confirmare de la sendgrid
import json
import urllib.request # trimite cererea catre sendgrid
from flask import Flask, request, abort
from supabase import create_client, Client
from flask_apscheduler import APScheduler # verifica o data la 5 minute daca este timpul pentru un mail, ma ajuta ca sa stiu ce ora este
from datetime import datetime, timedelta # datetime = cat este ora acum, timedelta = operatii cu timp, permite faza cu jumatate din interval
from dotenv import load_dotenv
ACTIVITIES = ["trezire", "ex1", "masa_dimineata", "masa_pranz", "ex2", "masa_seara", "culcare"]
load_dotenv()
app = Flask(__name__)
scheduler = APScheduler()
API_KEY = os.getenv("API_KEY")
EMAIL_SENDER = os.getenv("EMAIL")
SENDGRID_KEY = os.getenv("SENDGRID_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def send_via_sendgrid(to, subject, message):
    # Aceasta este structura (body-ul) pe care o primește SendGrid
    payload = {
        "personalizations": [{
            "to": [{"email": to}]
        }],
        "from": {"email": EMAIL_SENDER},
        "subject": subject,
        "content": [{
            "type": "text/plain",
            "value": message
        }]
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/email/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Email trimis la {to}, status: {response.status}")
    except Exception as e:
        # Dacă e eroare de la server, printăm și detaliile dacă se poate
        print(f"Eroare la trimiterea emailului către {to}: {e}")

def get_parent_email(parent_id):
    try:
        user_data = supabase.auth.admin.get_user_by_id(parent_id)
        return user_data.user.email
    except Exception as e:
        print(f"Eroarea: {e}")
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
                    status = child_progres.get(activity)
                    if status == 0:
                        nume_afisare = {
                            "trezire": "pregatirea de dimineata",
                            "ex1": "exercitiile de dimineata",
                            "masa_dimineata": "masa de dimineata",
                            "masa_pranz": "masa de pranz",
                            "ex2": "exercitiile de dupa amiaza",
                            "masa_seara": "masa de seara",
                            "culcare": "pregatirea de somn"
                        }.get(activity, activity)

                        mesg = f"Copilul inca nu a inceput {nume_afisare}, activitate setata pentru ora {time_val[:5]}."
                        threading.Thread(target=send_via_sendgrid,
                                         args=(email_parinte, "Alertă activitate", mesg)).start()
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
                        "trezire": "pregatirea de dimineata",
                        "ex1": "exercitiile de dimineata",
                        "masa_dimineata": "masa de dimineata",
                        "masa_pranz": "masa de pranz",
                        "ex2": "exercitiile de dupa amiaza",
                        "masa_seara": "masa de seara",
                        "culcare": "pregatirea de somn"
                    }
                    for act in ACTIVITIES:
                        nume = mapping.get(act, act)
                        if child_progres.get(act) == 1:
                            realizate.append(nume)
                        else:
                            nerealizate.append(nume)
                    msg_raport = "Bună ziua! A venit ora de verificare.\n\n"
                    msg_raport += "Realizate:\n- " + ("\n- ".join(realizate) if realizate else "Niciuna")
                    msg_raport += "\n\nNerealizate:\n- " + (
                        "\n- ".join(nerealizate) if nerealizate else "Toate au fost făcute!")

                    threading.Thread(target=send_via_sendgrid,
                                     args=(email_parinte, "Raport Zilnic", msg_raport)).start()
            except:
                pass


if __name__ == "__main__":
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
