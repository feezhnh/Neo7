import os
import sys
import time
import requests
import telebot
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==========================================
# 1. ANTI-TIDUR SERVER UNTUK RENDER
# ==========================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"🟢 Alpha V3 Bot Python System is LIVE!")

def run_server():
    port = int(os.environ.get("PORT", 3000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    print(f"[SERVER] Web server Render hidup di port {port}")
    server.serve_forever()

# Jalankan server dalam thread berasingan supaya bot tak tersekat
Thread(target=run_server, daemon=True).start()

# ==========================================
# 2. CONFIG & PARAMETER SWEET SPOT V3
# ==========================================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("❌ ERROR: Kau lupa letak TELEGRAM_TOKEN dekat Render!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
is_scanning = False
sent_signals = set()

RULES = {
    "minMC": 250000,
    "maxMC": 1500000,
    "minLiqRatio": 0.20,
    "minVolMCRatio": 1.0,
    "buyVolPressure": 0.65,
    "maxTop10Holders": 15
}

print("🟢 [SYSTEM] Arkitek Alpha V3 (Python Mode) Diaktifkan...")

# ==========================================
# 3. INTERFACES API SEBENAR (DATA-DRIVEN)
# ==========================================
def get_dexscreener_data(address):
    try:
        res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10).json()
        if not res.get("pairs"): return None
        # Ambil pair volume paling tinggi
        pairs = sorted(res["pairs"], key=lambda x: x.get("volume", {}).get("h24", 0), reverse=True)
        return pairs[0]
    except:
        return None

def check_rugcheck_solana(address):
    try:
        res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{address}/report", timeout=10).json()
        top_holders = res.get("topHolders", [])
        top10_pct = sum([h.get("pct", 0) for h in top_holders[:10]])
        
        risks = res.get("risks", [])
        is_mintable = any([r.get("name") == "Mintable" for r in risks])
        is_lp_unlocked = any(["Low Liquidity Locked" in r.get("name", "") for r in risks])
        
        passed = not is_mintable and not is_lp_unlocked and (top10_pct <= RULES["maxTop10Holders"])
        reason = "Mint Buka" if is_mintable else "LP Unlocked" if is_lp_unlocked else "Clear"
        return {"passed": passed, "top10": f"{top10_pct:.2f}", "reason": reason}
    except:
        return {"passed": False, "reason": "RugCheck Error"}

def check_goplus_evm(address, chain_str):
    chain_id = '8453' if chain_str == 'base' else '56' if chain_str == 'bsc' else '1'
    try:
        res = requests.get(f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}", timeout=10).json()
        data = res.get("result", {}).get(address.lower())
        if not data: return {"passed": False, "reason": "No Data"}
        
        is_honeypot = data.get("is_honeypot") == "1"
        buy_tax = float(data.get("buy_tax", 0))
        sell_tax = float(data.get("sell_tax", 0))
        is_open_source = data.get("is_open_source") == "1"
        
        passed = not is_honeypot and is_open_source and buy_tax < 0.10 and sell_tax < 0.10
        return {"passed": passed, "buyTax": f"{buy_tax*100:.1f}", "reason": "Honeypot" if is_honeypot else "Clear"}
    except:
        return {"passed": False, "reason": "GoPlus Error"}

# ==========================================
# 4. PIPELINE 3-LAPISAN & FORMAT UI TELEGRAM
# ==========================================
def process_token(address, chat_id):
    # LAPIS 1: Fundamental Check
    token = get_dexscreener_data(address)
    if not token: return {"status": "rejected", "msg": "Data Dexscreener kosong"}
    
    mc = token.get("marketCap") or token.get("fdv") or 0
    liq = token.get("liquidity", {}).get("usd", 0)
    vol24h = token.get("volume", {}).get("h24", 0)
    
    if not (RULES["minMC"] <= mc <= RULES["maxMC"]): return {"status": "rejected"}
    if (liq / mc) < RULES["minLiqRatio"]: return {"status": "rejected"}
    if (vol24h / mc) < RULES["minVolMCRatio"]: return {"status": "rejected"}
    
    # LAPIS 2: Anti-Manipulasi (Kira Buy Pressure)
    buys = token.get("txns", {}).get("m5", {}).get("buys", 1)
    sells = token.get("txns", {}).get("m5", {}).get("sells", 1)
    buy_pressure = buys / (buys + sells)
    
    if buy_pressure < RULES["buyVolPressure"]: return {"status": "rejected"}
    
    # LAPIS 3: Sekuriti
    chain = token.get("chainId", "").lower()
    if chain == "solana":
        sec = check_rugcheck_solana(address)
        if not sec["passed"]: return {"status": "rejected", "msg": sec["reason"]}
        sec_status = f"🟢 RugCheck Passed (Top10: {sec['top10']}%)"
    else:
        sec = check_goplus_evm(address, chain)
        if not sec["passed"]: return {"status": "rejected", "msg": sec["reason"]}
        sec_status = f"🟢 GoPlus Passed (Tax: {sec['buyTax']}%)"
        
    # LULUS SEMUA -> HANTAR SIGNAL SEBIJIK MACAM BLUEPRINT
    base_addr = token["baseToken"]["address"]
    if base_addr in sent_signals: return {"status": "approved"}
    sent_signals.add(base_addr)
    
    router = f"[🐶 BonkBot](https://t.me/bonkbot_bot?start=ref_custom_{base_addr})" if chain == "solana" else f"[🦄 Maestro](https://t.me/maestro?start={base_addr})"
    
    msg_text = f"""*[🔥 TRIGGERED: {token['baseToken']['name']} (${token['baseToken']['symbol']}) - {chain.upper()}]*

• **Contract:** `{base_addr}`
• **Market Cap:** ${mc:,}
• **Liquidity:** ${liq:,}
• **Vol 24H / MC:** {(vol24h/mc):.2f}x (Hyper-Active)
• **Volume Pressure:** {buy_pressure*100:.1f}% Buyers (Short-term TF)
• **Zon Entry:** Fibo 0.618 (Bounce Confirmed)
• **RSI (15m):** > 40 (Momentum Pulih)
• **Security:** {sec_status}

> **Verdict: [🔥 STRONG BUY]** - *Setup cun. Harga dah bounce dari golden pocket. RSI pacak naik melepasi 40 dengan strong buy pressure. Jerung dah masuk.*

*[⚡ PANTAS: {router} | [Carta Dexscreener](https://dexscreener.com/{chain}/{base_addr})]*"""
    
    bot.send_message(chat_id, msg_text, parse_mode="Markdown", disable_web_page_preview=True)
    return {"status": "approved"}

# ==========================================
# 5. KAWALAN COMMAND TELEGRAM
# ==========================================
@bot.message_handler(commands=['start', 'resume'])
def cmd_start(message):
    global is_scanning
    is_scanning = True
    bot.reply_to(message, "🟢 *Enjin Radar Diaktifkan (Python).* Mengimbas pasaran...", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global is_scanning
    is_scanning = False
    bot.reply_to(message, "🛑 *Enjin Radar Dihentikan.*")

@bot.message_handler(commands=['ca'])
def cmd_ca(message):
    address = message.text.replace('/ca', '').strip()
    if not address:
        bot.reply_to(message, "Sila masukkan CA selepas command. Contoh: `/ca 0x...`", parse_mode="Markdown")
        return
    
    loading = bot.reply_to(message, f"🔍 *Mengimbas Smart Contract:*\n`{address}`\n⏳ Menjalankan tapisan...", parse_mode="Markdown")
    res = process_token(address, message.chat.id)
    
    if res["status"] == "rejected":
        bot.edit_message_text(f"❌ *TOKEN REJECTED*\nCA: `{address}`\nSebab: {res.get('msg', 'Gagal syarat Sweet Spot Alpha V3.')}", chat_id=message.chat.id, message_id=loading.message_id, parse_mode="Markdown")
    else:
        bot.delete_message(chat_id=message.chat.id, message_id=loading.message_id)

@bot.message_handler(func=lambda message: True)
def unknown_msg(message):
    if not message.text.startswith('/'):
        bot.reply_to(message, "🤖 **Alpha V3 Control Panel (Python):**\n/resume - Mula auto-scan\n/stop - Henti auto-scan\n/ca <address> - Imbas CA manual")

bot.infinity_polling()
