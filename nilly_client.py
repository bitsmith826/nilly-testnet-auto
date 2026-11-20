import json
import os
import random
import time
import warnings
import requests
from web3 import Web3
from web3.exceptions import Web3RPCError, ContractLogicError, TransactionNotFound
from eth_account import Account

# Suppress internal eth_utils event signature warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, 'config.json'), 'r') as f:
    CONFIG = json.load(f)

with open(os.path.join(BASE_DIR, 'abis.json'), 'r') as f:
    ABIS = json.load(f)

RPC_LIST = CONFIG.get("rpcUpstreams", [
    "https://sepolia.base.org",
    "https://base-sepolia-rpc.publicnode.com"
])
CHAIN_ID = CONFIG.get("chainId", 84532)
FACTORY_ADDR = Web3.to_checksum_address(CONFIG.get("factory", "0x0D8bFF4Dc1a5b1CB9Dc28F3a54302ABa6c3b5488"))
ROUTER_ADDR = Web3.to_checksum_address(CONFIG.get("router", "0xc7ed5f570f6Ca50078B0B359943Cd57338De57B5"))
EXPLORER = CONFIG.get("explorer", "https://sepolia.basescan.org")
ZERO_ADDR = "0x0000000000000000000000000000000000000000"

MEME_PREFIXES = ["Moon", "Zero", "Super", "Alpha", "Hyper", "Pepe", "Nilly", "Cyber", "Rocket", "Base", "Giga", "Omni", "Turbo", "Chad"]
MEME_SUFFIXES = ["Inu", "Cat", "Coin", "AI", "Token", "Protocol", "Bot", "Star", "Gem", "Pump", "DAO", "Fun", "Doge", "Kek"]

class NillyClient:
    def __init__(self, private_key: str, rpc_url: str = None, referrer: str = None):
        self.rpc_urls = [rpc_url] if rpc_url else RPC_LIST
        self.current_rpc_idx = 0
        self.w3 = self._init_web3()
        
        # Setup account
        clean_key = private_key.strip()
        if not clean_key.startswith("0x"):
            clean_key = "0x" + clean_key
        self.account = Account.from_key(clean_key)
        self.address = self.account.address
        
        # Referrer
        if referrer and Web3.is_address(referrer):
            self.referrer = Web3.to_checksum_address(referrer)
        else:
            self.referrer = ZERO_ADDR
            
        # Contracts
        self.factory = self.w3.eth.contract(address=FACTORY_ADDR, abi=ABIS["NillyFactory"])
        self.router = self.w3.eth.contract(address=ROUTER_ADDR, abi=ABIS["NillyRouter"])

    def _init_web3(self) -> Web3:
        url = self.rpc_urls[self.current_rpc_idx % len(self.rpc_urls)]
        return Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 20}))

    def _switch_rpc(self):
        self.current_rpc_idx = (self.current_rpc_idx + 1) % len(self.rpc_urls)
        self.w3 = self._init_web3()
        self.factory = self.w3.eth.contract(address=FACTORY_ADDR, abi=ABIS["NillyFactory"])
        self.router = self.w3.eth.contract(address=ROUTER_ADDR, abi=ABIS["NillyRouter"])

    def get_balance(self) -> float:
        for _ in range(len(self.rpc_urls)):
            try:
                wei_bal = self.w3.eth.get_balance(self.address)
                return float(Web3.from_wei(wei_bal, 'ether'))
            except Exception:
                self._switch_rpc()
        return 0.0
        
    def get_token_balance(self, token_address: str) -> int:
        for _ in range(len(self.rpc_urls)):
            try:
                token_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(token_address), 
                    abi=ABIS["NillyToken"]
                )
                return token_contract.functions.balanceOf(self.address).call()
            except Exception:
                self._switch_rpc()
        return 0

    def get_profile(self) -> dict:
        url = f"https://testnet.nilly.fun/api/profile?a={self.address}"
        for _ in range(2):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                time.sleep(1)
        return {}

    def get_points(self) -> dict:
        url = f"https://testnet.nilly.fun/api/points?a={self.address}"
        for _ in range(2):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                time.sleep(1)
        return {}

    def get_leaderboard(self, limit: int = 10) -> dict:
        url = "https://testnet.nilly.fun/api/leaderboard"
        for _ in range(2):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if "top" in data:
                        data["top"] = data["top"][:limit]
                    return data
            except Exception:
                time.sleep(1)
        return {}

    def get_active_coins(self, limit: int = 20) -> list:
        url = f"https://testnet.nilly.fun/v1/coins?sort=active&limit={limit}"
        for _ in range(2):
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    return r.json().get("coins", [])
            except Exception:
                time.sleep(1)
        return []

    def _send_transaction(self, tx_dict: dict, retries: int = 3) -> dict:
        last_error = None
        for attempt in range(retries):
            try:
                if "nonce" not in tx_dict:
                    tx_dict["nonce"] = self.w3.eth.get_transaction_count(self.address, "pending")
                if "chainId" not in tx_dict:
                    tx_dict["chainId"] = CHAIN_ID

                # Dynamic gas pricing
                try:
                    latest_block = self.w3.eth.get_block('latest')
                    base_fee = latest_block.get('baseFeePerGas', 10000000)
                    max_priority = self.w3.eth.max_priority_fee or 1000000
                    tx_dict["maxFeePerGas"] = int(base_fee * 1.5 + max_priority)
                    tx_dict["maxPriorityFeePerGas"] = max_priority
                except Exception:
                    tx_dict["gasPrice"] = int(self.w3.eth.gas_price * 1.2)

                # Gas limit estimation
                if "gas" not in tx_dict:
                    try:
                        estimated = self.w3.eth.estimate_gas(tx_dict)
                        tx_dict["gas"] = int(estimated * 1.25)
                    except Exception:
                        tx_dict["gas"] = 350000

                signed_tx = self.w3.eth.account.sign_transaction(tx_dict, self.account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                return receipt

            except (Web3RPCError, Exception) as e:
                err_str = str(e).lower()
                last_error = e
                if "insufficient funds" in err_str:
                    raise ValueError("Saldo Base Sepolia ETH tidak cukup untuk gas/transaksi.")
                elif "nonce" in err_str or "already known" in err_str:
                    tx_dict["nonce"] = self.w3.eth.get_transaction_count(self.address, "pending")
                elif "timeout" in err_str or "connection" in err_str:
                    self._switch_rpc()
                time.sleep(2)

        raise RuntimeError(f"Gagal memproses transaksi setelah {retries} percobaan: {last_error}")

    def launch_coin(self, name: str = None, symbol: str = None, desc: str = None, first_buy_eth: float = 0.0) -> dict:
        if not name or not symbol:
            pfx = random.choice(MEME_PREFIXES)
            sfx = random.choice(MEME_SUFFIXES)
            num = random.randint(100, 999)
            name = f"{pfx} {sfx} {num}"
            symbol = f"{pfx[:2].upper()}{sfx[:2].upper()}{num % 100}"
            
        desc = desc or f"Community token {name} on Nilly Testnet"
        meta = json.dumps({"desc": desc})

        try:
            fee = self.factory.functions.launchFee().call()
            dep = self.factory.functions.launchDeposit().call()
        except Exception:
            fee, dep = 0, 100000000000000 # fallback 0.0001 ETH

        first_buy_wei = Web3.to_wei(first_buy_eth, 'ether')
        total_value = fee + dep + first_buy_wei

        p = (
            name,
            symbol,
            meta,
            0,            # 0% tax
            ZERO_ADDR,    # feeRecipient
            [],           # splitTo
            [],           # splitBps
            [],           # exempt
            first_buy_wei,# firstBuy
            0             # minTokensOut
        )

        fn = self.factory.functions.launchExpect(p, ZERO_ADDR)
        tx = fn.build_transaction({
            'from': self.address,
            'value': total_value
        })

        receipt = self._send_transaction(tx)
        
        market_addr, token_addr = None, None
        try:
            events = self.factory.events.Launched().process_receipt(receipt)
            if events:
                market_addr = events[0]['args']['market']
                token_addr = events[0]['args']['token']
        except Exception:
            pass

        return {
            "success": receipt.status == 1,
            "tx_hash": receipt.transactionHash.hex(),
            "name": name,
            "symbol": symbol,
            "token": token_addr,
            "market": market_addr,
            "gas_used": receipt.gasUsed
        }

    def buy_coin(self, token_address: str, eth_amount: float = 0.00011, slippage_pct: float = 5.0) -> dict:
        token = Web3.to_checksum_address(token_address)
        amount_in = Web3.to_wei(eth_amount, 'ether')

        min_out = 0
        for _ in range(3):
            try:
                expected_out = self.router.functions.getAmountOutBuy(token, amount_in, self.address).call()
                min_out = int(expected_out * (1 - (slippage_pct / 100.0)))
                break
            except Exception:
                self._switch_rpc()
                time.sleep(1)

        if min_out == 0:
            return {"success": False, "error": "Gagal mendapatkan kuotasi buy aman (anti-slippage protection)"}

        deadline = int(time.time()) + 600

        fn = self.router.functions.swapExactNativeForTokens(
            token,
            min_out,
            self.address,
            self.referrer,
            deadline
        )

        tx = fn.build_transaction({
            'from': self.address,
            'value': amount_in
        })

        receipt = self._send_transaction(tx)
        return {
            "success": receipt.status == 1,
            "tx_hash": receipt.transactionHash.hex(),
            "token": token,
            "eth_spent": eth_amount,
            "gas_used": receipt.gasUsed
        }

    def sell_coin(self, token_address: str, token_amount: int = None, sell_pct: float = 100.0, slippage_pct: float = 5.0) -> dict:
        token = Web3.to_checksum_address(token_address)
        token_contract = self.w3.eth.contract(address=token, abi=ABIS["NillyToken"])
        
        balance = token_contract.functions.balanceOf(self.address).call()
        if balance == 0:
            return {"success": False, "error": "Saldo token 0, tidak ada token untuk dijual"}

        # Precise integer math to avoid float precision overflow
        if token_amount is None:
            if sell_pct >= 100.0:
                tokens_in = balance
            else:
                tokens_in = (balance * int(sell_pct * 100)) // 10000
        else:
            tokens_in = min(token_amount, balance)

        if tokens_in == 0:
            return {"success": False, "error": "Jumlah token untuk dijual adalah 0"}

        # Check allowance - Approve safe bounded amount instead of infinite 2**256 - 1
        allowance = token_contract.functions.allowance(self.address, ROUTER_ADDR).call()
        if allowance < tokens_in:
            approve_tx = token_contract.functions.approve(
                ROUTER_ADDR,
                tokens_in * 100
            ).build_transaction({'from': self.address})
            self._send_transaction(approve_tx)
            time.sleep(2)

        # Expected ETH return with retry and slippage protection
        min_out = 0
        expected_eth = 0
        for _ in range(3):
            try:
                expected_eth = self.router.functions.getAmountOutSell(token, tokens_in).call()
                min_out = int(expected_eth * (1 - (slippage_pct / 100.0)))
                break
            except Exception:
                self._switch_rpc()
                time.sleep(1)

        if min_out == 0:
            return {"success": False, "error": "Gagal mendapatkan kuotasi sell aman (anti-slippage protection)"}

        deadline = int(time.time()) + 600

        fn = self.router.functions.swapExactTokensForNative(
            token,
            tokens_in,
            min_out,
            self.address,
            self.referrer,
            deadline
        )

        tx = fn.build_transaction({'from': self.address})
        receipt = self._send_transaction(tx)

        return {
            "success": receipt.status == 1,
            "tx_hash": receipt.transactionHash.hex(),
            "token": token,
            "tokens_sold": tokens_in,
            "eth_returned": float(Web3.from_wei(expected_eth, 'ether')) if 'expected_eth' in locals() else 0.0,
            "gas_used": receipt.gasUsed
        }

    def claim_fees(self, market_address: str) -> dict:
        try:
            market = self.w3.eth.contract(address=Web3.to_checksum_address(market_address), abi=ABIS["NillyMarket"])
            owed = market.functions.owed(self.address).call()
            if owed > 0:
                tx = market.functions.claim().build_transaction({'from': self.address})
                receipt = self._send_transaction(tx)
                return {
                    "success": receipt.status == 1, 
                    "claimed_wei": owed, 
                    "tx_hash": receipt.transactionHash.hex()
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "No fees owed"}
