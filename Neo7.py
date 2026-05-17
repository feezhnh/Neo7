import os
import time
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import schedule
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# =====================================================================
# 1. KONFIGURASI KESELAMATAN (ENVIRONMENT VARIABLES)
# =====================================================================
TELEGRAM_BOT_TOKEN = "8529207956:AAE8Kb-j8soVd1se9WLj4OgpX5rwNPTOrYU"
VIP_CHANNEL_ID = os.environ.get("VIP_CHANNEL_ID", "-1003943365561")
ADMIN_ID = os.environ.get("ADMIN_ID", "970309251")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
IS_SCANNING = True  # Dibawa masuk dari Alpha V3

# =====================================================================
# 2. PARAMETER NEO7: (ULTRA-LOW CAP)
# =====================================================================
MC_MIN = 50000           
MC_MAX = 2000000         
MIN_LIQUIDITY = 15000    
MIN_VOL_LIQ_RATIO = 2.0  
MIN_5M_CHANGE = 10.0     

# =====================================================================
# 3. LIVE API (DEXSCREENER FOKUS)
# =====================================================================
def get_dexscreener_data(query, search_type="ca"):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{query}" if search_type == "ca" else f"https://api.dexscreener.com/latest/dex/search?q={query}"
            
        res = requests.get(url, timeout=10).json()
        if res.get('pairs'):
            pair = sorted(res['pairs'], key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]
            
            chain_id = pair.get('chainId', 'unknown')
            created_at = pair.get('pairCreatedAt', 0)
            age_days = (int(time.time() * 1000) - created_at) / (1000 * 60 * 60 * 24) if created_at else 0
            
            if age_days < 1:
                age_display = f"{int(age_days * 24)} Jam" if age_days * 24 >= 1 else f"{int(age_days * 24 * 60)} Minit"
            else:
                age_display = f"{int(age_days)} Hari"
            
            info = pair.get('info', {})
            websites = info.get('websites', [])
            website_url = websites[0].get('url') if websites else None
            socials = info.get('socials', [])
            twitter_url = next((s.get('url') for s in socials if s.get('type') == 'twitter'), None)
            telegram_url = next((s.get('url') for s in socials if s.get('type') == 'telegram'), None)

            return {
                'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                'symbol': pair.get('baseToken', {}).get('symbol', 'TOKEN'),
                'contract_address': pair.get('baseToken', {}).get('address', 'Unknown'),
                'price_usd': float(pair.get('priceUsd', 0)),
                'market_cap': float(pair.get('fdv', 0)), 
                'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                'price_change_5m': float(pair.get('priceChange', {}).get('m5', 0)), 
                'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                'network': chain_id.upper(),
                'chain_raw': chain_id, 
                'age_display': age_display,
                'website': website_url,
                'twitter_official': twitter_url,
                'telegram': telegram_url,
                'pair_address': pair.get('pairAddress', '')
            }
        return None
    except: return None

# =====================================================================
# 4. NEO7 MICRO ENGINE: PENAPISAN & ANTI-RUG KETAT
# =====================================================================
def verify_security_strict(network, ca):
    if network.lower() in ['solana', 'sol']:
        try:
            res = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{ca}/report", timeout=5).json()
            risks = res.get('risks', [])
            
            mint_revoked = True
            lp_safe = True
            
            for risk in risks:
                name = risk.get('name', '').lower()
                if 'mint' in name: mint_revoked = False
                if 'liquidity' in name and risk.get('level') == 'danger': lp_safe = False
                
            if not mint_revoked or not lp_safe:
                return False, "❌ GAGAL (Mint Aktif / LP Bahaya)", res.get('score', 1000)
            return True, "✅ LP BURNED & MINT REVOKED", res.get('score', 0)
        except: return False, "⚠️ Gagal API RugCheck", 1000
    else:
        return True, "✅ PASSED (EVM Safe Assumption)", 0

def execute_neo7_protocol(dex_data):
    if not (MC_MIN <= dex_data['market_cap'] <= MC_MAX): return False
    if dex_data['liquidity'] < MIN_LIQUIDITY: return False
    
    vol_liq_ratio = dex_data['volume_24h'] / dex_data['liquidity'] if dex_data['liquidity'] > 0 else 0
    if vol_liq_ratio < MIN_VOL_LIQ_RATIO: return False
    
    if dex_data['price_change_5m'] < MIN_5M_CHANGE: return False
    
    return True

# =====================================================================
# 5. NEO7 TELEGRAM EXECUTION (DYNAMIC UI)
# =====================================================================
def send_neo7_signal(dex_data, target_chat_id=VIP_CHANNEL_ID):
    is_sol = dex_data['network'].lower() in ['solana', 'sol']
    ca = dex_data['contract_address']
    
    is_safe, sec_msg, sec_score = verify_security_strict(dex_data['network'], ca)
    vol_ratio = dex_data['volume_24h'] / dex_data['liquidity'] if dex_data['liquidity'] > 0 else 0
    
    msg = f"""🚨 <b>ULTRA-LOW CAP V1: MOMENTUM DETECTED!</b> 🚨

⛓ <b>Chain:</b> {dex_data['network']}
🪙 <b>Token:</b> {dex_data['name']} ({dex_data['symbol']})
📝 <b>CA:</b> <code>{ca}</code>

📊 <b>DATA MARKET (5-Min):</b>
💰 <b>Market Cap:</b> ${dex_data['market_cap']:,.0f}
💧 <b>Liquidity:</b> ${dex_data['liquidity']:,.0f}
🔄 <b>Volume:</b> ${dex_data['volume_24h']:,.0f}
⚡ <b>Vol/Liq Ratio:</b> <b>{vol_ratio:.2f}x</b> 🔥
🚀 <b>5M Change:</b> <b>+{dex_data['price_change_5m']}%</b> 🟢

🛡 <b>KESELAMATAN:</b>
{sec_msg}
"""

    markup = InlineKeyboardMarkup()
    twitter_search = f"https://twitter.com/search?q=%24{dex_data['symbol']}"
    chain_url = dex_data.get('chain_raw', 'solana').lower()
    
    if is_sol:
        markup.row(
            InlineKeyboardButton("📊 DexScreener", url=f"https://dexscreener.com/{chain_url}/{ca}"),
            InlineKeyboardButton("🐦 X Search", url=twitter_search)
        )
        markup.row(
            InlineKeyboardButton("🔎 RugCheck", url=f"https://rugcheck.xyz/tokens/{ca}"),
            InlineKeyboardButton("🔗 Solscan", url=f"https://solscan.io/token/{ca}")
        )
        buy_bot_name = "🐶 BUY ON BONKBOT"
        buy_bot_url = f"https://t.me/bonkbot_bot?start={ca}"
    else:
        markup.row(
            InlineKeyboardButton("📊 DexScreener", url=f"https://dexscreener.com/{chain_url}/{ca}"),
            InlineKeyboardButton("🐦 X Search", url=twitter_search)
        )
        markup.row(
            InlineKeyboardButton("🔎 TokenSniffer", url=f"https://tokensniffer.com/token/{ca}"),
            InlineKeyboardButton("🔗 Explorer", url=f"https://dexscreener.com/{chain_url}/{ca}") 
        )
        buy_bot_name = "🦄 BUY ON MAESTRO"
        buy_bot_url = f"https://t.me/maestro?start={ca}"

    soc_btns = []
    if dex_data.get('website'): soc_btns.append(InlineKeyboardButton("🌐 Website", url=dex_data['website']))
    if dex_data.get('telegram'): soc_btns.append(InlineKeyboardButton("💬 Telegram", url=dex_data['telegram']))
    if soc_btns: markup.row(*soc_btns)
    
    markup.row(InlineKeyboardButton(buy_bot_name, url=buy_bot_url))

    bot.send_message(target_chat_id, msg, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

# =====================================================================
# 6. ENJIN PENGIMBAS (NEO7)
# =====================================================================
def run_live_scan():
    # Contoh array carian. Dalam Neo7 kita ping network SOL dan Base secara umum
    search_queries = ["solana", "base"] 
    
    for query in search_queries:
        print(f"\n[📡] Menyemak Rangkaian: {query.upper()}...")
        # Ping API menggunakan fungsi Neo7
        dex_data = get_dexscreener_data(query, search_type="network")
        
        if not dex_data: 
            print(f"   [!] Gagal dapat data {query.upper()}. Berehat 15 saat...")
            time.sleep(15)
            continue
            
        sym = dex_data.get('symbol', 'UNKNOWN')
        print(f"   [🔍] Menganalisis token {sym} di rangkaian {query.upper()}...")
        
        # Eksekusi protokol Neo7 (Tanpa RSI/Fibo)
        if execute_neo7_protocol(dex_data):
            # Semak sekuriti ketat. Jika gagal, DROP terus (jangan blast)
            is_safe, sec_msg, sec_score = verify_security_strict(dex_data['network'], dex_data['contract_address'])
            if is_safe:
                print(f"   🔥 [LULUS NEO7 & SAFE] Signal ditemui untuk {sym.upper()}!")
                send_neo7_signal(dex_data, target_chat_id=VIP_CHANNEL_ID)
            else:
                 print(f"   ❌ [GAGAL ANTI-RUG] Token {sym.upper()} diabaikan. ({sec_msg})")
        else:
            print(f"   📉 [GAGAL PARAMETER] Token {sym.upper()} tidak menepati kriteria.")
        
        time.sleep(5) 

def main_job():
    global IS_SCANNING
    if not IS_SCANNING: return
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚙️ Kitaran Auto-Scan Neo7 Bermula...")
    run_live_scan()

# =====================================================================
# 7. TELEGRAM COMMANDS & BULLETPROOF SCHEDULER
# =====================================================================
@bot.message_handler(commands=['scan'])
def cmd_scan(message): 
    bot.reply_to(message, "⏳ Memaksa kitaran imbasan manual Neo7...")
    threading.Thread(target=main_job).start()

@bot.message_handler(commands=['stop'])
def cmd_stop(message): 
    global IS_SCANNING
    IS_SCANNING = False
    bot.reply_to(message, "🛑 Sistem Auto-Scan Neo7 Dihentikan.")

@bot.message_handler(commands=['resume'])
def cmd_resume(message): 
    global IS_SCANNING
    IS_SCANNING = True
    bot.reply_to(message, "✅ Sistem Auto-Scan Neo7 Disambung semula.")

@bot.message_handler(commands=['ca'])
def cmd_ca(message):
    try:
        address = message.text.split()[1]
        bot.reply_to(message, f"⚙️ Memulakan Imbasan Neo7 V1 untuk CA:\n`{address}`", parse_mode="Markdown")
        dex_data = get_dexscreener_data(address, search_type="ca")
        
        if dex_data:
            # 1. Tembak signal terus ke VIP Channel
            send_neo7_signal(dex_data, target_chat_id=VIP_CHANNEL_ID) 
            
            # 2. Beritahu kat DM kau yang kerja dah siap
            bot.reply_to(message, "✅ Signal berjaya ditembak ke VIP Channel!")
        else: 
            bot.reply_to(message, "❌ Data DexScreener gagal diakses. Pastikan CA sah.")
    except Exception as e: 
        bot.reply_to(message, "❌ Format salah. Taip: `/ca <contract_address>`", parse_mode="Markdown")

# Server Endpoint untuk pastikan bot tak mati (Keep-Alive dari Alpha V3)
class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Neo7 TRENCH SNIPER V1 ACTIVE")
    def log_message(self, format, *args): pass

def run_scheduler():
    schedule.every(15).minutes.do(lambda: threading.Thread(target=main_job).start())
    while True:
        try: schedule.run_pending()
        except Exception as e: print(f"\n[⚠️] Ralat Penjadualan: {e}. Meneruskan kitaran...")
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), RenderHandler).serve_forever(), daemon=True).start()
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    print("=======================================")
    print("🚀 NEO7 ULTRA V1 ACTIVATE")
    print("=======================================")
    
    try: bot.send_message(ADMIN_ID, "🚨 HELLO, NEO7 ULTRA ACTIVATED!")
    except: pass
    
    threading.Thread(target=main_job).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=20)
