# Nilly Testnet Automation Bot (LayerZero Eco)

Sistem otomasi untuk menggarap **Nilly Testnet** (`testnet.nilly.fun`) di jaringan **Base Sepolia**.

Bot ini berinteraksi langsung dengan Smart Contract resmi Nilly (**NillyFactory** & **NillyRouter**) dan REST API Nilly dengan sistem **Recycle ETH** (modal beli langsung dijual kembali 100% sehingga saldo testnet Anda sangat hemat).

---

## ⚡ Cara Menjalankan

Cukup buka terminal dan jalankan:

```bash
python main.py
```

Bot akan **langsung otomatis**:
1. Membaca daftar wallet dari `wallets.txt`.
2. Mengecek saldo dan status misi.
3. Meluncurkan koin baru (*Launch*).
4. Membeli koin aktif di bonding curve (*Buy*).
5. Menjual kembali token ke ETH (*Sell/Recycle*).
6. Menampilkan perolehan poin dan tabel ringkasan akhir.

---

## 🛠️ Perintah Tambahan (Opsional)

* **Mode Auto-Loop 24 Jam** (Bot jalan terus & otomatis mengulang tiap 24 jam):
  ```bash
  python main.py --loop
  ```

* **Cek Saldo & Poin Seluruh Wallet**:
  ```bash
  python main.py --status
  ```

* **Cek Top 10 Leaderboard**:
  ```bash
  python main.py --leaderboard
  ```

* **Info Faucet Testnet ETH**:
  ```bash
  python main.py --faucet
  ```

---

## 📁 Konfigurasi Wallet

Daftar Private Key tersimpan di [wallets.txt](wallets.txt) (satu private key per baris):
```text
0xprivatekey1...
0xprivatekey2...
```

---

## 📋 Aturan Poin Nilly

| Misi | Poin | Maksimal |
|---|---|---|
| **Launch your first coin** | 100 pts | 1 kali |
| **Make your first buy** | 50 pts | 1 kali |
| **Make your first sell** | 50 pts | 1 kali |
| **Trade on different days** | 20 pts | 30 hari (Total 600 pts) |
| **Trade different coins** | 10 pts | 20 koin (Total 200 pts) |
| **Launch more coins** | 10 pts | 10 kali (Total 100 pts) |
