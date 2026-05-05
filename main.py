from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re
import smtplib
import os

app = FastAPI()

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ---------- SCRAPERS ----------

def search_idealo(game):
    url = f"https://www.idealo.es/precios/MainSearchProductCategory.html?q={game}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)

    results = []

    # Búsqueda simple por precios en texto
    matches = re.findall(r"\d{1,4},\d{2}\s?€", r.text)

    for m in matches[:5]:  # cogemos los primeros 5 precios
        price = float(m.replace("€", "").replace(",", ".").strip())
        results.append({
            "store": "Idealo",
            "title": game,
            "price": price
        })

    return results


def search_dekudeals(game):
    url = f"https://www.dekudeals.com/search?q={game}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    results = []

    price = soup.select_one(".price")
    if price:
        value = re.findall(r"\d+\.\d+", price.text)
        if value:
            results.append({
                "store": "DekuDeals",
                "title": game,
                "price": float(value[0])
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
        return {
            "game": game,
            "min_price": 999,
            "results": [
                {"store": "fallback", "title": game, "price": 999}
            ]
        }

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
