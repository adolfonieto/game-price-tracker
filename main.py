from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re
import smtplib
import os

app = FastAPI()



# ---------- SCRAPERS ----------


def search_idealo(game):
    url = f"https://www.idealo.es/precios/MainSearchProductCategory.html?q={game.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)

    results = []

    # buscar precios tipo "59,99 €"
    matches = re.findall(r'(\d{1,4},\d{2})\s?€', r.text)

    for m in matches[:10]:
        price = float(m.replace(",", "."))
        results.append({
            "store": "Idealo",
            "title": game,
            "price": price
        })

    return results


def search_dekudeals(game):
    url = f"https://www.dekudeals.com/search?q={game.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)

    results = []

    matches = re.findall(r'\$(\d+\.\d{2})', r.text)

    for m in matches[:5]:
        price = float(m)
        results.append({
            "store": "DekuDeals",
            "title": game,
            "price": price
        })

    return results


# ---------- API ----------

@app.get("/prices")
def get_prices(game: str):
    results = []
    try:
        results += search_idealo(game)
    except:
        pass

    try:
        results += search_dekudeals(game)
    except:
        pass

    if not results:
        return {"error": "No results"}
    
    min_price = min(r["price"] for r in results)

    return {
        "game": game,
        "min_price": min_price,
        "results": results
    }


# ---------- ALERTAS ----------

def send_email(subject, body):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(EMAIL_FROM, EMAIL_TO, message)


# memoria simple (en producción usar DB)
price_cache = {}

def check_price(game):
    data = get_prices(game)
    if "error" in data:
        return

    current = data["min_price"]
    old = price_cache.get(game)

    if old and current < old:
        send_email(
            f"Bajada de precio: {game}",
            f"Nuevo precio: {current}€ (antes {old}€)"
        )

    price_cache[game] = current
