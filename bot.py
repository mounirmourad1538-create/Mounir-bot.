import os
import warnings
import pandas as pd
import yfinance as yf
import requests
import asyncio
from datetime import datetime, timedelta
import pytz
import nest_asyncio
import logging

# === [ 1. SILENCE & CLEANUP ] ===
warnings.filterwarnings("ignore")
warnings.simplefilter(action='ignore', category=FutureWarning)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
nest_asyncio.apply()

# ========= [ 2. CONFIGURATION ] =========
BOT_TOKEN = "8005944153:AAEe8ejVtjljarwxHXt0MmxiTqGHtd1Nr8Y"
CHAT_ID = "1682985357"
CAIRO_TZ = pytz.timezone("Africa/Cairo")
LOG_FILE = "smart_classic_log.csv"

PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X",
    "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "CADJPY=X", "CHFJPY=X",
    "EURCAD=X", "GBPCAD=X", "AUDCAD=X", "CADCHF=X", "EURGBP=X",
    "EURAUD=X", "GBPAUD=X", "GC=F"
]

PAIR_MEMORY = {}
for pair in PAIRS:
    initial_r = 1.3 if "GC=F" in pair else 1.1
    PAIR_MEMORY[pair] = {'ratio': initial_r, 'wins': 0, 'losses': 0, 'streak': 0}

SENT_SIGNALS = {}

if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["time", "pair", "type", "entry", "result", "ratio"]).to_csv(LOG_FILE, index=False)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

# ========= [ 3. BACKGROUND AI LEARNING ] =========
async def smart_learning(pair, entry_p, sig_type):
    await asyncio.sleep(62)
    try:
        df = await asyncio.to_thread(yf.download, pair, period="1d", interval="1m", progress=False, auto_adjust=True)
        exit_p = float(df['Close'].iloc[-1])
        is_win = (exit_p > entry_p if "UP" in sig_type else exit_p < entry_p)
        result = "WIN" if is_win else "LOSS"
        
        mem = PAIR_MEMORY[pair]
        current_r = mem['ratio']
        
        if result == "LOSS":
            mem['losses'] += 1
            mem['streak'] += 1
            if mem['streak'] >= 2:
                mem['ratio'] = round(current_r + 0.2, 2)
                mem['streak'] = 0 
        else:
            mem['wins'] += 1
            mem['streak'] = 0
            
        pd.DataFrame([[datetime.now(CAIRO_TZ), pair, sig_type, entry_p, result, current_r]]).to_csv(LOG_FILE, mode='a', header=False, index=False)
    except: pass

# ========= [ 4. THE CLEAN ENGINE ] =========
async def scan():
    print("🔱 Salvador V61.0 Started - Console is Clean.")
    
    while True:
        try:
            now = datetime.now(CAIRO_TZ)
            print(f"[{now.strftime('%H:%M:%S')}] 📡 Scanning Market...", end='\r')
            
            if 40 <= now.second <= 55:
                data = await asyncio.to_thread(yf.download, tickers=PAIRS, period="1d", interval="1m", progress=False, group_by='ticker', auto_adjust=True, timeout=10)
                
                for pair in PAIRS:
                    try:
                        df = data[pair].dropna()
                        if len(df) < 30: continue
                        
                        my_ratio = PAIR_MEMORY[pair]['ratio']
                        history = df.tail(50)
                        resis, supp = history['High'].max(), history['Low'].min()
                        
                        last = df.iloc[-1]
                        o, h, l, c = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
                        body = max(abs(c - o), 1e-7)
                        u_wick, l_wick = (h - max(o, c)), (min(o, c) - l)
                        
                        signal = None
                        direction = ""
                        tolerance = 0.0002 
                        
                        if (l <= supp + tolerance) and (l_wick >= body * my_ratio):
                            signal = "UP⬆️"
                        elif (h >= resis - tolerance) and (u_wick >= body * my_ratio):
                            signal = "DOWN⬇️"

                        if signal:
                            sig_id = f"{pair}_{now.strftime('%H:%M')}"
                            if sig_id not in SENT_SIGNALS:
                                next_candle_time = (now + timedelta(minutes=1)).strftime('%H:%M')
                                pair_clean = "GOLD (XAUUSD)" if "GC=F" in pair else pair.replace('=X','').replace('/', '-')
                                
                                # ---[ الرسالة المطلوبة بالظبط ]---
                                msg = (
                                    f"📊 صفقة جديدة the beast🌟:\n\n"
                                    f"{pair_clean} | M1 | {next_candle_time} | {signal}"
                                )
                                # ----------------------------
                                
                                send_telegram(msg)
                                SENT_SIGNALS[sig_id] = True
                                asyncio.create_task(smart_learning(pair, c, signal))
                    except: continue
                
                await asyncio.sleep(10)
            
        except:
            await asyncio.sleep(1)
        
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    send_telegram("The beast is awake")
    asyncio.run(scan())
