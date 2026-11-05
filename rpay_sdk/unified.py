from __future__ import annotations
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Union
from .constants import resolve_usdt_network_spec


def normalize_transfer_text(value: str, ignore_separators: bool = True) -> str:
    upper = str(value or "").strip().upper()
    if not ignore_separators:
        return upper
    return re.sub(r"[^A-Z0-9]", "", upper)


def detect_payment_channel(
    input_or_code: Union[Mapping[str, Any], str, None],
    fallback: str = "bank",
) -> str:
    if isinstance(input_or_code, str):
        code = input_or_code.strip().upper()
        if code.startswith(("USINV", "USTX", "USDT", "USDC")):
            return "usdt"
        if code.startswith(("RPINV", "RPAY")):
            return "bank"
        return fallback

    if not isinstance(input_or_code, Mapping):
        return fallback

    explicit = str(
        input_or_code.get("channel")
        or input_or_code.get("type")
        or input_or_code.get("paymentType")
        or ""
    ).strip().lower()
    if explicit in ("usdt", "usdc", "crypto"):
        return "usdt"
    if explicit in ("bank", "vietqr", "vnd"):
        return "bank"

    currency = str(input_or_code.get("currency") or input_or_code.get("token") or "").strip().upper()
    if currency in ("USDT", "USDC"):
        return "usdt"
    if currency == "VND":
        return "bank"

    if (
        input_or_code.get("amountUsdt") is not None
        or input_or_code.get("amount_usdt") is not None
        or (input_or_code.get("network") and resolve_usdt_network_spec(str(input_or_code.get("network"))))
        or input_or_code.get("walletAddress")
        or input_or_code.get("trans_id")
    ):
        return "usdt"

    return fallback


def normalize_invoice_status(raw_status: Optional[str]) -> str:
    s = str(raw_status or "pending").strip().lower()
    if s in ("paid", "reconciled", "completed", "success", "underpaid_settled", "settled"):
        return "paid"
    if s in ("expired", "timeout"):
        return "expired"
    if s in ("cancelled", "canceled", "failed"):
        return "cancelled"
    return "pending"


def normalize_unified_invoice(raw_response: Any, hint_channel: Optional[str] = None) -> Dict[str, Any]:
    data = (
        raw_response["data"]
        if isinstance(raw_response, Mapping) and isinstance(raw_response.get("data"), Mapping)
        else (dict(raw_response) if isinstance(raw_response, Mapping) else {})
    )
    channel = hint_channel or (
        "bank"
        if data.get("currency") == "VND" or data.get("amountVnd") is not None or data.get("beneficiary")
        else "usdt"
    )

    if channel == "bank":
        status = normalize_invoice_status(data.get("status"))
        beneficiary = data.get("beneficiary") or {}
        qr = data.get("qr") or {}
        amount = float(data.get("amountVnd") or data.get("amount") or 0)
        paid = float(data.get("paidAmountVnd") or (amount if status == "paid" else 0))
        return {
            "channel": "bank",
            "invoiceId": str(data.get("invoiceId") or data.get("id") or data.get("invoiceCode") or ""),
            "invoiceCode": str(data.get("invoiceCode") or ""),
            "orderId": str(data.get("orderId") or ""),
            "status": status,
            "rawStatus": str(data.get("status") or "pending"),
            "isPaid": status == "paid",
            "amount": amount,
            "paidAmount": paid,
            "currency": "VND",
            "networkOrBank": str(beneficiary.get("bankCode") or data.get("provider") or "BANK"),
            "bankBin": str(beneficiary.get("bankBin") or ""),
            "recipientAddress": str(beneficiary.get("accountNumber") or ""),
            "recipientName": str(beneficiary.get("accountHolder") or ""),
            "transferContent": str(data.get("transferContent") or ""),
            "description": str(data.get("description") or ""),
            "paymentUrl": str(data.get("paymentUrl") or data.get("checkoutUrl") or ""),
            "qrContent": str(qr.get("content") or ""),
            "qrImageUrl": str(qr.get("imageUrl") or ""),
            "qrDataUrl": str(qr.get("dataUrl") or ""),
            "cancelToken": data.get("cancelToken"),
            "transactionId": data.get("matchedTransactionId"),
            "remainingSeconds": int(data.get("remainingSeconds") or 0),
            "expiresAt": data.get("expiresAt"),
            "paidAt": data.get("paidAt"),
            "raw": data,
        }

    status = normalize_invoice_status(data.get("status"))
    inv_code = str(data.get("invoiceCode") or data.get("invoice_code") or data.get("trans_id") or data.get("txCode") or "")
    tx_code = str(data.get("txCode") or data.get("trans_id") or inv_code)
    amount = float(data.get("amountUsdt") or data.get("amount") or 0)
    paid = float(
        data.get("receivedUsdt")
        or data.get("receivedAmountUsdt")
        or data.get("received")
        or (amount if status == "paid" else 0)
    )
    return {
        "channel": "usdt",
        "invoiceId": str(data.get("id") or data.get("invoiceId") or tx_code or inv_code),
        "invoiceCode": inv_code or tx_code,
        "txCode": tx_code,
        "orderId": str(data.get("orderId") or data.get("request_id") or data.get("orderCode") or ""),
        "status": status,
        "rawStatus": str(data.get("status") or "waiting"),
        "isPaid": status == "paid",
        "amount": amount,
        "paidAmount": paid,
        "currency": str(data.get("token") or "USDT").upper(),
        "networkOrBank": str(data.get("network") or "TRC20").upper(),
        "bankBin": "",
        "recipientAddress": str(data.get("walletAddress") or data.get("address") or ""),
        "recipientName": str(data.get("networkName") or data.get("network") or "USDT Wallet"),
        "transferContent": str(data.get("orderId") or data.get("request_id") or inv_code),
        "description": str(data.get("description") or ""),
        "paymentUrl": str(data.get("paymentUrl") or data.get("checkoutUrl") or data.get("url_payment") or ""),
        "qrContent": str(data.get("qrContent") or data.get("walletAddress") or data.get("address") or ""),
        "qrImageUrl": str(data.get("qrImageUrl") or data.get("qrcode") or data.get("qr_code") or ""),
        "qrDataUrl": str(data.get("qrDataUrl") or data.get("qrcode") or data.get("qr_code") or ""),
        "transactionId": str(data.get("txHash") or data.get("transaction_id") or "") or None,
        "remainingSeconds": int(data.get("remainingSeconds") or 0),
        "expiresAt": data.get("expiresAt"),
        "paidAt": data.get("paidAt") or data.get("completedAt") or data.get("update_gettime"),
        "raw": data,
    }


def normalize_unified_transaction(
    raw_tx: Mapping[str, Any],
    channel: str,
    bank_code: str = "BANK",
    account_number: str = "",
) -> Dict[str, Any]:
    if channel == "bank":
        raw_amt = str(raw_tx.get("amount") or "0").replace(",", "").strip()
        try:
            numeric_amt = float(raw_amt)
        except ValueError:
            numeric_amt = 0.0
        tx_type = str(raw_tx.get("type") or "IN").strip().upper()
        return {
            "channel": "bank",
            "transactionID": str(raw_tx.get("transactionID") or raw_tx.get("id") or ""),
            "invoiceCode": "",
            "orderId": "",
            "type": "OUT" if tx_type == "OUT" else "IN",
            "status": "completed",
            "amount": numeric_amt,
            "currency": "VND",
            "networkOrBank": str(raw_tx.get("bankCode") or bank_code or "BANK"),
            "recipientAddress": str(raw_tx.get("accountNumber") or account_number or ""),
            "senderAddress": "",
            "description": str(raw_tx.get("description") or ""),
            "transactionDate": str(raw_tx.get("transactionDate") or ""),
            "txHash": "",
            "raw": dict(raw_tx),
        }

    norm_status = normalize_invoice_status(str(raw_tx.get("status") or "completed"))
    amount = float(
        raw_tx.get("received")
        or raw_tx.get("receivedUsdt")
        or raw_tx.get("amount")
        or raw_tx.get("amountUsdt")
        or 0
    )
    tx_id = str(
        raw_tx.get("transaction_id")
        or raw_tx.get("txHash")
        or raw_tx.get("trans_id")
        or raw_tx.get("txCode")
        or raw_tx.get("invoice_code")
        or raw_tx.get("invoiceCode")
        or ""
    )
    return {
        "channel": "usdt",
        "transactionID": tx_id,
        "invoiceCode": str(raw_tx.get("invoice_code") or raw_tx.get("invoiceCode") or raw_tx.get("trans_id") or ""),
        "orderId": str(raw_tx.get("request_id") or raw_tx.get("orderId") or ""),
        "type": "IN",
        "status": "completed" if norm_status == "paid" else norm_status,
        "amount": amount,
        "currency": str(raw_tx.get("token") or "USDT").upper(),
        "networkOrBank": str(raw_tx.get("network") or "TRC20").upper(),
        "recipientAddress": str(raw_tx.get("address") or raw_tx.get("walletAddress") or ""),
        "senderAddress": str(raw_tx.get("from_address") or raw_tx.get("fromAddress") or ""),
        "description": str(
            raw_tx.get("description")
            or raw_tx.get("request_id")
            or raw_tx.get("orderId")
            or raw_tx.get("invoice_code")
            or ""
        ),
        "transactionDate": str(
            raw_tx.get("update_gettime")
            or raw_tx.get("create_gettime")
            or raw_tx.get("completedAt")
            or raw_tx.get("createdAt")
            or ""
        ),
        "txHash": str(raw_tx.get("transaction_id") or raw_tx.get("txHash") or ""),
        "raw": dict(raw_tx),
    }


def match_unified_transactions(
    transactions: Iterable[Mapping[str, Any]],
    *,
    channel: str = "all",
    expected_amount: float = 0.0,
    order_code: str = "",
    tx_hash: str = "",
    exact_amount: bool = False,
    processed_ids: Optional[Set[str]] = None,
    mutate_processed_ids: bool = False,
) -> List[Dict[str, Any]]:
    filter_ch = str(channel or "all").lower()
    needle_raw = str(order_code or "").strip()
    needle_upper = needle_raw.upper()
    needle_compact = normalize_transfer_text(needle_raw, True) if needle_raw else ""
    tx_hash_needle = str(tx_hash or "").strip().lower()
    seen: Set[str] = processed_ids if isinstance(processed_ids, set) else set(processed_ids or [])

    matches: List[Dict[str, Any]] = []
    for item in transactions:
        if filter_ch != "all" and item.get("channel") != filter_ch:
            continue
        tx_id = str(item.get("transactionID") or item.get("invoiceCode") or "").strip()
        if not tx_id or tx_id in seen:
            continue
        if item.get("type") != "IN" or item.get("status") not in ("completed", "paid"):
            continue

        amt = float(item.get("amount") or 0)
        if expected_amount > 0:
            if exact_amount and amt != expected_amount:
                continue
            if not exact_amount and amt < expected_amount:
                continue

        if tx_hash_needle and str(item.get("txHash") or "").lower() != tx_hash_needle:
            continue

        if needle_raw:
            desc = str(item.get("description") or "")
            ord_id = str(item.get("orderId") or "")
            inv_code = str(item.get("invoiceCode") or "")
            direct_hit = (
                needle_upper in desc.upper()
                or ord_id.upper() == needle_upper
                or inv_code.upper() == needle_upper
            )
            compact_hit = bool(
                needle_compact
                and (
                    needle_compact in normalize_transfer_text(desc, True)
                    or normalize_transfer_text(ord_id, True) == needle_compact
                )
            )
            if not direct_hit and not compact_hit:
                continue

        matches.append(dict(item))
        if mutate_processed_ids and isinstance(processed_ids, set):
            processed_ids.add(tx_id)

    return matches
