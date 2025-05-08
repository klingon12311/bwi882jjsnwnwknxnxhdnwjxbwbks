import json
import time
import random
import requests
from colorama import init, Fore
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed

init(autoreset=True)

API_PROXIES = [
    "https://damp-wind-eb32.slaungther1231.workers.dev/?url=https://api.solixdepin.net/api",
    "https://testpoint1.vercel.app/proxy?url=https://api.solixdepin.net/api"
]

DELAY_BETWEEN_TASKS = 2
DELAY_BETWEEN_ACCOUNTS = 2
MAX_RETRIES = 3
MAX_LOGIN_ATTEMPTS = 3
THREADS = 20

ua = UserAgent()


def load_accounts():
    try:
        with open('hasil.txt') as f:
            lines = f.read().splitlines()
            return [{"email": line.split(':')[0], "password": line.split(':')[1]} for line in lines if ':' in line]
    except Exception as e:
        print(f"{Fore.RED}Gagal baca hasil.txt: {e}")
        return []


def login(email, password, user_agent, base_url):
    for attempt in range(MAX_LOGIN_ATTEMPTS):
        try:
            res = requests.post(
                f"{base_url}/auth/login-password",
                headers={"Content-Type": "application/json", "User-Agent": user_agent},
                json={"email": email, "password": password},
                timeout=2
            )
            if res.status_code in (200, 201):
                return res.json().get("data", {}).get("accessToken")
        except:
            pass
    return None


def get_balance(session):
    try:
        res = session.get("https://api.solixdepin.net/api/point/get-total-point", timeout=2)
        return res.json().get("data", {}).get("total", 0)
    except:
        return 0


def get_tasks(session, base_url):
    try:
        res = session.get(f"{base_url}/task/get-user-task", timeout=2)
        tasks = res.json().get('data', [])
        return [{"id": t["_id"], "name": t.get("name", "Unknown Task")} for t in tasks]
    except:
        return []


def process_task(session, task, base_url):
    for _ in range(MAX_RETRIES):
        try:
            session.post(f"{base_url}/task/do-task", json={"taskId": task["id"]}, timeout=2)
            claim = session.post(f"{base_url}/task/claim-task", json={"taskId": task["id"]}, timeout=2)
            if claim.status_code in (200, 201):
                return True
        except:
            pass
        time.sleep(DELAY_BETWEEN_TASKS)
    return False


def process_account(account, index, total):
    base_url = random.choice(API_PROXIES)  # URL random tiap akun
    user_agent = ua.random
    email_short = f"{account['email'][:3]}***{account['email'].split('@')[0][-2:]}"

    token = login(account["email"], account["password"], user_agent, base_url)
    if not token:
        print(f"[{index}/{total}] {email_short} | ❌ Login gagal")
        return

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    })

    awal = get_balance(session)
    tasks = get_tasks(session, base_url)
    berhasil = 0

    for task in tasks:
        if process_task(session, task, base_url):
            berhasil += 1
        time.sleep(DELAY_BETWEEN_TASKS)

    akhir = get_balance(session)
    earned = akhir - awal

    print(f"[{index}/{total}] {email_short} | ✅ Login | Task: {berhasil}/{len(tasks)} | +{earned:.2f} | Total: {akhir:.2f}")


def main_loop():
    base_accounts = load_accounts()
    if not base_accounts:
        print(f"{Fore.RED}Tidak ada akun ditemukan.")
        return

    while True:
        accounts = base_accounts[:]
        random.shuffle(accounts)
        total = len(accounts)

        print(f"{Fore.CYAN}\nMulai loop baru...\n")
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = []
            for i, acc in enumerate(accounts):
                futures.append(executor.submit(process_account, acc, i + 1, total))
                time.sleep(DELAY_BETWEEN_ACCOUNTS)
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"{Fore.RED}Thread error: {e}")
        print(f"{Fore.YELLOW}\nSelesai 1 loop. Ulangi setelah 10 detik...\n")
        time.sleep(10)


if __name__ == "__main__":
    main_loop()