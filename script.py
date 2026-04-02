import requests
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
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

GIORNI = ["arte", "letteratura", "filosofia", "arte", "tecnologia"]

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

def normalize(text):
    return text.lower().strip()

# ---------------------------
# CATEGORIA DEL GIORNO
# ---------------------------
def categoria_del_giorno():
    return GIORNI[datetime.datetime.today().weekday() % len(GIORNI)]

# ---------------------------
# FALLBACK IMAGE
# ---------------------------
def fallback_image():
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/480px-No_image_available.svg.png"

# ---------------------------
# VALIDAZIONE OPERA (ANTI FAKE)
# ---------------------------
def opera_valida(titolo):
    try:
        url = f"https://it.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo)}"
        res = requests.get(url)
        return res.status_code == 200
    except:
        return False

# ---------------------------
# 🎬 OMDB
# ---------------------------
def get_movie_poster(titolo):
    if not OMDB_API_KEY:
        return None

    try:
        url = f"http://www.omdbapi.com/?t={urllib.parse.quote(titolo)}&apikey={OMDB_API_KEY}"
        res = requests.get(url).json()

        if res.get("Response") == "True":
            poster = res.get("Poster")
            if poster and poster != "N/A":
                return poster
    except:
        pass

    return None

# ---------------------------
# 🎨 MET (ARTE)
# ---------------------------
def get_art_image(titolo, autore=None):
    try:
        search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={urllib.parse.quote(titolo)}"
        res = requests.get(search_url).json()

        if res["total"] > 0:
            for object_id in res["objectIDs"][:10]:

                obj = requests.get(
                    f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
                ).json()

                title = obj.get("title", "").lower()
                artist = obj.get("artistDisplayName", "").lower()

                if titolo.lower() in title or title in titolo.lower():
                    if not autore or autore.lower() in artist:
                        img = obj.get("primaryImage")
                        if img:
                            return img

    except:
        pass

    return None

# ---------------------------
# 📚 OPENLIBRARY
# ---------------------------
def get_book_cover(titolo):
    try:
        url = f"https://openlibrary.org/search.json?title={urllib.parse.quote(titolo)}"
        res = requests.get(url).json()

        docs = res.get("docs", [])
        if docs and "cover_i" in docs[0]:
            return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg"
    except:
        pass

    return None

# ---------------------------
# WIKIPEDIA
# ---------------------------
def get_wikipedia_summary(titolo):
    try:
        url = f"https://it.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo)}"
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
def get_best_image(titolo, categoria, autore=None):

    if categoria == "cinema":
        img = get_movie_poster(titolo)
        if img:
            return img

    if categoria == "arte":
        img = get_art_image(titolo, autore)
        if img:
            return img

    if categoria == "letteratura":
        img = get_book_cover(titolo)
        if img:
            return img

    _, wiki_img = get_wikipedia_summary(titolo)
    if wiki_img:
        return wiki_img

    return fallback_image()

# ---------------------------
# OPENAI - SCELTA OPERA
# ---------------------------
def scegli_opera_ai(categoria, history):
    prompt = f"""
Sei un curatore culturale.

Categoria: {categoria}

NON usare queste opere:
{history}

Regole:
- deve esistere davvero
- niente placeholder
- varia autore e periodo

Formato JSON:
{{
  "titolo": "...",
  "autore": "..."
}}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = res.choices[0].message.content
        start = content.find("{")
        end = content.rfind("}") + 1

        return json.loads(content[start:end])

    except:
        return {"titolo": "Opera culturale", "autore": ""}

# ---------------------------
# OPENAI - POST
# ---------------------------
def genera_post_ai(titolo, categoria, descrizione):
    prompt = f"""
Scrivi un post Telegram per "Il Caffè".

Titolo: {titolo}
Categoria: {categoria}

Regole:
- max 120 parole
- coinvolgente
- non accademico
- insight interessante
"""

    try:
        res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content

    except:
        return f"☕ {titolo}"

# ---------------------------
# TELEGRAM
# ---------------------------
def manda_post(testo, immagine):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    res = requests.post(url, data={
        "chat_id": CHAT_ID,
        "caption": testo,
        "photo": immagine
    })

    print(res.status_code, res.text)

# ---------------------------
# MAIN
# ---------------------------
def main():
    if not BOT_TOKEN or not CHAT_ID or not OPENAI_API_KEY:
        raise Exception("Variabili mancanti")

    history = load_json("history.json")
    categoria = categoria_del_giorno()

    if categoria not in history:
        history[categoria] = []

    normalized_history = [normalize(h) for h in history[categoria]]

    # 🔁 RETRY + VALIDAZIONE
    for _ in range(5):
        opera = scegli_opera_ai(categoria, history[categoria])

        titolo = opera.get("titolo", "")
        autore = opera.get("autore", "")

        query = f"{titolo} {autore}".strip()

        if (
            normalize(query) not in normalized_history
            and opera_valida(titolo)
        ):
            break
    else:
        raise Exception("Nessuna opera valida trovata")

    descrizione, _ = get_wikipedia_summary(query)
    immagine = get_best_image(titolo, categoria, autore)

    post = genera_post_ai(query, categoria, descrizione)

    manda_post(post, immagine)

    history[categoria].append(query)
    save_json("history.json", history)


main()