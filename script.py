import requests
import random
import json
import datetime
import os
import urllib.parse
from openai import OpenAI

# ---------------------------
# ENV
# ---------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

GIORNI = ["arte", "letteratura", "filosofia", "cinema", "tecnologia"]

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
# WIKIPEDIA (ROBUSTO)
# ---------------------------
def get_wikipedia(titolo):
    titolo_url = urllib.parse.quote(titolo)
    url = f"https://it.wikipedia.org/api/rest_v1/page/summary/{titolo_url}"

    try:
        res = requests.get(url)

        if res.status_code != 200:
            return "", fallback_image()

        if not res.text.strip():
            return "", fallback_image()

        try:
            data = res.json()
        except:
            return "", fallback_image()

    except:
        return "", fallback_image()

    testo = data.get("extract", "")
    immagine = data.get("thumbnail", {}).get("source", fallback_image())

    return testo, immagine


def fallback_image():
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/480px-No_image_available.svg.png"


# ---------------------------
# OPENAI GENERAZIONE TESTO
# ---------------------------
def genera_post_ai(titolo, categoria, descrizione_base):
    prompt = f"""
Sei autore di un canale Telegram culturale chiamato "Il Caffè".

Scrivi un post su:
Titolo: {titolo}
Categoria: {categoria}

Regole:
- massimo 120 parole
- tono: coinvolgente, moderno, NON accademico
- deve incuriosire subito
- evita frasi banali tipo "oggi parliamo"
- inserisci un piccolo insight interessante
- stile fluido e leggibile

Base:
{descrizione_base}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("ERRORE OPENAI:", e)
        return fallback_post(titolo)


def fallback_post(titolo):
    return f"""☕ {titolo}

Un contenuto culturale interessante da scoprire.

☕ Il Caffè è il tuo momento quotidiano di cultura.
"""


# ---------------------------
# TELEGRAM
# ---------------------------
def manda_post(testo, immagine):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "caption": testo,
        "photo": immagine
    })

    print("TELEGRAM STATUS:", response.status_code)
    print("TELEGRAM RESPONSE:", response.text)
    

def scegli_opera_ai(categoria):
    prompt = f"""
Sei un curatore culturale.

Dammi UN'opera interessante per la categoria: {categoria}

Regole:
- deve essere specifica (non generica)
- deve esistere davvero
- includi autore se necessario
- evita opere troppo obscure

Formato risposta JSON:
{{
  "titolo": "...",
  "autore": "..."
}}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    return json.loads(response.choices[0].message.content)


# ---------------------------
# MAIN
# ---------------------------
def main():
    if not BOT_TOKEN or not CHAT_ID or not OPENAI_API_KEY:
        raise Exception("Mancano variabili d'ambiente!")
    
    history = load_json("history.json")

    categoria = categoria_del_giorno()

    if categoria not in history:
        history[categoria] = []

    opera_ai = scegli_opera_ai(categoria)

    titolo = opera_ai["titolo"]
    autore = opera_ai["autore"]

    query = f"{titolo} {autore}" if autore else titolo

    descrizione, immagine = get_wikipedia(query)

    post = genera_post_ai(query, categoria, descrizione)

    manda_post(post, immagine)

    history[categoria].append(opera_ai)
    save_json("history.json", history)


main()