import requests
import random
import json
import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

GIORNI = ["arte", "letteratura", "musica", "filosofia"]

# ---------------------------
# UTIL
# ---------------------------
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# ---------------------------
# CATEGORIA DEL GIORNO
# ---------------------------
def categoria_del_giorno():
    giorno = datetime.datetime.today().weekday()
    return GIORNI[giorno % len(GIORNI)]

# ---------------------------
# NO DUPLICATI
# ---------------------------
def scegli_opera(opere, history):
    disponibili = [o for o in opere if o not in history]
    if not disponibili:
        history.clear()
        disponibili = opere
    return random.choice(disponibili)

# ---------------------------
# WIKIPEDIA
# ---------------------------
def get_wikipedia(titolo):
    # 🔧 sistema titolo per URL
    titolo_url = titolo.replace(" ", "_")

    url = f"https://it.wikipedia.org/api/rest_v1/page/summary/{titolo_url}"

    try:
        res = requests.get(url)

        # ❌ pagina non trovata
        if res.status_code != 200:
            return f"Nessuna descrizione trovata per {titolo}.", None

        data = res.json()

    except Exception as e:
        return f"Errore nel recupero dati per {titolo}.", None

    testo = data.get("extract", f"{titolo} è un'opera significativa della cultura mondiale.")
    immagine = None

    if "thumbnail" in data:
        immagine = data["thumbnail"]["source"]

    return testo, immagine

# ---------------------------
# GENERAZIONE TESTO (NO AI)
# ---------------------------
def genera_post(titolo, testo, categoria):
    intro = random.choice([
        "☕ Oggi al Caffè:",
        "📚 Un sorso di cultura:",
        "✨ Scopriamo insieme:"
    ])
    
    return f"""{intro}

📌 {titolo} ({categoria})

{testo[:250]}...

👉 Torna domani per il prossimo caffè culturale.
"""

# ---------------------------
# TELEGRAM
# ---------------------------
def manda_post(testo, immagine=None):
    if immagine:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "caption": testo,
            "photo": immagine
        })
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": testo
        })

# ---------------------------
# MAIN
# ---------------------------
def main():
    opere = load_json("opere.json")
    history = load_json("history.json")

    categoria = categoria_del_giorno()
    
    if categoria not in history:
        history[categoria] = []

    opera = scegli_opera(opere[categoria], history[categoria])

    testo, immagine = get_wikipedia(opera)
    
    if not testo:
        testo = "Oggi scopriamo un'opera interessante della cultura mondiale."

    post = genera_post(opera, testo, categoria)

    manda_post(post, immagine)

    history[categoria].append(opera)
    save_json("history.json", history)

main()