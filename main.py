import os
from flask import Flask
from dotenv import load_dotenv

# Configurare
load_dotenv()
app = Flask(__name__)

@app.route("/") # pentru uptime robot
def home():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
