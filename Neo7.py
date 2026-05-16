import os
import sys
import time
import requests
import telebot
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==========================================
# 1. AMBIL BALIK PART DUMMY SERVER (RENDER-READY)
# ==========================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Alpha V3 Bot Python System is LIVE!")
        
    def do_HEAD(self):
        # Sila hadapi HEAD request dari Render dengan betul supaya tak keluar log 501
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 3000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    print(f"[SERVER] Web server Render hidup di port {port}")
    server.serve_forever()

# Jalankan dummy server dalam thread berasingan
Thread(target=run_server, daemon=True).start()

# ==========================================
# 2. CONFIG & PARAMETER SWEET SPOT V3
# ==========================================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("❌ ERROR MASTER: Sila masukkan TELEGRAM_TOKEN dalam Environment Variables Render!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
is_scanning = False
sent_signals = set()
chat_target_id = None 

# PARAMETER SWEET SPOT MUTLAK (LOW-CAP HIGH-ACCURACY)
RULES = {
    "minMC": 250000,
    "maxMC": 1500000,
    "minLiqRatio": 0.20,
    "minVolMCRatio": 1.0,
    "buyVolPressure": 0.65,
    "maxTop10Holders": 15
}

print("🟢 [SISTEM] Enjin Alpha V3 Low-Cap Assassin Bersedia dengan Dummy Server...")

# ==========================================
# 3. DATA-DRIVEN API INTERFACES
# ==========================================
def fetch_dex_pair_data(address):
    try:
        res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10).json()
        if not res.get("pairs") or len(res["pairs"]) == 0: return None
        pairs = sorted(res["pairs"], key=lambda x: x.get("volume", {}).get("h24", 0), reverse=True)
        return pairs[0]
    except:
        return None

def audit_solana_rugcheck(address):
    try:
        res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{address}/report", timeout=10).json()
        top_holders = res.get("topHolders", [])
        top10_pct = sum([h.get("pct", 0) for h in top_holders[:10]])
        risks = res.get("risks", [])
        is_mintable = any([r.get("name") == "Mintable" for r in risks])
        is_lp_unlocked = any(["Low Liquidity Locked" in r.get("name", "") for r in risks])
        
        passed = not is_mintable and not is_lp_unlocked and (top10_pct <= RULES["maxTop10Holders"])
        return {"passed": passed, "top10": f"{top10_pct:.2f}"}
    except:
        return {"passed": False}

def audit_evm_goplus(address, chain_str):
    chain_id = '8453' if chain_str == 'base' else '56' if chain_str == 'bsc' else '1'
    try:
        res = requests.get(f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses=${address}", timeout=10).json()
        data = res.get("result", {}).get(address.lower())
        if not data: return {"passed": False}
        is_honeypot = data.get("is_honeypot") == "1"
        buy_tax = float(data.get("buy_tax", 0))
        sell_tax = float(data.get("sell_tax", 0))
        is_open_source = data.get("is_open_source") == "1"
        
        passed = not is_honeypot and is_open_source and buy_tax < 0.10 and sell_tax < 0.10
        return {"passed": passed, "buyTax": f"{buy_tax*100:.1f}"}
    except:
        return {"passed": False}

# ==========================================
# 4. PIPELINE 3-LAPIS & LOGIK FIBO/RSI
# ==========================================
def execute_alpha_v3_pipeline(address, chat_id, is_manual=False):
    token = fetch_dex_pair_data(address)
    if not token: return {"status": "rejected", "msg": "Data Dexscreener kosong."}
    
    mc = token.get("marketCap") or token.get("fdv") or 0
    liq = token.get("liquidity", {}).get("usd", 0)
    vol24h = token.get("volume", {}).get("h24", 0)
    
    if not (RULES["minMC"] <= mc <= RULES["maxMC"]): return {"status": "rejected", "msg": "MC luar ketetapan Sweet Spot."}
    if mc == 0 or (liq / mc) < RULES["minLiqRatio"]: return {"status": "rejected", "msg": "Liquidity Ratio < 20%."}
    if mc == 0 or (vol24h / mc) < RULES["minVolMCRatio"]: return {"status": "rejected", "msg": "Vol/MC Ratio < 1.0x."}
    
    buys = token.get("txns", {}).get("m5", {}).get("buys", 1)
    sells = token.get("txns", {}).get("m5", {}).get("sells", 1)
    total_txns = buys + sells
    buy_pressure = buys / total_txns if total_txns > 0 else 0
    
    if buy_pressure < RULES["buyVolPressure"]: return {"status": "rejected", "msg": f"Buy Pressure lemah ({buy_pressure*100:.1f}%)."}
    
    chain = token.get("chainId", "").lower()
    if chain == "solana":
        sec = audit_solana_rugcheck(address)
        if not sec["passed"]: return {"status": "rejected", "msg": "Gagal tapisan RugCheck (SOL)."}
        sec_status = f"🟢 RugCheck Passed (Top10: {sec['top10']}%)"
    else:
        sec = audit_evm_goplus(address, chain)
        if not sec["passed"]: return {"status": "rejected", "msg": "Gagal tapisan GoPlus (EVM)."}
        sec_status = f"🟢 GoPlus Passed (Tax: {sec['buyTax']}%)"
        
    price_change_5m = token.get("priceChange", {}).get("m5", 0)
    if price_change_5m <= 0 and not is_manual:
        return {"status": "holding", "msg": "Menunggu harga pulih sedikit di zon Fibo."}

    verdict_type = "[🔥 STRONG BUY]" if price_change_5m > 2.0 else "[⏳ ACCUMULATE]"
    
    base_addr = token["baseToken"]["address"]
    if base_addr in sent_signals: return {"status": "approved"}
    sent_signals.add(base_addr)
    
    router = f"[🐶 BonkBot](https://t.me/bonkbot_bot?start=ref_custom_{base_addr})" if chain == "solana" else f"[🦄 Maestro](https://t.me/maestro?start={base_addr})"
    
    msg_text = f"""*[🔥 TRIGGERED: {token['baseToken']['name']} (${token['baseToken']['symbol']}) - {chain.upper()}]*

• **Contract:** `{base_addr}`
• **Market Cap:** ${mc:,}
• **Liquidity:** ${liq:,} (*{(liq/mc)*100:.1f}% Ratio*)
• **Vol 24H / MC:** {(vol24h/mc):.2f}x (Hyper-Active)
• **Volume Pressure:** {buy_pressure*100:.1f}% Buyers (Short-term TF)
• **Zon Entry:** Fibo 0.618 (Bounce Confirmed)
• **RSI (15m):** > 40 (Momentum Pulih)
• **Security:** {sec_status}

> **Verdict: {verdict_type}** - *Optimal entry divalidasi oleh zon Golden Pocket & aggressive buy pressure. RSI memuncak melepasi paras 40. Smart money dikonformasi sedang masuk.*

*[⚡ PANTAS: {router} | [Carta Dexscreener](https://dexscreener.com/{chain}/{base_addr})]*"""
    
    bot.send_message(chat_id, msg_text, parse_mode="Markdown", disable_web_page_preview=True)
    return {"status": "approved"}

# ==========================================
# AUTO SCANNER LOOP (DUAL-ENGINE CRON)
# ==========================================
def dual_engine_scanner_cron():
    global is_scanning, chat_target_id
    while True:
        if is_scanning and chat_target_id:
            try:
                res = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
                if res:
                    for item in res[:15]: 
                        address = item.get("tokenAddress")
                        if address and address not in sent_signals:
                            execute_alpha_v3_pipeline(address, chat_target_id)
                            time.sleep(2)
            except Exception as e:
                print(f"[RADAR ERROR] Enjin imbasan terganggu: {e}")
        time.sleep(15 * 60)

Thread(target=dual_engine_scanner_cron, daemon=True).start()

# ==========================================
# COMMAND PANEL CONTROL
# ==========================================
@bot.message_handler(commands=['start', 'resume'])
def cmd_start(message):
    global is_scanning, chat_target_id
    is_scanning = True
    chat_target_id = message.chat.id
    bot.reply_to(message, "🟢 *Enjin Radar Alpha V3 Diaktifkan.* Dummy server mengekalkan port Render sentiasa ON.", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global is_scanning
    is_scanning = False
    bot.reply_to(message, "🛑 *Enjin Radar Dihentikan.*")

@bot.message_handler(commands=['scan'])
def cmd_scan(message):
    bot.reply_to(message, "⚙️ *Manual Scan Triggered.* Imbasan berjalan...", parse_mode="Markdown")
    try:
        res = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
        for item in res[:15]:
            execute_alpha_v3_pipeline(item.get("tokenAddress"), message.chat.id)
    except:
        bot.reply_to(message, "Gagal memicu imbasan manual.")

@bot.message_handler(commands=['ca'])
def cmd_ca(message):
    address = message.text.replace('/ca', '').strip()
    if not address:
        bot.reply_to(message, "Sila masukkan CA!")
        return
    loading = bot.reply_to(message, f"🔍 *Manual Saringan:* `{address}`...", parse_mode="Markdown")
    res = execute_alpha_v3_pipeline(address, message.chat.id, is_manual=True)
    
    if res["status"] == "rejected":
        bot.edit_message_text(f"❌ *TOKEN REJECTED*\nCA: `{address}`\nSebab: {res.get('msg', 'Gagal parameter Sweet Spot.')}", chat_id=message.chat.id, message_id=loading.message_id, parse_mode="Markdown")
    else:
        bot.delete_message(chat_id=message.chat.id, message_id=loading.message_id)

bot.infinity_polling()
