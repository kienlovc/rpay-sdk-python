from __future__ import annotations
from .client import RPayClient, RPayError, create_client, rpay
from .constants import (
    RPAY_BANKS,
    RPAY_DEFAULT_BASE_URL,
    RPAY_DEFAULT_TIMEOUT_SEC,
    RPAY_USDT_NETWORKS,
    resolve_bank_spec,
    resolve_usdt_network_spec,
)
from .unified import (
    detect_payment_channel,
    match_unified_transactions,
    normalize_unified_invoice,
    normalize_unified_transaction,
)
from .webhooks import (
    build_canonical_payload_string,
    hmac_sha256_hex,
    safe_compare_signature,
    sign_canonical_payload,
    sign_raw_body,
    verify_webhook,
)

# Module-level shorthands so `import rpay_sdk as rpay; rpay.pay(...)` works seamlessly
init = rpay.init
configure = rpay.configure
for_domain = rpay.for_domain
pay = rpay.pay
create_invoice = rpay.create_invoice
check = rpay.check
check_invoice = rpay.check_invoice
status = rpay.status
get_invoice = rpay.get_invoice
lsgd = rpay.lsgd
get_history = rpay.get_history
qr = rpay.qr
match_payment = rpay.match_payment
route = rpay.route

__all__ = [
    "rpay",
    "RPayClient",
    "RPayError",
    "create_client",
    "init",
    "configure",
    "for_domain",
    "pay",
    "create_invoice",
    "check",
    "check_invoice",
    "status",
    "get_invoice",
    "lsgd",
    "get_history",
    "qr",
    "match_payment",
    "route",
    "verify_webhook",
    "sign_canonical_payload",
    "sign_raw_body",
    "hmac_sha256_hex",
    "safe_compare_signature",
    "build_canonical_payload_string",
    "RPAY_BANKS",
    "RPAY_USDT_NETWORKS",
    "RPAY_DEFAULT_BASE_URL",
    "RPAY_DEFAULT_TIMEOUT_SEC",
    "resolve_bank_spec",
    "resolve_usdt_network_spec",
    "detect_payment_channel",
    "normalize_unified_invoice",
    "normalize_unified_transaction",
    "match_unified_transactions",
]
