# main.py

import time
import requests
import pandas as pd
import schedule
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from config import API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# === TEMEL AYARLAR ===
BASE_URL = 'https://api.binance.com'
headers = {'X-MBX-APIKEY': API_KEY}
log_file = "sinyal_log.txt"

# === TELEGRAM MESAJI GÖNDER ===
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print("Telegram gönderim hatası:", response.text)
    except Exception as e:
        print("Telegram Hatası:", e)

# === TÜM USDT PARİTELERİNİ AL ===
def get_usdt_pairs():
    url = f"{BASE_URL}/api/v3/exchangeInfo"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        symbols = data['symbols']
        return [s['symbol'] for s in symbols if 'USDT' in s['symbol'] and s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
    else:
        print("USDT pariteleri alınamadı:", response.text)
        return []

# === 5 DAKİKALIK KLINE VERİSİ AL ===
def get_klines(symbol, interval='5m', limit=100):
    url = f"{BASE_URL}/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    else:
        print(f"{symbol}: Veri alınamadı! Hata: {response.json()}")
        return pd.DataFrame()

# === ANALİZ VE SİNYAL ===
def analyze_and_score(symbol):
    try:
        df = get_klines(symbol)
        if df.empty:
            print(f"{symbol}: VERİ YOK veya RATE LIMIT.")
            return

        close = df['close']
        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        ema_short = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
        ema_long = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
        bb = BollingerBands(close)
        lower_band = bb.bollinger_lband().iloc[-1]
        upper_band = bb.bollinger_hband().iloc[-1]
        current_price = close.iloc[-1]

        score = 0
        score += int(rsi < 30)
        score += int(macd > 0)
        score += int(current_price < lower_band)
        score += int(ema_short > ema_long)

        log = f"\n{symbol} | RSI: {rsi:.2f} | MACD: {macd:.5f} | EMA9: {ema_short:.2f} | EMA21: {ema_long:.2f} | " \
              f"Price: {current_price:.2f} | BB: [{lower_band:.2f} - {upper_band:.2f}] | Score: {score}/4\n"

        if score == 4:
            log += f">>> {symbol} GÜÇLÜ ALIM SİNYALİ ✅\n"
            send_telegram(f"🚨 {symbol} GÜÇLÜ ALIM SİNYALİ!\nFiyat: {current_price:.2f}\nRSI: {rsi:.2f} | MACD: {macd:.5f}")
        elif score == 3:
            log += f">>> {symbol} İYİ ALIM ADAYI ⚠️\n"
        elif rsi < 40 and macd > 0:
            log += f">>> {symbol} ZAYIF ALIM ADAYI 🟡\n"
        else:
            log += "Sinyal Yok\n"

        print(log)
        with open(log_file, "a") as f:
            f.write(log)

    except Exception as e:
        print(f"Hata ({symbol}): {e}")

# === ANA BOT FONKSİYONU ===
def run_bot():
    print("\n🔄 Yeni Tarama Başladı:", time.strftime("%Y-%m-%d %H:%M:%S"))
    symbols = get_usdt_pairs()
    for symbol in symbols:
        analyze_and_score(symbol)
    print("✅ Tarama tamamlandı.\n")

# === DÖNGÜ: 5 DAKİKADA BİR ÇALIŞTIR ===
schedule.every(5).minutes.do(run_bot)

if __name__ == "__main__":
    send_telegram("🤖 Bot başlatıldı! 5 dakikada bir tüm USDT pariteleri taranıyor...")
    run_bot()
    while True:
        schedule.run_pending()
        time.sleep(1)
