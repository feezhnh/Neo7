# -*- coding: utf-8 -*-
import os
import sys
import time
import requests
import telebot
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==========================================
# 1. DUMMY SERVER (PENGHALANG ERROR 501/409)
# ==========================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Neo7 System is LIVE!")
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 3000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

Thread(target=run_server, daemon=True).start()

# ==========================================
# 2. CONFIG & CODENAME: NEO7 SYSTEMS
# ==========================================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN tidak dijumpai dalam Environment Variables Render!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

# HARDCODED ADMIN SETTING FOR SYSTEM AUTOMATION
ADMIN_CHAT_ID = 970309251
is_scanning = True  # AUTOMATIC ACTIVE ON BOOT
sent_signals = set()
sep_line = "\u2501" * 19 # Solid divider line

# ==========================================
# 🔥 THE ULTIMATE SWEET SPOT PARAMETERS
# ==========================================
RULES = {
    "minMC": 80000,         # Minimum $80k (Tangkap fasa awal jerung)
    "maxMC": 2000000,       # Siling 2M kekal
    "minLiqUSD": 10000,     # Lantai USD 10k (Elak slippage)
    "minLiqRatio": 0.10,    # Ratio Minimum 10%
    "minVolMCRatio": 0.50,  # RVOL Minimum 0.5x
    "buyVolPressure": 0.55, # Minimum 55% Bids
    "maxTop10Holders": 15   # Anti-Whale Limit 15%
}

print("🟢 [SYSTEM] Neo7 Engine Initialized & Booted Successfully.")

# ==========================================
# 3. NOTIFIKASI AUTO-STARTUP (RENDER BOOT)
# ==========================================
def send_startup_alert():
    try:
        time.sleep(5)  # Beri masa bot engine stabil
        startup_msg = (
            "⚙️ **[SISTEM NEO7] PELAYAN DIHIDUPKAN**\n\n"
            "Sistem Neo7 telah memulakan but automatik.\n"
            "• **Sasaran Rangkaian:** Solana & Base\n"
            "• **Parameter Sweet Spot:** MC $80k-$2M | Liq > $10k\n"
            "• **Enjin Auto-Scan 15-minit:** 🟢 AKTIF\n\n"
            "_Sistem kini memantau pasaran tanpa henti. Tiada tindakan lanjut diperlukan._"
        )
        bot.send_message(ADMIN_CHAT_ID, startup_msg, parse_mode="Markdown")
        print(f"✅ [ALERT] Startup notification successfully sent to Admin ID: {ADMIN_CHAT_ID}")
    except Exception as e:
        print(f"❌ [ALERT ERROR] Gagal hantar startup alert: {e}")

Thread(target=send_startup_alert, daemon=True).start()

# ==========================================
# 4. DATA-DRIVEN INTERFACES (ON-CHAIN API)
# ==========================================
def fetch_dex_pair_data(address):
    try:
        res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{address}", timeout=10).json()
        if not res.get("pairs"): return None
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
        
        # Keselamatan Tegar: Jika ada perkataan ini dalam risks, REJECT.
        is_mintable = any(["Mintable" in r.get("name", "") for r in risks])
        is_freezable = any(["Freeze" in r.get("name", "") for r in risks])
        is_lp_unlocked = any(["Low Liquidity Locked" in r.get("name", "") for r in risks])
        
        passed = not is_mintable and not is_freezable and not is_lp_unlocked and (top10_pct <= RULES["maxTop10Holders"])
        return {"passed": passed, "top10": f"{top10_pct:.2f}"}
    except:
        return {"passed": False}

def audit_evm_goplus(address, chain_str):
    chain_id = '8453' if chain_str == 'base' else '1'
    try:
        res = requests.get(f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}", timeout=10).json()
        data = res.get("result", {}).get(address.lower())
        if not data: return {"passed": False}
        
        is_honeypot = data.get("is_honeypot") == "1"
        buy_tax = float(data.get("buy_tax", 0))
        sell_tax = float(data.get("sell_tax", 0))
        # Sebahagian token baru open source lambat sikit, kita longgarkan sikit syarat open source tapi ketatkan honeypot
        
        passed = not is_honeypot and buy_tax < 0.10 and sell_tax < 0.10
        return {"passed": passed, "buyTax": f"{buy_tax*100:.1f}", "sellTax": f"{sell_tax*100:.1f}"}
    except:
        return {"passed": False}

# ==========================================
# 5. CORE 3-LAYER SELECTION PIPELINE
# ==========================================
def execute_pipeline(address, chat_id, is_manual=False):
    token = fetch_dex_pair_data(address)
    if not token: 
        print(f"   ❌ REJECT: Tiada data pasaran untuk CA: {address[:8]}...")
        return {"status": "rejected", "msg": "Tiada data pasaran."}
    
    symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
    chain = token.get("chainId", "UNKNOWN").upper()
    mc = token.get("marketCap") or token.get("fdv") or 0
    liq = token.get("liquidity", {}).get("usd", 0)
    vol24h = token.get("volume", {}).get("h24", 0)
    
    print(f"🔍 [MENGIMBAS] {symbol} ({chain}) | MC: ${mc:,.0f} | Liq: ${liq:,.0f}")
    
    # LAYER 1: STRICT ON-CHAIN FUNDAMENTALS
    if not (RULES["minMC"] <= mc <= RULES["maxMC"]): 
        print(f"   ❌ REJECT: Lapis 1 - Market Cap luar radar.")
        return {"status": "rejected", "msg": "Lapis 1: Market Cap luar radar."}
    if liq < RULES["minLiqUSD"]: 
        print(f"   ❌ REJECT: Lapis 1 - Liquidity Depth terlalu nipis (<$10k).")
        return {"status": "rejected", "msg": "Lapis 1: Liquidity Depth terlalu nipis."}
    if mc == 0 or (liq / mc) < RULES["minLiqRatio"]: 
        print(f"   ❌ REJECT: Lapis 1 - Liquidity/MC Ratio gagal (<10%).")
        return {"status": "rejected", "msg": "Lapis 1: Liquidity/MC Ratio gagal."}
    if mc == 0 or (vol24h / mc) < RULES["minVolMCRatio"]: 
        print(f"   ❌ REJECT: Lapis 1 - Active RVOL di bawah paras standard (<0.5x).")
        return {"status": "rejected", "msg": "Lapis 1: Active RVOL di bawah paras standard."}
    
    # LAYER 2: INTERFACES DOMINANCE ANALYSIS
    buys = token.get("txns", {}).get("m5", {}).get("buys", 1)
    sells = token.get("txns", {}).get("m5", {}).get("sells", 1)
    total_txns = buys + sells
    buy_pressure = buys / total_txns if total_txns > 0 else 0
    
    if buy_pressure < RULES["buyVolPressure"]: 
        print(f"   ❌ REJECT: Lapis 2 - Order Flow Dominance lemah ({buy_pressure*100:.0f}% Bids).")
        return {"status": "rejected", "msg": f"Lapis 2: Order Flow Dominance lemah ({buy_pressure*100:.0f}%)."}
    
    # LAYER 3: CONTRACT INTEGRITY AUDIT
    if chain.lower() == "solana":
        sec = audit_solana_rugcheck(address)
        if not sec["passed"]: 
            print(f"   ❌ REJECT: Lapis 3 - Gagal RugCheck (Risiko Kritikal dikesan).")
            return {"status": "rejected", "msg": "Lapis 3: Gagal Saringan Security Contract (RugCheck)."}
        security_breakdown = f"• **Contract Risks:** ✅ Tiada Risiko Kritikal (Mint/Freeze/LP Selamat)\n• **Top 10 Wallets:** ✅ {sec['top10']}%"
    else:
        sec = audit_evm_goplus(address, chain.lower())
        if not sec["passed"]: 
            print(f"   ❌ REJECT: Lapis 3 - Gagal GoPlus (Honeypot / Tax tinggi).")
            return {"status": "rejected", "msg": "Lapis 3: Gagal Saringan Security Contract (GoPlus)."}
        security_breakdown = f"• **Honeypot Risk:** ✅ Bebas Ancaman\n• **Buy/Sell Tax:** ✅ {sec['buyTax']}% / {sec['sellTax']}%"
        
    # MOMENTUM DATA-DRIVEN LOGIC (Replaces Fake Fibo/RSI)
    price_change_5m = token.get("priceChange", {}).get("m5", 0)
    
    if price_change_5m > 5.0:
        verdict_tag = "[🔥 STRONG BUY]"
        trend_status = "🚀 Breakout Phase (Pacak)"
        verdict_text = f"Momentum belian sangat agresif disokong dengan kemasukan volume yang padat. Harga sedang mencetak kenaikan (+{price_change_5m:.1f}%). Setup sesuai untuk momentum ride pantas (scalping)."
    elif 0 <= price_change_5m <= 5.0:
        verdict_tag = "[🔥 STRONG BUY]"
        trend_status = "📈 Konsolidasi / Pemulihan Uptrend"
        verdict_text = f"Aliran wang pintar sedang mengumpul momentum secara berperingkat (+{price_change_5m:.1f}%). Zon entry yang ideal dan selamat sebelum penembusan harga (breakout) berskala besar."
    else:
        # Tahan seketika jika price action terlalu negatif untuk elak tangkap pisau yang terlalu tajam
        if price_change_5m < -15.0 and not is_manual:
            print(f"   ⏳ HOLDING: Harga menjunam terlalu teruk ({price_change_5m}%). Risiko tinggi.")
            return {"status": "holding", "msg": "Menunggu kejatuhan harga reda."}
            
        verdict_tag = "[⏳ ACCUMULATE]"
        trend_status = "⏳ Penurunan (Dip) - Mencari Sokongan"
        verdict_text = f"Harga sedang membuat retracement ({price_change_5m:.1f}%) walaupun metrik fundamental (MC/Liq) sangat sihat. Sesuai untuk teknik tangkap bottom (DCA) bagi meminimumkan risiko entry."
    
    base_addr = token["baseToken"]["address"]
    if base_addr in sent_signals: 
        print(f"   ⚠️ SKIP: Token {symbol} sudah pernah dihantar sebelum ini.")
        return {"status": "approved"}
    
    sent_signals.add(base_addr)
    
    # DYNAMIC SMART ROUTER LINKING
    if chain.lower() == "solana":
        router_link = f"[🐶 BonkBot Sniper](https://t.me/bonkbot_bot?start=ref_custom_{base_addr})"
        monitor_links = (
            f"[📊 Dexscreener](https://dexscreener.com/solana/{base_addr}) | "
            f"[🦅 BirdEye](https://birdeye.so/token/{base_addr}?chain=solana)\n"
            f"[🛡️ RugCheck](https://rugcheck.xyz/tokens/{base_addr}) | "
            f"[📱 Bubblemaps](https://bubblemaps.io/solana/token/{base_addr})"
        )
    else:
        router_link = f"[🦄 Maestro Bot](https://t.me/maestro?start={base_addr})"
        monitor_links = (
            f"[📊 Dexscreener](https://dexscreener.com/base/{base_addr}) | "
            f"[🦅 DEXTools](https://www.dextools.io/app/en/base/pair-explorer/{base_addr})\n"
            f"[🛡️ GoPlus](https://gopluslabs.io/token-security/8453/{base_addr}) | "
            f"[📱 Bubblemaps](https://bubblemaps.io/base/token/{base_addr})"
        )
    
    # 📌 FORMAT TELEGRAM V4
    msg_output = f"**{verdict_tag} {token['baseToken']['name']} (${symbol}) - {chain}**\n"
    msg_output += f"{sep_line}\n"
    msg_output += f"**📜 Contract Address:**\n`{base_addr}`\n\n"
    msg_output += f"**📊 On-Chain Fundamentals:**\n"
    msg_output += f"• **Market Capitalization:** ${mc:,}\n"
    msg_output += f"• **Liquidity Depth:** ${liq:,}\n"
    msg_output += f"• **Volume/MC Ratio:** {(vol24h/mc):.2f}x\n"
    msg_output += f"• **Order Flow Dominance (5m):** {buy_pressure*100:.0f}% Bids\n\n"
    msg_output += f"**🛡️ Contract Integrity:**\n{security_breakdown}\n\n"
    msg_output += f"**📈 Market Momentum (5-Min):**\n"
    msg_output += f"• **Price Action:** {price_change_5m:+.1f}%\n"
    msg_output += f"• **Trend Status:** {trend_status}\n\n"
    msg_output += f"> **💡 Verdict:** {verdict_text}\n\n"
    msg_output += f"**⚡ PANTAS BELI:** {router_link}\n"
    msg_output += f"**🔍 PEMANTAUAN:**\n{monitor_links}\n"
    msg_output += f"{sep_line}\n"
    msg_output += f"_© 2026 Neo7 Premium Radar_"
    
    bot.send_message(chat_id, msg_output, parse_mode="Markdown", disable_web_page_preview=True)
    print(f"   ✅ APPROVED: Isyarat {verdict_tag} dihantar ke Telegram!")
    return {"status": "approved"}

# ==========================================
# 6. HIGH-PERFORMANCE SMART SCANNER CRON
# ==========================================
def smart_cron_scanner():
    global is_scanning
    while True:
        if is_scanning:
            try:
                print("\n⏳ [AUTO-SCAN] Pusingan 15-minit bermula. Menyedut data pasaran Dexscreener...")
                res = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
                if res:
                    filtered_targets = [t for t in res[:50] if t.get("chainId") in ['solana', 'base']]
                    
                    found_any = False
                    for item in filtered_targets[:20]:
                        addr = item.get("tokenAddress")
                        if addr and addr not in sent_signals:
                            result = execute_pipeline(addr, ADMIN_CHAT_ID)
                            if result["status"] == "approved":
                                found_any = True
                            time.sleep(2)  # Pencegah sekatan Rate Limit API
                    
                    if not found_any:
                        print("⚠️ [AUTO-SCAN] Selesai. Tiada token melepasi spec Sweet Spot pada pusingan ini.")
            except Exception as e:
                print(f"❌ [AUTO-SCAN ERROR] Ralat sistem: {e}")
                pass
        time.sleep(15 * 60)

Thread(target=smart_cron_scanner, daemon=True).start()

# ==========================================
# 7. TELEGRAM PANEL CONTROL INTERFACE
# ==========================================
@bot.message_handler(commands=['start', 'resume'])
def cmd_start(message):
    global is_scanning
    if message.chat.id != ADMIN_CHAT_ID: return
    is_scanning = True
    bot.reply_to(message, "🟢 **Enjin Neo7 Diaktifkan.** Imbasan menumpukan ekosistem Solana & Base secara automatik...", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global is_scanning
    if message.chat.id != ADMIN_CHAT_ID: return
    is_scanning = False
    bot.reply_to(message, "🛑 **Enjin Neo7 Dihentikan.**", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if message.chat.id != ADMIN_CHAT_ID: return
    status_str = "🟢 AKTIF (Auto-scanning)" if is_scanning else "🛑 BERHENTI"
    
    msg = f"**📊 STATUS ENJIN NEO7 PREMIUM**\n"
    msg += f"{sep_line}\n"
    msg += f"• **Status Operasi:** {status_str}\n"
    msg += f"• **Admin Target ID:** `{ADMIN_CHAT_ID}`\n"
    msg += f"• **Jumlah Memori Isyarat:** {len(sent_signals)} token\n"
    msg += f"• **Ekosistem Radar:** Solana & Base\n"
    msg += f"{sep_line}"
    
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['scan'])
def cmd_scan(message):
    if message.chat.id != ADMIN_CHAT_ID: return
    bot.reply_to(message, "⚙️ **Manual Scan Triggered.** Semak terminal log pelayan untuk laporan imbasan secara live.", parse_mode="Markdown")
    print("\n🚀 [MANUAL-SCAN] Diaktifkan oleh Admin.")
    found_any = False
    try:
        res = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
        filtered_targets = [t for t in res[:50] if t.get("chainId") in ['solana', 'base']]
        
        for item in filtered_targets[:20]:
            result = execute_pipeline(item.get("tokenAddress"), ADMIN_CHAT_ID, is_manual=True)
            if result["status"] == "approved":
                found_any = True
            time.sleep(1.5)
        
        if not found_any:
            bot.send_message(ADMIN_CHAT_ID, "⚠️ **Laporan:** Tiada token Solana/Base yang melepasi Lapis Keselamatan & Liquidity >$10k pada masa ini.", parse_mode="Markdown")
            print("⚠️ [MANUAL-SCAN] Selesai. Tiada hasil tangkapan.")
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, "❌ **Ralat sambungan API Dexscreener.**", parse_mode="Markdown")
        print(f"❌ [MANUAL-SCAN ERROR] {e}")

@bot.message_handler(commands=['ca'])
def cmd_ca(message):
    if message.chat.id != ADMIN_CHAT_ID: return
    address = message.text.replace('/ca', '').strip()
    if not address:
        bot.reply_to(message, "**Sila masukkan Contract Address (CA)!**", parse_mode="Markdown")
        return
    loading = bot.reply_to(message, f"🔍 **Mengimbas CA:** `{address}`...", parse_mode="Markdown")
    print(f"\n🎯 [MANUAL CA AUDIT] Mengimbas: {address}")
    res = execute_pipeline(address, ADMIN_CHAT_ID, is_manual=True)
    
    if res["status"] == "rejected":
        bot.edit_message_text(f"❌ **REJECTED**\n**CA:** `{address}`\n**Sebab:** {res.get('msg', 'Gagal saringan.')}", chat_id=ADMIN_CHAT_ID, message_id=loading.message_id, parse_mode="Markdown")
    else:
        bot.delete_message(chat_id=ADMIN_CHAT_ID, message_id=loading.message_id)

bot.infinity_polling()
