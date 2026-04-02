import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8555630882:AAGqeRiq1jU6W-fqjr_soJTH0168B7Iclsg")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "1999635628"))

VPN_LINK    = os.environ.get("VPN_LINK",    "https://hirbilon.net/open?sub_url=https://g3.hirbilon.net:443/yessub/p5ln8k1qld9nf0sa")
SBP_LINK    = os.environ.get("SBP_LINK",    "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111")
TON_WALLET  = os.environ.get("TON_WALLET",  "UQCe2TzE4kDy9dTgiESd_xCTX9FLrVGm29JX-RqaYKhEr0kT")
USDT_WALLET = os.environ.get("USDT_WALLET", "TWJwXNwMYrGXcnbzs2Q6YeBWm4i8XkBHoh")
SUPPORT     = os.environ.get("SUPPORT",     "@Husnijan_Axi")

TRIAL_DAYS = 3
TARIFFS = {
    "1":  {"name": "1 oy",  "price": 75,  "days": 30},
    "3":  {"name": "3 oy",  "price": 200, "days": 90},
    "6":  {"name": "6 oy",  "price": 350, "days": 180},
    "12": {"name": "12 oy", "price": 500, "days": 365},
}
REF_BONUS         = 10
PAYMENT_REF_BONUS = 30
MIN_WITHDRAW      = 200
DB                = "vpn.db"
