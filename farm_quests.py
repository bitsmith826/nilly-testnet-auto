import os
import sys
import time
import random
import json
from colorama import init, Fore, Style

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from bot import load_wallets, get_config_values, log_info, log_success, log_warn, log_error, log_step, log_tx, pad_cell, print_box, countdown_sleep
from nilly_client import NillyClient

init(autoreset=True)

def run_quest_maximizer():
    wallets = load_wallets()
    rpc, trade_amt = get_config_values()
    clients = [NillyClient(k, rpc_url=rpc) for k in wallets]

    print(f"\n{Fore.CYAN}╔═════════════════════════════════════════════════════════════════════════╗")
    print(f"║   NILLY QUEST MAXIMIZER & MULTI-WALLET SYNERGY ACCELERATOR              ║")
    print(f"║   Target: Crowd (3/3) │ Launch (10/10) │ Different Coins (20/20)        ║")
    print(f"╚═════════════════════════════════════════════════════════════════════════╝{Fore.RESET}\n")

    log_info(f"Memuat {Fore.GREEN}{len(clients)}{Fore.RESET} wallet aktif...")

    # 1. Koleksi semua koin yang sudah dibuat oleh tiap wallet
    log_step(1, 4, "Inventarisasi Koin Pool dari Semua Wallet...")
    wallet_coins = {} # creator_addr -> list of coins
    for c in clients:
        prof = c.get_profile()
        my_coins = prof.get("created", [])
        wallet_coins[c.address.lower()] = my_coins
        log_info(f"Wallet {c.address[:10]}... memiliki {len(my_coins)} koin buatan sendiri.")

    # 2. Tuntaskan Launch 10/10 untuk Wallet 1 (dan wallet lain yang saldonya cukup)
    log_step(2, 4, "Menuntaskan Misi Launch 10/10...")
    for idx, c in enumerate(clients):
        prof = c.get_profile()
        items = {it["key"]: it for it in prof.get("items", [])}
        l_done = items.get("launchMore", {}).get("done", 0)
        needed = 10 - l_done
        if needed > 0 and c.get_balance() > 0.002:
            log_info(f"Wallet [{idx+1}/{len(clients)}] {c.address[:10]}... butuh {needed}x peluncuran koin lagi.")
            for n in range(needed):
                log_info(f"  ↳ Meluncurkan koin ke-{l_done + n + 1}...")
                res = c.launch_coin()
                if res.get("success"):
                    log_success(f"  Token Berhasil Dibuat: {res['name']} ({res['symbol']})")
                    log_tx(res['tx_hash'])
                    wallet_coins.setdefault(c.address.lower(), []).append({
                        "token": res["token"],
                        "market": res["market"],
                        "name": res["name"],
                        "symbol": res["symbol"]
                    })
                    time.sleep(3)
                else:
                    log_warn("  Gagal meluncurkan koin, melanjutkan.")
                    break
        else:
            log_info(f"Wallet [{idx+1}/{len(clients)}] {c.address[:10]}... Launch sudah maksimal ({l_done}/10).")

    # 3. Optimasi Misi Crowd: 10 Traders untuk Koin-Koin Wallet 1
    log_step(3, 4, "Menggenjot Misi Crowd (10 Traders) untuk Koin Wallet 1...")
    w1_created = wallet_coins.get(clients[0].address.lower(), [])
    w1_prof = clients[0].get_profile()
    w1_items = {it["key"]: it for it in w1_prof.get("items", [])}
    w1_crowd = w1_items.get("crowd", {}).get("done", 0)

    log_info(f"Progress Crowd Wallet 1 saat ini: {w1_crowd}/3.")
    if w1_crowd < 3 and len(w1_created) >= 2:
        # Kita targetkan koin index 1 dan index 2 (karena index 0 sudah 10 traders)
        target_coins = w1_created[1:3]
        for coin_idx, coin in enumerate(target_coins):
            t_addr = coin.get("token")
            t_sym = coin.get("symbol", "TOKEN")
            log_info(f"\nMemulai Crowd Booster untuk Koin #{coin_idx+2}: {Fore.YELLOW}{t_sym}{Fore.RESET} ({t_addr})...")
            
            # Minta wallet 2 s/d 10 (dan wallet 1 jika perlu) untuk trading koin ini
            for trader_idx in range(1, len(clients)):
                trader = clients[trader_idx]
                trader.referrer = clients[0].address # Sekaligus booster referral Wallet 1!
                log_info(f"  [Trader {trader_idx+1}/10] {trader.address[:10]}... Membeli {t_sym}...")
                try:
                    b_res = trader.buy_coin(t_addr, eth_amount=trade_amt)
                    if b_res.get("success"):
                        log_success(f"  ✔ Beli sukses! Recycle sell...")
                        time.sleep(3)
                        s_res = trader.sell_coin(t_addr, sell_pct=100.0)
                        if s_res.get("success"):
                            log_success(f"  ✔ Daur ulang ETH sukses ({s_res.get('eth_returned', 0):.6f} ETH kembali).")
                    time.sleep(2)
                except Exception as e:
                    log_warn(f"  Gagal transaksi: {e}")

    # 4. Optimasi Misi Trade Different Coins (Mencapai 20/20)
    log_step(4, 4, "Memaksimalkan Misi Trade Different Coins (Menuju 20/20)...")
    # Kumpulkan seluruh token unik dari pool
    all_pool_tokens = []
    for c_list in wallet_coins.values():
        for item in c_list:
            if item.get("token") and item["token"] not in all_pool_tokens:
                all_pool_tokens.append(item["token"])

    # Ambil koin pasar aktif tambahan jika pool kurang
    if len(all_pool_tokens) < 20:
        market_coins = clients[0].get_active_coins(limit=25)
        for mc in market_coins:
            tok = mc.get("token")
            if tok and tok not in all_pool_tokens:
                all_pool_tokens.append(tok)

    log_info(f"Tersedia {len(all_pool_tokens)} token unik untuk diverifikasi.")

    # Jalankan pembelian koin unik untuk Wallet 1
    w1 = clients[0]
    w1_prof = w1.get_profile()
    w1_c_done = {it["key"]: it for it in w1_prof.get("items", [])}.get("coins", {}).get("done", 0)
    coins_needed = 20 - w1_c_done
    log_info(f"Wallet 1 sudah trade {w1_c_done}/20 koin. Membutuhkan {coins_needed} koin baru.")

    traded_count = 0
    for tok in all_pool_tokens:
        if traded_count >= coins_needed:
            break
        try:
            log_info(f"Wallet 1 trading koin unik ({traded_count+1}/{coins_needed}): {tok[:12]}...")
            b = w1.buy_coin(tok, eth_amount=trade_amt)
            if b.get("success"):
                time.sleep(3)
                w1.sell_coin(tok, sell_pct=100.0)
                traded_count += 1
                time.sleep(2)
        except Exception as e:
            pass

    # Klaim royalti fee untuk semua koin
    log_info("Mengecek dan mengklaim semua royalti fee yang tersedia...")
    for idx, c in enumerate(clients):
        my_c = wallet_coins.get(c.address.lower(), [])
        for coin in my_c:
            m_addr = coin.get("market")
            if m_addr:
                c.claim_fees(m_addr)

    # Cetak Hasil Akhir Poin
    print(f"\n{Fore.GREEN}╔═════════════════════════════════════════════════════════════════════════╗")
    print(f"║   HASIL AKHIR SETELAH PENGGARAPAN MAKSIMAL                              ║")
    print(f"╚═════════════════════════════════════════════════════════════════════════╝{Fore.RESET}\n")

    for idx, c in enumerate(clients):
        p = c.get_profile()
        it = {item["key"]: item for item in p.get("items", [])}
        print(f"Wallet {idx+1:<2} [{c.address[:10]}...]: Saldo {c.get_balance():.6f} ETH │ Poin: {Fore.MAGENTA}{p.get('points', 0)} pts{Fore.RESET} │ Rank: {Fore.CYAN}#{p.get('rank', '-')}{Fore.RESET}")

if __name__ == "__main__":
    run_quest_maximizer()
