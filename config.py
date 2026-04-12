import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8555630882:AAE-QIjFgCVQMUlh18vTbQ5SuOW9Z83DZcY")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "1999635628"))

TRIAL_LINK  = os.environ.get("TRIAL_LINK",  "http://185.121.234.203:43234/red_vl?url=happ://add/https://riseadd.in/U70Jj6rWeNj15o5M")
VPN_LINK    = os.environ.get("VPN_LINK",    "http://185.121.234.203:43234/red_vl?url=happ://add/https://riseadd.in/DuAoKZ4c-uNkSZXV")
SBP_LINK    = os.environ.get("SBP_LINK",    "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111")
TON_WALLET  = os.environ.get("TON_WALLET",  "UQCe2TzE4kDy9dTgiESd_xCTX9FLrVGm29JX-RqaYKhEr0kT")
USDT_WALLET = os.environ.get("USDT_WALLET", "TWJwXNwMYrGXcnbzs2Q6YeBWm4i8XkBHoh")
SUPPORT     = os.environ.get("SUPPORT",     "@Husnijan_Axi")

TRIAL_DAYS = 3
TARIFFS = {
    "1":  {"name": "1 месяц",  "price": 75,  "days": 30},
    "3":  {"name": "3 месяц",  "price": 200, "days": 90},
    "6":  {"name": "6 месяц",  "price": 350, "days": 180},
    "12": {"name": "12 месяц", "price": 500, "days": 365},
}
REF_BONUS         = 20
PAYMENT_REF_BONUS = 50
MIN_WITHDRAW      = 300
DB                = "vpn.db"
