import os
import sys
import time
import random
import argparse
import datetime
import warnings
import re
from colorama import init, Fore, Style
from dotenv import load_dotenv

from nilly_client import NillyClient, CONFIG, EXPLORER

# Suppress internal warnings
warnings.filterwarnings('ignore')

# Initialize colorama
init(autoreset=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def strip_ansi(s: str) -> str:
    return ANSI_REGEX.sub('', s)

def visible_len(s: str) -> int:
    return len(strip_ansi(s))

def pad_cell(text: str, width: int, align: str = 'left') -> str:
    v = visible_len(text)
    pad = max(0, width - v)
    if align == 'center':
        l = pad // 2
        r = pad - l
        return ' ' * l + text + ' ' * r
    elif align == 'right':
        return ' ' * pad + text
    else:
        return text + ' ' * pad

def print_box(lines: list, border_color: str = Fore.CYAN, width: int = 75):
    inner_w = width - 4
    bar = "═" * (width - 2)
    print(f"{border_color}╔{bar}╗{Style.RESET_ALL}")
    for l in lines:
        p = max(0, inner_w - visible_len(l))
        print(f"{border_color}║{Style.RESET_ALL} {l}{' ' * p} {border_color}║{Style.RESET_ALL}")
    print(f"{border_color}╚{bar}╝{Style.RESET_ALL}")

BANNER = f"""{Fore.CYAN}
╔═════════════════════════════════════════════════════════════════════════╗
║   _   __ _  __ __          ___          __                              ║
║  / | / /(_)/ // /__  __   /   |  __  __/ /_____                         ║
║ /  |/ // // // // / / /  / /| | / / / / __/ __ \                        ║
║/ /|  // // // // /_/ /  / ___ |/ /_/ / /_/ /_/ /                        ║
║/_/ |_//_//_//_/ \__, /  /_/  |_|\__,_/\__/\____/                        ║
║                /____/                                                   ║
║   {Fore.GREEN}● Nilly Testnet Auto Bot (Cross-Farming){Fore.CYAN} │  {Fore.YELLOW}LayerZero Eco / nilly.fun{Fore.CYAN} ║
║   {Fore.WHITE}● Auto-Referral & Auto-Claim Fees{Fore.CYAN}      │  {Fore.MAGENTA}Recycle System: ACTIVE{Fore.CYAN}      ║
╚═════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}"""

FAUCET_INFO = f"""
{Fore.CYAN}╔═══════════════════════ DAFTAR FAUCET BASE SEPOLIA ══════════════════════╗{Fore.RESET}
  {Fore.WHITE}Nilly berjalan di jaringan Base Sepolia testnet (Chain ID: 84532).
  Setiap wallet membutuhkan sedikit Base Sepolia ETH untuk gas & transaksi.

  {Fore.GREEN}[1] QuickNode      :{Fore.CYAN} https://faucet.quicknode.com/base/sepolia
  {Fore.GREEN}[2] Superchain     :{Fore.CYAN} https://console.optimism.io/faucet {Fore.WHITE}(Pilih Base Sepolia)
  {Fore.GREEN}[3] Alchemy        :{Fore.CYAN} https://www.alchemy.com/faucets/base-sepolia
  {Fore.GREEN}[4] Coinbase CDP   :{Fore.CYAN} https://portal.cdp.coinbase.com/onchain-tools/faucet
  {Fore.GREEN}[5] Google Web3    :{Fore.CYAN} https://cloud.google.com/application/web3/faucet/ethereum/sepolia
                       {Fore.YELLOW}↳ Dapatkan Sepolia ETH lalu bridge lewat https://superbridge.app/base-sepolia

  {Fore.YELLOW}💡 Tips: Saldo 0.001 ETH sudah cukup untuk garap harian selama 80+ hari!
{Fore.CYAN}╚═════════════════════════════════════════════════════════════════════════╝{Fore.RESET}
"""

def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")

def log_info(msg: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.CYAN}[INFO]   {Style.RESET_ALL} {msg}")

def log_success(msg: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.GREEN}{Style.BRIGHT}[SUCCESS]{Style.RESET_ALL} {Fore.GREEN}{msg}{Style.RESET_ALL}")

def log_warn(msg: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.YELLOW}[WARN]   {Style.RESET_ALL} {Fore.YELLOW}{msg}{Style.RESET_ALL}")

def log_error(msg: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.RED}{Style.BRIGHT}[ERROR]  {Style.RESET_ALL} {Fore.RED}{msg}{Style.RESET_ALL}")

def log_step(cur: int, tot: int, title: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.MAGENTA}[STEP]   {Style.RESET_ALL} [{cur}/{tot}] {Style.BRIGHT}{title}{Style.RESET_ALL}")

def log_tx(tx_hash: str):
    print(f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.BLUE}[TX]     {Style.RESET_ALL} ↳ {Fore.WHITE}Explorer:{Fore.RESET} {EXPLORER}/tx/{tx_hash}")

def countdown_sleep(seconds: int, msg: str = "Menunggu wallet berikutnya"):
    for remaining in range(seconds, 0, -1):
        line = f"{Fore.BLACK}{Style.BRIGHT}[{now_str()}]{Style.RESET_ALL} {Fore.MAGENTA}[WAIT]   {Style.RESET_ALL} {msg}: {Fore.YELLOW}{remaining}s{Fore.RESET}"
        sys.stdout.write(f"\r{line}   ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write(f"\r{' ' * 85}\r")
    sys.stdout.flush()

def load_wallets():
    keys = []
    wallets_file = os.path.join(BASE_DIR, 'wallets.txt')
    if os.path.exists(wallets_file):
        with open(wallets_file, 'r') as f:
            for line in f:
                k = line.strip()
                if k and not k.startswith("#"):
                    keys.append(k)

    env_keys = os.getenv("PRIVATE_KEYS") or os.getenv("PRIVATE_KEY")
    if env_keys:
        for k in env_keys.split(','):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)

    return keys

def get_config_values():
    rpc = os.getenv("RPC_URL", CONFIG.get("rpc", "https://sepolia.base.org"))
    trade_amount = float(os.getenv("TRADE_AMOUNT_ETH", "0.00011"))
    return rpc, trade_amount

def collect_pool_coins(clients: list) -> list:
    """Collect coins created by our pool wallets to cross-trade."""
    pool_coins = []
    for c in clients:
        try:
            prof = c.get_profile()
            for coin in prof.get("created", []):
                pool_coins.append({
                    "token": coin.get("token"),
                    "market": coin.get("market"),
                    "symbol": coin.get("symbol"),
                    "name": coin.get("name"),
                    "creator": c.address.lower()
                })
        except Exception:
            pass
    return pool_coins

def show_wallet_status(client: NillyClient, idx: int = 1, total: int = 1):
    bal = client.get_balance()
    prof = client.get_profile()

    pts = prof.get("points", 0)
    rank = prof.get("rank", "-")
    wallets_count = prof.get("wallets", "-")
    rank_str = f"#{rank} / {wallets_count}" if rank else "Belum Masuk"

    lines = [
        f"{Fore.WHITE}Wallet [{idx}/{total}]: {Fore.YELLOW}{client.address}{Fore.RESET}",
        f"{Fore.WHITE}Saldo : {Fore.GREEN}{bal:.6f} ETH{Fore.CYAN}  │  {Fore.WHITE}Poin: {Fore.MAGENTA}{pts} pts{Fore.CYAN}  │  {Fore.WHITE}Rank: {Fore.CYAN}{rank_str}{Fore.RESET}"
    ]
    print()
    print_box(lines)

    items = prof.get("items", [])
    if items:
        print(f" {Fore.WHITE}{Style.BRIGHT}Status Misi Checklist:{Fore.RESET}")
        for item in items:
            done = item.get("done", 0)
            mx = item.get("max", 1)
            earned = item.get("earned", 0)
            if done >= mx:
                icon = f"{Fore.GREEN}✔ Selesai{Fore.RESET}"
            elif done > 0:
                icon = f"{Fore.CYAN}↻ {done}/{mx}{Fore.RESET}"
            else:
                icon = f"{Fore.BLACK}{Style.BRIGHT}○ 0/{mx}{Fore.RESET}"
            ic = pad_cell(icon, 12, 'left')
            lb = pad_cell(item.get('label', ''), 42, 'left')
            pt = pad_cell(f"{earned} pts", 8, 'right')
            print(f"   {ic} {Fore.WHITE}{lb}{Fore.RESET} : {Fore.MAGENTA}{pt}{Fore.RESET}")

def show_leaderboard(client: NillyClient):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}● TOP 10 LEADERBOARD GLOBAL NILLY:{Style.RESET_ALL}")
    lb = client.get_leaderboard(limit=10)
    if "top" in lb:
        w_rnk, w_addr, w_pts = 8, 48, 14
        b1, b2, b3 = '═'*w_rnk, '═'*w_addr, '═'*w_pts
        top = f"{Fore.CYAN}╔═{b1}═╦═{b2}═╦═{b3}═╗{Fore.RESET}"
        mid = f"{Fore.CYAN}╠═{b1}═╬═{b2}═╬═{b3}═╣{Fore.RESET}"
        bot = f"{Fore.CYAN}╚═{b1}═╩═{b2}═╩═{b3}═╝{Fore.RESET}"

        h1 = pad_cell(f"{Fore.WHITE}Rank{Fore.RESET}", w_rnk, 'center')
        h2 = pad_cell(f"{Fore.WHITE}Wallet Address{Fore.RESET}", w_addr, 'center')
        h3 = pad_cell(f"{Fore.WHITE}Total Poin{Fore.RESET}", w_pts, 'center')

        print(top)
        print(f"{Fore.CYAN}║{Fore.RESET} {h1} {Fore.CYAN}║{Fore.RESET} {h2} {Fore.CYAN}║{Fore.RESET} {h3} {Fore.CYAN}║{Fore.RESET}")
        print(mid)

        for r in lb["top"]:
            is_me = (r["address"].lower() == client.address.lower())
            addr_str = r["address"] + (" (YOU)" if is_me else "")
            color = Fore.GREEN if is_me else Fore.WHITE
            r1 = pad_cell(f"{color}#{r.get('rank', '-')}{Fore.RESET}", w_rnk, 'center')
            r2 = pad_cell(f"{color}{addr_str}{Fore.RESET}", w_addr, 'left')
            r3 = pad_cell(f"{Fore.MAGENTA}{r.get('total', 0)} pts{Fore.RESET}", w_pts, 'right')
            print(f"{Fore.CYAN}║{Fore.RESET} {r1} {Fore.CYAN}║{Fore.RESET} {r2} {Fore.CYAN}║{Fore.RESET} {r3} {Fore.CYAN}║{Fore.RESET}")
        print(bot)
        print(f"  Total Wallets Terdaftar: {Fore.YELLOW}{lb.get('wallets', 0)}{Fore.RESET}")
    else:
        log_error("Gagal mengambil data leaderboard dari API Nilly.")

def run_auto_farm(client: NillyClient, trade_amount: float = 0.00011, idx: int = 1, total: int = 1, pool_coins: list = None, referrer_addr: str = None) -> dict:
    start_time = time.time()
    initial_bal = client.get_balance()
    initial_prof = client.get_profile()
    initial_pts = initial_prof.get("points", 0)
    initial_rank = initial_prof.get("rank", "-")

    # Set referrer
    if referrer_addr:
        client.referrer = referrer_addr

    rank_display = f"#{initial_rank}" if initial_rank else "Unranked"
    lines = [
        f"{Fore.WHITE}[{idx}/{total}] WALLET: {Fore.YELLOW}{client.address}{Fore.RESET}",
        f"{Fore.WHITE}Saldo : {Fore.GREEN}{initial_bal:.6f} ETH{Fore.CYAN}  │  {Fore.WHITE}Poin: {Fore.MAGENTA}{initial_pts} pts{Fore.CYAN}  │  {Fore.WHITE}Rank: {Fore.CYAN}{rank_display}{Fore.RESET}"
    ]
    print()
    print_box(lines)

    if initial_bal < 0.00025:
        log_warn(f"Saldo {initial_bal:.6f} ETH terlalu kecil (minimal butuh ~0.0003 ETH). Melewati wallet ini.")
        return {"status": "skipped", "address": client.address, "reason": "low_balance"}

    items = {i["key"]: i for i in initial_prof.get("items", [])} if initial_prof else {}

    # 1. Quest Launch
    launch_done = items.get("launch", {}).get("done", 0)
    launch_more_done = items.get("launchMore", {}).get("done", 0)
    if launch_done == 0 or launch_more_done < 10:
        log_step(1, 4, "Meluncurkan Koin Baru (Factory.launchExpect)...")
        try:
            res = client.launch_coin(first_buy_eth=0.0)
            if res.get("success"):
                log_success(f"Token Baru Berhasil Diluncurkan: {res['name']} ({res['symbol']})")
                log_tx(res['tx_hash'])
                if pool_coins is not None and res.get("token"):
                    pool_coins.append({
                        "token": res.get("token"),
                        "market": res.get("market"),
                        "symbol": res.get("symbol"),
                        "name": res.get("name"),
                        "creator": client.address.lower()
                    })
            else:
                log_error("Gagal meluncurkan koin baru.")
        except Exception as e:
            log_error(f"Error saat launch: {e}")
        time.sleep(random.uniform(3, 5))
    else:
        log_info("Misi Launch sudah selesai maksimal. Lanjut ke trading.")

    # 2. Quest Buy (Prioritaskan Koin dari Wallet Lain di Pool untuk Crowd & Fees)
    log_step(2, 4, "Membeli Token di Bonding Curve (Cross-Trade / Pool)...")
    target_token, target_symbol = None, "TOKEN"

    # Cari koin yang dibuat oleh wallet lain di pool
    other_pool_coins = [c for c in (pool_coins or []) if c.get("creator") != client.address.lower()]
    if other_pool_coins:
        chosen = random.choice(other_pool_coins)
        target_token = chosen.get("token")
        target_symbol = chosen.get("symbol", "TOKEN")
        log_info(f"Target Cross-Trade (Koin Anggota Pool): {Fore.YELLOW}{target_symbol}{Fore.RESET} ({target_token})")
    else:
        coins = client.get_active_coins(limit=15)
        if coins:
            chosen = random.choice(coins)
            target_token = chosen.get("token")
            target_symbol = chosen.get("symbol", "TOKEN")
        else:
            target_token = "0x1bd7c29cc0b6fbc3f9614c3fe833e4258b1a284e"
            target_symbol = "GEJROT"
        log_info(f"Target Koin Pasar: {Fore.YELLOW}{target_symbol}{Fore.RESET} ({target_token})")

    log_info(f"Nominal Beli: {Fore.GREEN}{trade_amount:.6f} ETH{Fore.RESET} (Referral: {client.referrer[:10]}...)")

    buy_success = False
    try:
        buy_res = client.buy_coin(target_token, eth_amount=trade_amount)
        if buy_res.get("success"):
            buy_success = True
            log_success(f"Pembelian {target_symbol} Berhasil!")
            log_tx(buy_res['tx_hash'])
        else:
            log_error(f"Gagal membeli {target_symbol}.")
    except Exception as e:
        log_error(f"Error saat buy: {e}")

    # 3. Quest Sell (Recycle ETH)
    if buy_success:
        delay = random.uniform(5, 7)
        log_step(3, 4, f"Menunggu {delay:.1f}s lalu Menjual Token Kembali ke ETH (Recycle)...")
        time.sleep(delay)

        try:
            token_bal = client.get_token_balance(target_token)
            if token_bal > 0:
                sell_res = client.sell_coin(target_token, sell_pct=100.0)
                if sell_res.get("success"):
                    eth_back = sell_res.get("eth_returned", 0.0)
                    log_success(f"Penjualan Berhasil! ETH didaur ulang kembali ke dompet ({eth_back:.6f} ETH).")
                    log_tx(sell_res['tx_hash'])
                else:
                    log_error(f"Gagal menjual token: {sell_res.get('error')}")
            else:
                log_warn("Saldo token 0, tidak ada token yang dijual.")
        except Exception as e:
            log_error(f"Error saat sell: {e}")

    # 4. Quest Claim Creator Fees (Jika ada royalti dari koin buatan sendiri)
    log_step(4, 4, "Mengecek & Mengklaim Royalti Biaya Pembuat Koin (Claim Fees)...")
    my_created = initial_prof.get("created", [])
    claimed_any = False
    for mc in my_created:
        m_addr = mc.get("market")
        if m_addr:
            clm = client.claim_fees(m_addr)
            if clm.get("success"):
                log_success(f"Royalti berhasil diklaim dari market {m_addr}!")
                log_tx(clm['tx_hash'])
                claimed_any = True
                break
    if not claimed_any:
        log_info("Belum ada royalti baru yang siap diklaim di market ini.")

    final_bal = client.get_balance()
    diff = initial_bal - final_bal
    time.sleep(2)
    updated_prof = client.get_profile()

    new_pts = updated_prof.get("points", 0)
    new_rank = updated_prof.get("rank", "-")
    duration = time.time() - start_time

    log_success(f"Selesai dalam {duration:.1f}s │ Biaya Bersih: {diff:.6f} ETH │ Poin Baru: {new_pts} pts (#{new_rank})")
    return {
        "status": "success",
        "address": client.address,
        "initial_bal": initial_bal,
        "final_bal": final_bal,
        "diff": diff,
        "points": new_pts,
        "rank": new_rank
    }

def print_summary_table(results: list):
    w_no, w_addr, w_bal, w_pts, w_rank = 4, 44, 14, 10, 8
    b1, b2, b3, b4, b5 = '═'*w_no, '═'*w_addr, '═'*w_bal, '═'*w_pts, '═'*w_rank
    top = f"{Fore.CYAN}╔═{b1}═╦═{b2}═╦═{b3}═╦═{b4}═╦═{b5}═╗{Fore.RESET}"
    mid = f"{Fore.CYAN}╠═{b1}═╬═{b2}═╬═{b3}═╬═{b4}═╬═{b5}═╣{Fore.RESET}"
    bot = f"{Fore.CYAN}╚═{b1}═╩═{b2}═╩═{b3}═╩═{b4}═╩═{b5}═╝{Fore.RESET}"

    h_no = pad_cell(f"{Fore.WHITE}No{Fore.RESET}", w_no, 'center')
    h_addr = pad_cell(f"{Fore.WHITE}Wallet Address{Fore.RESET}", w_addr, 'center')
    h_bal = pad_cell(f"{Fore.WHITE}Sisa Saldo{Fore.RESET}", w_bal, 'center')
    h_pts = pad_cell(f"{Fore.WHITE}Poin{Fore.RESET}", w_pts, 'center')
    h_rank = pad_cell(f"{Fore.WHITE}Rank{Fore.RESET}", w_rank, 'center')

    print(f"\n{Fore.CYAN}{Style.BRIGHT}● TABEL RINGKASAN AKHIR HASIL FARMING:{Style.RESET_ALL}")
    print(top)
    print(f"{Fore.CYAN}║{Fore.RESET} {h_no} {Fore.CYAN}║{Fore.RESET} {h_addr} {Fore.CYAN}║{Fore.RESET} {h_bal} {Fore.CYAN}║{Fore.RESET} {h_pts} {Fore.CYAN}║{Fore.RESET} {h_rank} {Fore.CYAN}║{Fore.RESET}")
    print(mid)

    for idx, r in enumerate(results):
        no = pad_cell(f"{Fore.GREEN}{idx+1:02d}{Fore.RESET}", w_no, 'center')
        addr = pad_cell(f"{Fore.YELLOW}{r['address']}{Fore.RESET}", w_addr, 'center')
        if r.get("status") == "success":
            bal_str = f"{r['final_bal']:.6f} ETH"
            pts_str = f"{r['points']} pts"
            rank_str = f"#{r['rank']}"
            bal = pad_cell(f"{Fore.GREEN}{bal_str}{Fore.RESET}", w_bal, 'right')
            pts = pad_cell(f"{Fore.MAGENTA}{pts_str}{Fore.RESET}", w_pts, 'right')
            rank = pad_cell(f"{Fore.CYAN}{rank_str}{Fore.RESET}", w_rank, 'center')
            print(f"{Fore.CYAN}║{Fore.RESET} {no} {Fore.CYAN}║{Fore.RESET} {addr} {Fore.CYAN}║{Fore.RESET} {bal} {Fore.CYAN}║{Fore.RESET} {pts} {Fore.CYAN}║{Fore.RESET} {rank} {Fore.CYAN}║{Fore.RESET}")
        else:
            skip_msg = pad_cell(f"{Fore.RED}DILEWATI (Saldo < 0.00025 ETH){Fore.RESET}", w_bal + w_pts + w_rank + 6, 'center')
            print(f"{Fore.CYAN}║{Fore.RESET} {no} {Fore.CYAN}║{Fore.RESET} {addr} {Fore.CYAN}║{Fore.RESET} {skip_msg} {Fore.CYAN}║{Fore.RESET}")
    print(bot)

def main():
    parser = argparse.ArgumentParser(description="Nilly Testnet Auto Bot (Base Sepolia)")
    parser.add_argument("--status", action="store_true", help="Cek status dan poin semua wallet lalu keluar")
    parser.add_argument("--leaderboard", action="store_true", help="Tampilkan leaderboard lalu keluar")
    parser.add_argument("--faucet", action="store_true", help="Tampilkan info faucet Base Sepolia")
    parser.add_argument("--loop", action="store_true", help="Jalankan otomatis secara berulang tiap 24 jam")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah wallet yang dijalankan (contoh: --limit 3)")
    args = parser.parse_args()

    print(BANNER)

    if args.faucet:
        print(FAUCET_INFO)
        return

    wallets = load_wallets()
    if not wallets:
        log_error("Tidak ada private key yang ditemukan!")
        log_info("Masukkan private key Anda ke dalam file 'wallets.txt'.")
        print(FAUCET_INFO)
        return

    rpc_url, trade_amount = get_config_values()
    clients = [NillyClient(k, rpc_url=rpc_url) for k in wallets]
    if args.limit:
        clients = clients[:args.limit]
    log_info(f"Berhasil memuat {Fore.GREEN}{len(clients)}{Fore.RESET} wallet dari wallets.txt.")

    if args.status:
        for idx, c in enumerate(clients):
            show_wallet_status(c, idx=idx+1, total=len(clients))
        return

    if args.leaderboard:
        show_leaderboard(clients[0])
        return

    log_info("Mengumpulkan daftar koin buatan anggota pool untuk cross-trading...")
    pool_coins = collect_pool_coins(clients)
    log_info(f"Ditemukan {Fore.GREEN}{len(pool_coins)}{Fore.RESET} koin dari pool untuk saling ditradingkan.\n")

    def run_farm_cycle():
        results = []
        for idx, c in enumerate(clients):
            # Rotasi referral: Wallet 1 merefer Wallet 2, Wallet 2-10 merefer Wallet 1 (membantu Wallet 1 menembus leaderboard atas)
            if idx == 0:
                ref_addr = clients[1].address if len(clients) > 1 else clients[0].address
            else:
                ref_addr = clients[0].address

            r = run_auto_farm(
                c, 
                trade_amount=trade_amount, 
                idx=idx+1, 
                total=len(clients), 
                pool_coins=pool_coins,
                referrer_addr=ref_addr
            )
            results.append(r)
            if idx < len(clients) - 1:
                wait_sec = random.randint(8, 14)
                countdown_sleep(wait_sec, "Jeda acak antar wallet")
        print_summary_table(results)

    # DEFAULT: LANGSUNG GARAP SEMUA WALLET SECARA OTOMATIS
    if args.loop:
        log_success("Mode Auto-Loop Harian aktif! Bot akan mengulang setiap 24 jam. (Ctrl+C untuk berhenti)")
        while True:
            run_farm_cycle()
            log_info("Putaran hari ini selesai. Tidur 24 jam untuk siklus harian berikutnya...")
            time.sleep(86400)
    else:
        run_farm_cycle()
        log_success("Seluruh wallet selesai digarap dengan optimasi maksimal!")
        log_info("Tip: Gunakan 'python main.py --loop' jika ingin bot berjalan otomatis setiap 24 jam.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[!] Program dihentikan oleh pengguna. Sampai jumpa!{Fore.RESET}")
        sys.exit(0)
