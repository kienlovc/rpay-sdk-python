from __future__ import annotations
from typing import Any, Dict, List, Optional

RPAY_DEFAULT_BASE_URL = "https://api.rpay.vn"
RPAY_DEFAULT_TIMEOUT_SEC = 60.0

RPAY_BANKS: List[Dict[str, Any]] = [
    {
        "key": "vietcombank",
        "code": "VCB",
        "shortName": "Vietcombank",
        "fullName": "Ngân hàng TMCP Ngoại thương Việt Nam",
        "bin": "970436",
        "apiSlug": "vcb",
        "primarySlug": "vcb",
        "aliases": ["vcb", "vietcombank"],
        "logo": "/ibankings/970436.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "acb",
        "code": "ACB",
        "shortName": "ACB",
        "fullName": "Ngân hàng TMCP Á Châu",
        "bin": "970416",
        "apiSlug": "acb",
        "primarySlug": "acb",
        "aliases": ["acb"],
        "logo": "/ibankings/970416.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "mbbank",
        "code": "MB",
        "shortName": "MBBank",
        "fullName": "Ngân hàng TMCP Quân đội",
        "bin": "970422",
        "apiSlug": "mb",
        "primarySlug": "mb",
        "aliases": ["mb", "mbbank"],
        "logo": "/ibankings/970422.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "techcombank",
        "code": "TCB",
        "shortName": "Techcombank",
        "fullName": "Ngân hàng TMCP Kỹ thương Việt Nam",
        "bin": "970407",
        "apiSlug": "tcb",
        "primarySlug": "tcb",
        "aliases": ["tcb", "techcombank"],
        "logo": "/ibankings/970407.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "bidv",
        "code": "BIDV",
        "shortName": "BIDV",
        "fullName": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam",
        "bin": "970418",
        "apiSlug": "bidv",
        "primarySlug": "bidv",
        "aliases": ["bidv"],
        "logo": "/ibankings/970418.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "vietinbank",
        "code": "ICB",
        "shortName": "VietinBank",
        "fullName": "Ngân hàng TMCP Công thương Việt Nam",
        "bin": "970415",
        "apiSlug": "icb",
        "primarySlug": "icb",
        "aliases": ["icb", "vietinbank", "ctg", "vtb", "viettinbank"],
        "logo": "/ibankings/970415.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "vpbank",
        "code": "VPB",
        "shortName": "VPBank",
        "fullName": "Ngân hàng TMCP Việt Nam Thịnh Vượng",
        "bin": "970432",
        "apiSlug": "vpb",
        "primarySlug": "vpb",
        "aliases": ["vpb", "vpbank"],
        "logo": "/ibankings/970432.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "tpbank",
        "code": "TPB",
        "shortName": "TPBank",
        "fullName": "Ngân hàng TMCP Tiên Phong",
        "bin": "970423",
        "apiSlug": "tpb",
        "primarySlug": "tpb",
        "aliases": ["tpb", "tpbank"],
        "logo": "/ibankings/970423.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "agribank",
        "code": "VBA",
        "shortName": "Agribank",
        "fullName": "Ngân hàng Nông nghiệp và PTNT Việt Nam",
        "bin": "970405",
        "apiSlug": "vba",
        "primarySlug": "vba",
        "aliases": ["vba", "agribank"],
        "logo": "/ibankings/970405.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "msb",
        "code": "MSB",
        "shortName": "MSB",
        "fullName": "Ngân hàng TMCP Hàng Hải",
        "bin": "970426",
        "apiSlug": "msb",
        "primarySlug": "msb",
        "aliases": ["msb", "maritimebank"],
        "logo": "/ibankings/970426.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "ocb",
        "code": "OCB",
        "shortName": "OCB",
        "fullName": "Ngân hàng TMCP Phương Đông",
        "bin": "970448",
        "apiSlug": "ocb",
        "primarySlug": "ocb",
        "aliases": ["ocb", "oceanbank"],
        "logo": "/ibankings/970448.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "seabank",
        "code": "SEAB",
        "shortName": "SeABank",
        "fullName": "Ngân hàng TMCP Đông Nam Á",
        "bin": "970440",
        "apiSlug": "seab",
        "primarySlug": "seabank",
        "aliases": ["seabank", "ssb", "seab", "sebank"],
        "logo": "/ibankings/970440.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "eximbank",
        "code": "EIB",
        "shortName": "Eximbank",
        "fullName": "Ngân hàng TMCP Xuất Nhập khẩu Việt Nam",
        "bin": "970431",
        "apiSlug": "eib",
        "primarySlug": "eib",
        "aliases": ["eib", "eximbank", "exim"],
        "logo": "/ibankings/970431.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "bvbank",
        "code": "BVB",
        "shortName": "BVBank",
        "fullName": "Ngân hàng TMCP Bản Việt",
        "bin": "970454",
        "apiSlug": "bvb",
        "primarySlug": "bvb",
        "aliases": ["bvb", "bvbank", "banviet", "vietcapitalbank"],
        "logo": "/ibankings/970454.png",
        "v3UsesPhonePin": False,
    },
    {
        "key": "viettelpay",
        "code": "VTP",
        "shortName": "Viettel Money",
        "fullName": "Tổng công ty Dịch vụ số Viettel",
        "bin": "971005",
        "apiSlug": "vtp",
        "primarySlug": "vtm",
        "aliases": ["vtm", "vtp", "viettelmoney", "viettelpay", "viettel_money", "viettel-money"],
        "logo": "/ibankings/971005.png",
        "v3UsesPhonePin": True,
    },
]

RPAY_USDT_NETWORKS: List[Dict[str, Any]] = [
    {"network": "TRC20", "name": "TRON (TRC-20)", "chainKey": "tron", "tokenStandard": "TRC-20", "decimals": 6},
    {"network": "BEP20", "name": "BNB Smart Chain (BEP-20)", "chainKey": "bsc", "tokenStandard": "BEP-20", "decimals": 18},
    {"network": "ERC20", "name": "Ethereum (ERC-20)", "chainKey": "ethereum", "tokenStandard": "ERC-20", "decimals": 6},
    {"network": "POLYGON", "name": "Polygon POS", "chainKey": "polygon", "tokenStandard": "ERC-20 (Polygon)", "decimals": 6},
    {"network": "ARBITRUM", "name": "Arbitrum One", "chainKey": "arbitrum", "tokenStandard": "ERC-20 (Arbitrum)", "decimals": 6},
    {"network": "OPTIMISM", "name": "OP Mainnet (Optimism)", "chainKey": "optimism", "tokenStandard": "ERC-20 (Optimism)", "decimals": 6},
    {"network": "SOLANA", "name": "Solana (SPL)", "chainKey": "solana", "tokenStandard": "SPL", "decimals": 6},
    {"network": "TON", "name": "The Open Network (TON Jetton)", "chainKey": "ton", "tokenStandard": "Jetton", "decimals": 6},
    {"network": "BASE", "name": "Base Mainnet", "chainKey": "base", "tokenStandard": "ERC-20 (Base)", "decimals": 6},
    {"network": "AVALANCHE", "name": "Avalanche C-Chain", "chainKey": "avalanche", "tokenStandard": "ARC-20", "decimals": 6},
    {"network": "APTOS", "name": "Aptos Mainnet", "chainKey": "aptos", "tokenStandard": "Aptos Fungible Asset", "decimals": 6},
    {"network": "SUI", "name": "Sui Network", "chainKey": "sui", "tokenStandard": "Sui Coin", "decimals": 6},
    {"network": "OPBNB", "name": "opBNB Mainnet", "chainKey": "opbnb", "tokenStandard": "BEP-20 (opBNB)", "decimals": 18},
    {"network": "CELO", "name": "Celo Mainnet", "chainKey": "celo", "tokenStandard": "ERC-20 (Celo)", "decimals": 6},
    {"network": "SCROLL", "name": "Scroll Mainnet", "chainKey": "scroll", "tokenStandard": "ERC-20 (Scroll)", "decimals": 6},
    {"network": "KAVA", "name": "Kava EVM", "chainKey": "kava", "tokenStandard": "ERC-20 (Kava)", "decimals": 6},
    {"network": "POLKADOT", "name": "Polkadot Asset Hub (Statemint)", "chainKey": "polkadot", "tokenStandard": "AssetHub #1984", "decimals": 6},
    {"network": "OSMOSIS", "name": "Osmosis (Cosmos IBC)", "chainKey": "osmosis", "tokenStandard": "IBC Denom", "decimals": 6},
]


def resolve_bank_spec(identifier: Optional[str]) -> Optional[Dict[str, Any]]:
    norm = str(identifier or "").strip().lower()
    if not norm:
        return None
    for bank in RPAY_BANKS:
        if (
            bank["key"] == norm
            or bank["code"].lower() == norm
            or bank["bin"] == norm
            or bank["shortName"].lower() == norm
            or bank["apiSlug"] == norm
            or bank["primarySlug"] == norm
            or norm in bank["aliases"]
        ):
            return dict(bank)
    return None


def resolve_usdt_network_spec(raw_network: Optional[str]) -> Optional[Dict[str, Any]]:
    norm = str(raw_network or "").strip().upper()
    if not norm:
        return None
    alias_map = {
        "TRX": "TRC20",
        "TRON": "TRC20",
        "TRC-20": "TRC20",
        "BSC": "BEP20",
        "BNB": "BEP20",
        "BEP-20": "BEP20",
        "ETH": "ERC20",
        "ETHEREUM": "ERC20",
        "ERC-20": "ERC20",
        "MATIC": "POLYGON",
        "ARB": "ARBITRUM",
        "OP": "OPTIMISM",
        "SOL": "SOLANA",
        "AVAX": "AVALANCHE",
        "DOT": "POLKADOT",
        "OSMO": "OSMOSIS",
    }
    target = alias_map.get(norm, norm)
    for item in RPAY_USDT_NETWORKS:
        if item["network"] == target or item["chainKey"].upper() == target:
            return dict(item)
    return None
