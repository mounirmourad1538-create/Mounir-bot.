import os
import warnings
import pandas as pd
import yfinance as yf
import requests
import asyncio
from datetime import datetime, timedelta
import pytz
import nest_asyncio

# كتم الضوضاء
warnings.filterwarnings("ignore")
nest_asyncio.apply()

# ========= [ 1. CONFIGURATION ] =========
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

PAIR_MEMORY = {pair: {'ratio': 1.1, 'wins': 0, 'losses': 0, 'streak': 0} for pair in PAIRS}
SENT_SIGNALS = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

# ========= [ 2. SMART LEARNING ] =========
async def smart_learning(pair, entry_p, sig_type):
    await asyncio.sleep(62)
    try:
        df = await asyncio.to_thread(yf.download, pair, period="1d", interval="1m", progress=False, auto_adjust=True)
        exit_p = float(df['Close'].iloc[-1])
        is_win = (exit_p > entry_p if "CALL" in sig_type else exit_p < entry_p)
        result = "WIN" if is_win else "LOSS"
        
        mem = PAIR_MEMORY[pair]
        if result == "LOSS":
            mem['streak'] += 1
            if mem['streak'] >= 2:
                mem['ratio'] = round(mem['ratio'] + 0.2, 2)
                mem['streak'] = 0
        else:
            mem['streak'] = 0
            
        pd.DataFrame([[datetime.now(CAIRO_TZ), pair, sig_type, entry_p, result, mem['ratio']]]).to_csv(LOG_FILE, mode='a', header=False, index=False)
    except: pass

# ========= [ 3. THE LIVE ENGINE ] =========
async def scan():
    print("🔱 Salvador V61.1 - The Beast is Awake")
    print("--------------------------------------")
    
    while True:
        try:
            now = datetime.now(CAIRO_TZ)
            # تحديث مستمر لكل ثانية عشان تتأكد إنه شغال
            print(f"[{now.strftime('%H:%M:%S')}] 📡 Status: Live Scanning Markets... ", end='\r')
            
            if 40 <= now.second <= 55:
                # سحب البيانات
                data = await asyncio.to_thread(yf.download, tickers=PAIRS, period="1d", interval="1m", progress=False, group_by='ticker', auto_adjust=True, timeout=10)
                
                for pair in PAIRS:
                    try:
                        df = data[pair].dropna()
                        if len(df) < 20: continue
                        
                        my_ratio = PAIR_MEMORY[pair]['ratio']
                        history = df.tail(50)
                        resis, supp = history['High'].max(), history['Low'].min()
                        
                        last = df.iloc[-1]
                        o, h, l, c = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
                        body = max(abs(c - o), 1e-7)
                        u_wick, l_wick = (h - max(o, c)), (min(o, c) - l)
                        
                        signal = None
                        tolerance = 0.0002 
                        
                        if (l <= supp + tolerance) and (l_wick >= body * my_ratio):
                            signal = "CALL ⏫"
                        elif (h >= resis - tolerance) and (u_wick >= body * my_ratio):
                            signal = "PUT ⏬"

                        if signal:
                            sig_id = f"{pair}_{now.strftime('%H:%M')}"
                            if sig_id not in SENT_SIGNALS:
                                next_candle = (now + timedelta(minutes=1)).strftime('%H:%M:00')
                                pair_clean = pair.replace('=X','')
                                
                                msg = (
                                    f"⏳ *إشارة جديدة ({pair_clean})*\n\n"
                                    f"الزوج: {pair_clean}\n"
                                    f"النوع: {signal}\n"
                                    f"التوقيت: {next_candle}\n"
                                    f"المدة: 1 دقيقة"
                                )
                                send_telegram(msg)
                                SENT_SIGNALS[sig_id] = True
                                asyncio.create_task(smart_learning(pair, c, signal))
                    except: continue
                await asyncio.sleep(10) # تجنب التكرار
            
        except:
            pass
        
        await asyncio.sleep(1) # سرعة التحديث كل ثانية

if __name__ == "__main__":
    send_telegram("👹 *الوحش صحي*")
    asyncio.run(scan())
