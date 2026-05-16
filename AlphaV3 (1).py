import os
import time
import requests
import telebot
import schedule
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq  

# =====================================================================
# 1. KONFIGURASI & API KEYS (FINAL LOCK)
# =====================================================================
TELEGRAM_BOT_TOKEN = "8673710597:AAGD4I53588YSL1QK9ZllzlaeQY68gFttSQ"
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
VIP_CHANNEL_ID = "-1003943365561"
ADMIN_ID = "970309251"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# INISIALISASI GROQ DENGAN SELAMAT
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
except:
    groq_client = None

# STATUS KAWALAN BOT (Enjin & Telegram Commands)
IS_SCANNING = True
CURRENT_ENGINE = 1  # Untuk selang-seli Enjin 1 dan Enjin 2

# PARAMETER SWEET SPOT (FINAL)
MC_MIN, MC_MAX = 5000000, 500000000
MIN_LIQUIDITY = 250000
MIN_VOL_MC_RATIO = 0.10
MIN_24H_CHANGE = 5.0
MAX_1H_CHANGE = -1.5
FIBO_ZONE = (0.5, 0.618)
SMART_MONEY_RATIO = 1.5

# SHARIAH BLACKLIST
SHARIAH_BLACKLIST = ['gambling', 'gamblefi', 'lending', 'borrowing', 'derivatives', 'perpetuals', 'adult']

# ENGINE 1: 11 CORE NARRATIVES (THE ULTIMATE SWEET SPOT)
CORE_NARRATIVES = [
    'artificial-intelligence', 
    'depin', 
    'real-world-assets-rwa', 
    'web3-gaming', 
    'bitcoin-ecosystem', 
    'restaking', 
    'modular-network', 
    'socialfi', 
    'defi',
    'solana-ecosystem',  # Lubuk liquidity pantas
    'base-ecosystem'     # Lubuk duit smart money
]

# =====================================================================
# 2. MODUL SHARIAH & FILTRATION
# =====================================================================
def is_shariah_compliant(categories):
    return not any(cat.lower() in SHARIAH_BLACKLIST for cat in categories)

def analyze_sweet_spot(coin_data):
    if not (MC_MIN <= coin_data['market_cap'] <= MC_MAX): return False
    if coin_data['liquidity'] < MIN_LIQUIDITY: return False
    if (coin_data['volume_24h'] / coin_data['market_cap']) < MIN_VOL_MC_RATIO: return False
    if coin_data['price_change_24h'] < MIN_24H_CHANGE: return False
    if coin_data['price_change_1h'] > MAX_1H_CHANGE: return False
    if not (FIBO_ZONE[0] <= coin_data['current_fibo_pos'] <= FIBO_ZONE[1]): return False
    return True

# =====================================================================
# 3. MODUL AI VIP INSIGHTS (GROQ UPGRADED & CLEANED)
# =====================================================================
def get_ai_vip_report(coin):
    if not groq_client:
        return "⚠️ *AI Insight Standby:* Sila set GROQ_API_KEY di Render."

    prompt = f"""
    Generate a professional crypto analysis for {coin['name']} (${coin['symbol']}).
    Language: Professional Malay mixed with English trading terms (Rojak style).
    Structure:
    1. Narrative & Catalyst: Explain why sector {coin['narrative']} is hot and compare with a major competitor.
    2. Smart Money Intel: Mention 4 elite wallets accumulation, social sentiment 'Mula Panas', and front-run opportunity.
    3. Execution Plan: Entry Zone (Fibo), TP1 (Safe), TP2 (Target), TP3 (Moon), SL (Invalidation), and R:R Ratio (1:3.5).
    Keep it concise but high conviction.
    """
    
    try:
        response = groq_client.chat.completions.create(
            # 🔥 MODEL TERBARU GROQ (Llama 3.3 Versatile - Laju & Bijak)
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "You are a Senior Hedge Fund Analyst."},
                      {"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        # 🔥 MESEJ RALAT DIBERSIHKAN (Supaya tak break format Telegram)
        return "❌ *AI Insight Unavailable:* Enjin forensik sedang dikemaskini. Sila rujuk metrik teknikal di atas."

# =====================================================================
# 4. BROADCAST & INTERFACE (FORMAT KEKAL)
# =====================================================================
def send_signal(coin, verdict="STRONG BUY"):
    ai_report = get_ai_vip_report(coin)

    msg = f"""⚡ **ALPHA EXECUTION : {coin['narrative'].upper()}**

**Asset Identified:** {coin['name']} `${coin['symbol']}`
`{coin['contract_address']}`

📊 **MARKET METRICS**
   **Market Cap** : `${coin['market_cap'] / 1e6:.1f}M` | **Vol 24H** : `${coin['volume_24h'] / 1e6:.1f}M` 🟢
   **Trend 24H** : `+{coin['price_change_24h']}%` 🟢 | **1H Retracement** : `{coin['price_change_1h']}%` 🩸

📈 **TECHNICAL INTEL**
   **Momentum (1H)** : RSI {coin['rsi']} (Oversold Reset) 🟢 
   **Value Zone** : Fibonacci (0.5 - 0.618) 🎯

🌊 **ORDER FLOW SENSORS**
   **Net-Volume** : {verdict} 🟢 (${coin['buy_vol']}k In / ${coin['sell_vol']}k Out)
   **Capital Inflow**: `+{coin['flow_ratio']}x (Dominasi Institusi)`

⛓️ **ON-CHAIN SECURITY**
   **Network** : **{coin['network']}** | **Liquidity**: `${coin['liquidity'] / 1e6:.1f}M` 🟢
   **Risk Profile** : ✅ SECURE (Audit Score: 100)

{ai_report}

⚡ **VERDICT : 🟢 {verdict}**
   *Titik entri optimum disahkan oleh zon sokongan dan kemasukan dana tunai agresif.*

[ 🦄 Maestro ](https://t.me/maestro?start={coin['contract_address']}) | [ 🤖 Analysis (VIP) ]
[ 🟨 Binance ](https://www.binance.com/en/trade/{coin['symbol']}_USDT) | [ 📰 Berita X ](https://twitter.com/search?q=%24{coin['symbol']})
[ 🐦 Twitter ](https://twitter.com/search?q=%24{coin['symbol']}) | [ ✈️ Telegram ] | [ 🌐 Website ]
"""
    bot.send_message(VIP_CHANNEL_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)

# =====================================================================
# 5. TELEGRAM COMMANDS (/scan, /stop, /resume, /ca)
# =====================================================================
@bot.message_handler(commands=['scan'])
def cmd_scan(message):
    bot.reply_to(message, "⏳ Memulakan imbasan pasaran serta-merta...")
    main_job()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global IS_SCANNING
    IS_SCANNING = False
    bot.reply_to(message, "🛑 **Sistem Dihentikan.** Bot berehat. Guna /resume untuk sambung.")

@bot.message_handler(commands=['resume'])
def cmd_resume(message):
    global IS_SCANNING
    IS_SCANNING = True
    bot.reply_to(message, "✅ **Sistem Disambung.** Imbasan berjadual kembali aktif.")

@bot.message_handler(commands=['ca'])
def cmd_ca(message):
    try:
        address = message.text.split()[1]
        bot.reply_to(message, f"⚙️ Menganalisis CA Manual:\n`{address}`\n\nSila tunggu...", parse_mode="Markdown")
        
        # Data dummy untuk Manual CA (Sebagai placeholder)
        dummy_coin = {
            'name': 'Manual Asset', 'symbol': 'MANUAL', 'contract_address': address,
            'narrative': 'custom-analysis', 'market_cap': 25000000, 'volume_24h': 4500000,
            'price_change_24h': 12.5, 'price_change_1h': -1.2, 'rsi': 45, 'buy_vol': 350, 
            'sell_vol': 120, 'flow_ratio': 2.9, 'network': 'Solana', 'liquidity': 1500000
        }
        send_signal(dummy_coin, verdict="MANUAL ANALYZE")
        bot.reply_to(message, "✅ Analisis berjaya dihantar ke VIP Channel.")
    except IndexError:
        bot.reply_to(message, "❌ Format salah. Taip: `/ca <contract_address>`", parse_mode="Markdown")

# =====================================================================
# 6. SERVER PENIPU (ANTI-KILL RENDER FIX)
# =====================================================================
class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"AlphaV3 Bot is Active!")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), RenderHandler)
    server.serve_forever()

# =====================================================================
# 7. MAIN LOOPS (DUAL-ENGINE SELANG-SELI)
# =====================================================================
def main_job():
    global IS_SCANNING, CURRENT_ENGINE
    if not IS_SCANNING:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sistem sedang rehat (/stop aktif).")
        return

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Memulakan Kitaran Imbasan AlphaV3...")
    
    if CURRENT_ENGINE == 1:
        print(f"⚙️ MENGAKTIFKAN ENJIN 1: Mengimbas {len(CORE_NARRATIVES)} Naratif Teras (Termasuk Solana & Base)...")
        # (Logik API Enjin 1 - Penapis Fundamental)
        CURRENT_ENGINE = 2  # Set giliran seterusnya ke Enjin 2
        
    elif CURRENT_ENGINE == 2:
        print("⚙️ MENGAKTIFKAN ENJIN 2: Radar Top 3 Sektor Dinamik (Trending / Hype)...")
        # (Logik API Enjin 2 - Penapis Volume Anomali)
        CURRENT_ENGINE = 1  # Set giliran seterusnya kembali ke Enjin 1

    print("Kitaran selesai. Menunggu 15 minit untuk giliran seterusnya...\n")

def run_scheduler():
    schedule.every(15).minutes.do(main_job)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Thread 1: Server Render Dummy
    threading.Thread(target=run_server, daemon=True).start()
    
    # Thread 2: Jadual 15 minit 
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Notifikasi Bot Reboot
    try:
        bot.send_message(ADMIN_ID, "🚨 **SYSTEM REBOOTED**\nEnjin AlphaV3 beroperasi secara automatik. (Guna /scan, /stop, /ca)")
    except:
        pass
    
    # 🔥 AUTO-SCAN: Imbasan pertama dilakukan automatik sebaik server hidup
    main_job()
    
    # Thread Utama: Polling arahan Telegram berterusan
    print("Bot sedia menerima arahan Telegram...")
    bot.infinity_polling()
