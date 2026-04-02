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
# FALLBACK IMAGE
# ---------------------------
def fallback_image():
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/480px-No_image_available.svg.png"

# ---------------------------
# WIKIMEDIA IMAGE (TOP)
# ---------------------------
def get_wikimedia_image(query):
    q = urllib.parse.quote(query)
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={q}&gsrlimit=5&prop=imageinfo&iiprop=url&format=json"

    try:
        res = requests.get(url).json()
        pages = res.get("query", {}).get("pages", {})

        for p in pages.values():
            info = p.get("imageinfo")
            if info:
                return info[0]["url"]
    except:
        pass

    return None

# ---------------------------
# WIKIPEDIA SUMMARY
# ---------------------------
def get_wikipedia_summary(titolo):
    titolo_url = urllib.parse.quote(titolo)
    url = f"https://it.wikipedia.org/api/rest_v1/page/summary/{titolo_url}"

    try:
        res = requests.get(url)
        if res.status_code != 200:
            return "", None

        data = res.json()
        return data.get("extract", ""), data.get("thumbnail", {}).get("source")

    except:
        return "", None

# ---------------------------
# BEST IMAGE
# ---------------------------
def get_best_image(titolo, categoria):
    if categoria == "cinema":
        query = f"{titolo} film poster"
    elif categoria == "arte":
        query = f"{titolo} painting"
    elif categoria == "letteratura":
        query = f"{titolo} book cover"
    elif categoria == "filosofia":
        query = f"{titolo} philosopher"
    else:
        query = titolo

    # 1️⃣ Wikimedia
    img = get_wikimedia_image(query)
    if img:
        return img

    # 2️⃣ Wikipedia
    _, wiki_img = get_wikipedia_summary(titolo)
    if wiki_img:
        return wiki_img

    # 3️⃣ fallback
    return fallback_image()

# ---------------------------
# OPENAI - SCELTA OPERA
# ---------------------------
def scegli_opera_ai(categoria):
    prompt = f"""
Sei un curatore culturale.

Dammi UN'opera interessante per la categoria: {categoria}

Formato JSON:
{{
  "titolo": "...",
  "autore": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        # sicurezza parsing
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]

        return json.loads(content)

    except Exception as e:
        print("ERRORE SCELTA OPERA:", e)
        return {"titolo": "Opera culturale", "autore": ""}

# ---------------------------
# OPENAI - GENERAZIONE TESTO
# ---------------------------
def genera_post_ai(titolo, categoria, descrizione_base):
    prompt = f"""
Sei autore di un canale Telegram chiamato "Il Caffè".

Scrivi un post breve e coinvolgente su:
Titolo: {titolo}
Categoria: {categoria}

Regole:
- massimo 120 parole
- tono moderno e interessante
- NO introduzioni banali
- inserisci un insight

Contesto:
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
        return f"☕ {titolo}\n\nUn contenuto interessante da scoprire."

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

# ---------------------------
# MAIN
# ---------------------------
def main():
    if not BOT_TOKEN or not CHAT_ID or not OPENAI_API_KEY:
        raise Exception("Variabili mancanti!")

    history = load_json("history.json")
    categoria = categoria_del_giorno()

    if categoria not in history:
        history[categoria] = []

    opera = scegli_opera_ai(categoria)

    titolo = opera.get("titolo", "")
    autore = opera.get("autore", "")

    query = f"{titolo} {autore}".strip()

    descrizione, _ = get_wikipedia_summary(query)
    immagine = get_best_image(query, categoria)

    post = genera_post_ai(query, categoria, descrizione)

    manda_post(post, immagine)

    history[categoria].append(query)
    save_json("history.json", history)


main()