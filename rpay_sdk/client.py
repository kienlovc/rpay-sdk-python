from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Set, Union

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


class RPayError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "RPAY_ERROR",
        status: int = 0,
        endpoint: str = "",
        method: str = "",
        raw_response: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.endpoint = endpoint
        self.method = method
        self.raw_response = raw_response


def normalize_base_url(url_or_domain: Optional[str] = None) -> str:
    trimmed = str(url_or_domain or "").strip().rstrip("/")
    if not trimmed or trimmed in ("auto", "current"):
        return RPAY_DEFAULT_BASE_URL
    if not trimmed.lower().startswith(("http://", "https://")):
        is_local = trimmed.startswith(("localhost", "127.0.0.1", "[::1]"))
        trimmed = f"{'http' if is_local else 'https'}://{trimmed}"
    return trimmed


def extract_host_from_url(url_or_domain: Optional[str] = None) -> str:
    norm = normalize_base_url(url_or_domain)
    parsed = urllib.parse.urlparse(norm)
    return (parsed.hostname or "").strip()


def encode_url_segment(segment: Any) -> str:
    return urllib.parse.quote(str(segment or ""), safe="").replace("#", "%23")


def append_query_params(base_path: str, query: Optional[Mapping[str, Any]] = None) -> str:
    if not query:
        return base_path
    clean = {k: str(v) for k, v in query.items() if v is not None and v != ""}
    if not clean:
        return base_path
    qs = urllib.parse.urlencode(clean)
    return f"{base_path}&{qs}" if "?" in base_path else f"{base_path}?{qs}"


class RPayClient:
    """
    Official RPAY Payment & Banking SDK Client for Python.
    Supports Zero-Config `.env` loading, Multi-Domain (`domain`, `for_domain`),
    and Unified Bank (VND) + Crypto (USDT/USDC) APIs (`pay`, `check`, `lsgd`, `qr`, `route`).
    """

    def __init__(
        self,
        *,
        domain: Optional[str] = None,
        base_url: Optional[str] = None,
        site_domain: Optional[str] = None,
        site_id: Optional[str] = None,
        bank_token: Optional[str] = None,
        api_token: Optional[str] = None,
        merchant_id: Optional[str] = None,
        usdt_key: Optional[str] = None,
        usdt_api_key: Optional[str] = None,
        secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout_sec: Optional[float] = None,
        transport: Optional[Callable[[str, str, Dict[str, str], Optional[bytes], float], Any]] = None,
    ) -> None:
        env_domain = os.environ.get("RPAY_DOMAIN") or os.environ.get("RPAY_BASE_URL") or ""
        raw_origin = domain or base_url or env_domain or RPAY_DEFAULT_BASE_URL
        resolved_bank_token = (
            bank_token
            or api_token
            or os.environ.get("RPAY_BANK_TOKEN")
            or os.environ.get("RPAY_API_TOKEN")
            or os.environ.get("RPAY_TOKEN")
            or ""
        )
        resolved_usdt_key = (
            usdt_key
            or usdt_api_key
            or os.environ.get("RPAY_USDT_API_KEY")
            or os.environ.get("RPAY_USDT_KEY")
            or os.environ.get("RPAY_API_KEY")
            or resolved_bank_token
            or ""
        )
        self.base_url: str = normalize_base_url(raw_origin)
        self.domain: str = normalize_base_url(domain or env_domain) if (domain or env_domain) else ""
        self.site_domain: str = (
            site_domain
            or os.environ.get("RPAY_SITE_DOMAIN")
            or (extract_host_from_url(domain) if domain and domain not in ("auto", "current") else "")
        )
        self.site_id: str = site_id or os.environ.get("RPAY_SITE_ID") or ""
        self.api_token: str = resolved_bank_token
        self.merchant_id: str = (
            merchant_id
            or os.environ.get("RPAY_MERCHANT_ID")
            or os.environ.get("RPAY_USDT_MERCHANT_ID")
            or ""
        )
        self.usdt_api_key: str = resolved_usdt_key
        self.webhook_secret: str = (
            secret
            or webhook_secret
            or os.environ.get("RPAY_WEBHOOK_SECRET")
            or os.environ.get("RPAY_SIGNATURE_KEY")
            or os.environ.get("RPAY_SECRET")
            or ""
        )
        self.timeout_sec: float = float(timeout_sec or RPAY_DEFAULT_TIMEOUT_SEC)
        self._transport = transport
        self._domain_clients: Dict[str, RPayClient] = {}

    def init(self, **kwargs: Any) -> "RPayClient":
        return self.configure(**kwargs)

    def configure(self, **kwargs: Any) -> "RPayClient":
        if "domain" in kwargs or "base_url" in kwargs:
            target = kwargs.get("domain") or kwargs.get("base_url") or RPAY_DEFAULT_BASE_URL
            self.base_url = normalize_base_url(target)
            if kwargs.get("domain"):
                self.domain = normalize_base_url(kwargs["domain"])
                if not kwargs.get("site_domain"):
                    self.site_domain = extract_host_from_url(kwargs["domain"])
        if "site_domain" in kwargs and kwargs["site_domain"] is not None:
            self.site_domain = str(kwargs["site_domain"])
        if "site_id" in kwargs and kwargs["site_id"] is not None:
            self.site_id = str(kwargs["site_id"])
        for k in ("bank_token", "api_token"):
            if kwargs.get(k) is not None:
                self.api_token = str(kwargs[k])
        if kwargs.get("merchant_id") is not None:
            self.merchant_id = str(kwargs["merchant_id"])
        for k in ("usdt_key", "usdt_api_key"):
            if kwargs.get(k) is not None:
                self.usdt_api_key = str(kwargs[k])
        for k in ("secret", "webhook_secret"):
            if kwargs.get(k) is not None:
                self.webhook_secret = str(kwargs[k])
        if kwargs.get("timeout_sec") is not None:
            self.timeout_sec = float(kwargs["timeout_sec"])
        if "transport" in kwargs:
            self._transport = kwargs["transport"]
        return self

    def for_domain(self, domain: str, **overrides: Any) -> "RPayClient":
        host = extract_host_from_url(domain).lower()
        if not host:
            return self
        if not overrides and host in self._domain_clients:
            return self._domain_clients[host]
        child = RPayClient(
            domain=overrides.get("domain", domain),
            site_domain=overrides.get("site_domain", host),
            site_id=overrides.get("site_id", self.site_id),
            bank_token=overrides.get("bank_token") or overrides.get("api_token") or self.api_token,
            merchant_id=overrides.get("merchant_id", self.merchant_id),
            usdt_key=overrides.get("usdt_key") or overrides.get("usdt_api_key") or self.usdt_api_key,
            secret=overrides.get("secret") or overrides.get("webhook_secret") or self.webhook_secret,
            timeout_sec=overrides.get("timeout_sec", self.timeout_sec),
            transport=overrides.get("transport", self._transport),
        )
        self._domain_clients[host] = child
        return child

    def request(
        self,
        method: str,
        path: str,
        *,
        domain: Optional[str] = None,
        site_domain: Optional[str] = None,
        site_id: Optional[str] = None,
        query: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        origin = normalize_base_url(domain or self.base_url)
        path_with_query = append_query_params(path, query)
        full_url = (
            path_with_query
            if path_with_query.startswith(("http://", "https://"))
            else f"{origin}{path_with_query if path_with_query.startswith('/') else '/' + path_with_query}"
        )
        http_method = method.upper()
        req_headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "rpay-sdk-python/1.0.0",
        }
        if headers:
            req_headers.update(headers)

        eff_site_domain = site_domain or (extract_host_from_url(domain) if domain else self.site_domain)
        if eff_site_domain:
            req_headers.setdefault("X-Site-Domain", eff_site_domain)
            req_headers.setdefault("X-Forwarded-Host", eff_site_domain)
        eff_site_id = site_id or self.site_id
        if eff_site_id:
            req_headers.setdefault("X-Site-ID", eff_site_id)
        if bearer_token:
            req_headers["Authorization"] = f"Bearer {bearer_token}"
        if api_key:
            req_headers["X-API-Key"] = api_key
        if idempotency_key:
            req_headers["Idempotency-Key"] = idempotency_key

        body_bytes: Optional[bytes] = None
        if body is not None and http_method not in ("GET", "HEAD"):
            clean_body = {k: v for k, v in body.items() if v is not None}
            req_headers.setdefault("Content-Type", "application/json")
            body_bytes = json.dumps(clean_body).encode("utf-8")

        if self._transport is not None:
            parsed = self._transport(http_method, full_url, req_headers, body_bytes, self.timeout_sec)
        else:
            req = urllib.request.Request(full_url, data=body_bytes, headers=req_headers, method=http_method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    raw_text = resp.read().decode("utf-8")
                    parsed = json.loads(raw_text) if raw_text else {}
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_text)
                except Exception:
                    err_json = None
                msg = (
                    (err_json or {}).get("message")
                    or (err_json or {}).get("msg")
                    or f"Yêu cầu RPAY thất bại với mã HTTP {e.code}"
                )
                code = (err_json or {}).get("code") or f"HTTP_{e.code}"
                raise RPayError(
                    str(msg),
                    code=str(code),
                    status=e.code,
                    endpoint=full_url,
                    method=http_method,
                    raw_response=err_json,
                ) from e
            except Exception as e:
                raise RPayError(
                    f"Không thể kết nối máy chủ RPAY ({http_method} {path}): {e}",
                    code="NETWORK_ERROR",
                    endpoint=full_url,
                    method=http_method,
                ) from e

        if isinstance(parsed, Mapping):
            if parsed.get("status") == "error" or parsed.get("isSuccess") is False or parsed.get("success") is False:
                err_msg = parsed.get("message") or parsed.get("msg") or "Yêu cầu bị từ chối bởi RPAY."
                err_code = parsed.get("code") or "RPAY_API_ERROR"
                raise RPayError(
                    str(err_msg),
                    code=str(err_code),
                    status=int(parsed.get("status") if isinstance(parsed.get("status"), int) else 400),
                    endpoint=full_url,
                    method=http_method,
                    raw_response=parsed,
                )
        return parsed

    # =========================================================================
    # 4 CORE ONE-LINERS: pay, check, lsgd, qr (+ route)
    # =========================================================================

    def pay(self, **params: Any) -> Dict[str, Any]:
        """
        Tạo hóa đơn thanh toán hợp nhất cho cả Bank (VNĐ) và Crypto (USDT/USDC trên 18 mạng lưới).
        """
        return self.create_invoice(**params)

    def create_invoice(self, **params: Any) -> Dict[str, Any]:
        channel = detect_payment_channel(params, "bank")
        domain = params.pop("domain", None)
        site_id = params.pop("site_id", None) or params.pop("siteId", None)
        idempotency_key = params.pop("idempotency_key", None) or params.pop("idempotencyKey", None)

        if channel == "usdt":
            api_key = (
                params.get("apiKey")
                or params.get("api_key")
                or params.get("usdt_key")
                or self.usdt_api_key
                or self.api_token
            )
            if not api_key:
                raise RPayError("Vui lòng cung cấp RPAY_USDT_API_KEY để tạo hóa đơn USDT/USDC.", code="MISSING_USDT_API_KEY")

            amount_usdt = float(params.get("amountUsdt") or params.get("amount_usdt") or params.get("amount") or 0)
            body = {
                "siteId": site_id or self.site_id or None,
                "merchantId": params.get("merchantId") or params.get("merchant_id") or self.merchant_id or None,
                "orderId": params.get("orderId") or params.get("order_id") or params.get("request_id"),
                "amountUsdt": amount_usdt,
                "network": params.get("network") or "TRC20",
                "token": str(params.get("token") or params.get("currency") or "USDT").upper(),
                "walletAddress": params.get("walletAddress") or params.get("address"),
                "expireMinutes": params.get("expireMinutes") or params.get("expire_minutes"),
                "description": params.get("description"),
                "callbackUrl": params.get("callbackUrl") or params.get("callback_url"),
                "returnUrl": params.get("returnUrl") or params.get("redirectUrl"),
                "cancelUrl": params.get("cancelUrl") or params.get("cancel_url"),
            }
            raw = self.request(
                "POST",
                "/api/public/usdt-invoices",
                domain=domain,
                site_id=site_id,
                body=body,
                bearer_token=api_key,
                api_key=api_key,
                idempotency_key=idempotency_key,
            )
            return normalize_unified_invoice(raw, "usdt")

        token = (
            params.get("apiToken")
            or params.get("api_token")
            or params.get("bank_token")
            or self.api_token
        )
        if not token:
            raise RPayError("Vui lòng cung cấp RPAY_BANK_TOKEN để tạo hóa đơn ngân hàng.", code="MISSING_API_TOKEN")

        amount_vnd = round(float(params.get("amountVnd") or params.get("amount_vnd") or params.get("amount") or 0))
        if amount_vnd < 1000:
            raise RPayError("Số tiền hóa đơn ngân hàng tối thiểu là 1.000 VNĐ.", code="INVALID_AMOUNT")

        body = {
            "amountVnd": amount_vnd,
            "orderId": params.get("orderId") or params.get("order_id"),
            "transferContent": params.get("transferContent") or params.get("transfer_content"),
            "description": params.get("description"),
            "expireMinutes": params.get("expireMinutes") or params.get("expire_minutes"),
            "qrLogoMode": params.get("qrLogoMode"),
            "qrLogoUrl": params.get("qrLogoUrl"),
            "redirectUrl": params.get("redirectUrl") or params.get("returnUrl"),
            "cancelUrl": params.get("cancelUrl"),
            "callbackUrl": params.get("callbackUrl") or params.get("callback_url"),
            "webhookSecret": params.get("webhookSecret") or params.get("webhook_secret"),
            "provider": params.get("provider"),
        }
        raw = self.request(
            "POST",
            "/api/public/bank-invoices",
            domain=domain,
            site_id=site_id,
            body=body,
            bearer_token=token,
            idempotency_key=idempotency_key,
        )
        return normalize_unified_invoice(raw, "bank")

    def status(self, invoice_code: str, *, channel: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
        return self.get_invoice(invoice_code, channel=channel, domain=domain)

    def get_invoice(self, invoice_code: str, *, channel: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
        ch = channel or detect_payment_channel(invoice_code, "bank")
        code = encode_url_segment(invoice_code)
        path = f"/api/public/usdt-invoices/{code}" if ch == "usdt" else f"/api/public/bank-invoices/{code}"
        raw = self.request("GET", path, domain=domain)
        return normalize_unified_invoice(raw, ch)

    def check(self, invoice_code: str, *, channel: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
        return self.check_invoice(invoice_code, channel=channel, domain=domain)

    def check_invoice(self, invoice_code: str, *, channel: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
        ch = channel or detect_payment_channel(invoice_code, "bank")
        code = encode_url_segment(invoice_code)
        path = f"/api/public/usdt-invoices/{code}/check" if ch == "usdt" else f"/api/public/bank-invoices/{code}/check"
        raw = self.request("POST", path, domain=domain, body={})
        return normalize_unified_invoice(raw, ch)

    def qr(
        self,
        *,
        bank: str,
        account: str,
        amount: Optional[Union[int, float, str]] = None,
        memo: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        spec = resolve_bank_spec(bank)
        body = {
            "bank": spec["code"] if spec else bank,
            "bankBin": spec["bin"] if spec else bank,
            "bankNumber": account,
            "amount": str(amount) if amount is not None else None,
            "purpose": memo,
        }
        res = self.request("POST", "/api/qr/vietqr", domain=domain, body=body)
        return res.get("data", res) if isinstance(res, Mapping) else res

    def lsgd(self, **params: Any) -> Dict[str, Any]:
        return self.get_history(**params)

    def get_history(self, **params: Any) -> Dict[str, Any]:
        raw_ch = str(params.get("channel") or params.get("type") or "").strip().lower()
        target_ch = "bank"
        if raw_ch in ("all", "both"):
            target_ch = "all"
        elif raw_ch in ("usdt", "crypto", "usdc"):
            target_ch = "usdt"
        elif params.get("network") or str(params.get("token") or "").upper() in ("USDT", "USDC"):
            target_ch = "usdt"

        domain = params.get("domain")
        site_id = params.get("site_id") or params.get("siteId")

        def _fetch_bank() -> Any:
            version = str(params.get("version") or "v2").lower()
            token = params.get("bank_token") or params.get("token") or self.api_token
            if not token:
                raise RPayError("Vui lòng cung cấp RPAY_BANK_TOKEN để lấy LSGD ngân hàng.", code="MISSING_BANK_TOKEN")
            bank_spec = resolve_bank_spec(params.get("bank")) if params.get("bank") else None
            slug = bank_spec["primarySlug"] if bank_spec else ""

            if version == "pos":
                raw_res = self.request(
                    "POST",
                    "/api/pos/transactions",
                    domain=domain,
                    site_id=site_id,
                    body={"token": token, "fromDate": params.get("fromDate"), "toDate": params.get("toDate"), "limit": params.get("limit")},
                )
            elif version == "v3":
                is_vtm = bool(bank_spec and bank_spec.get("v3UsesPhonePin"))
                v3_path = f"/historyapi{slug}v3" if slug else "/v3"
                v3_body = (
                    {"phone": params.get("phone"), "pin": params.get("pin"), "token": token}
                    if is_vtm
                    else {"password": params.get("password"), "accountNumber": params.get("accountNumber"), "token": token}
                )
                raw_res = self.request("POST", v3_path, domain=domain, site_id=site_id, body=v3_body)
            else:
                v2_path = f"/historyapi{slug}v2" if slug else "/v2"
                raw_res = self.request(
                    "POST",
                    v2_path,
                    domain=domain,
                    site_id=site_id,
                    body={"token": token, "fromDate": params.get("fromDate"), "toDate": params.get("toDate"), "limit": params.get("limit")},
                )

            raw_list = raw_res.get("transactions") or (raw_res.get("data") or {}).get("transactions") or []
            bank_code = raw_res.get("bankCode") or (bank_spec["code"] if bank_spec else "BANK")
            acct = raw_res.get("accountNumber") or params.get("accountNumber") or ""
            txs = [normalize_unified_transaction(t, "bank", bank_code=bank_code, account_number=acct) for t in raw_list]
            return raw_res, txs

        def _fetch_usdt() -> Any:
            m_id = params.get("merchant_id") or params.get("merchantId") or self.merchant_id
            u_key = params.get("usdt_key") or params.get("usdt_api_key") or params.get("api_key") or self.usdt_api_key
            if not m_id or not u_key:
                raise RPayError("Vui lòng cung cấp RPAY_MERCHANT_ID và RPAY_USDT_API_KEY để lấy LSGD USDT.", code="MISSING_USDT_CREDENTIALS")
            raw_res = self.request(
                "POST",
                "/api/GetInvoiceHistory",
                domain=domain,
                site_id=site_id,
                body={
                    "merchant_id": m_id,
                    "api_key": u_key,
                    "network": params.get("network"),
                    "status": params.get("status"),
                    "limit": params.get("limit"),
                    "page": params.get("page"),
                },
            )
            data_part = raw_res.get("data") if isinstance(raw_res, Mapping) else {}
            raw_list = (
                data_part.get("items")
                if isinstance(data_part, Mapping) and isinstance(data_part.get("items"), list)
                else (data_part if isinstance(data_part, list) else [])
            )
            txs = [normalize_unified_transaction(item, "usdt") for item in raw_list]
            return raw_res, txs

        if target_ch == "all":
            raw_b, txs_b = _fetch_bank()
            raw_u, txs_u = _fetch_usdt()
            merged = txs_b + txs_u
            return {
                "channel": "all",
                "count": len(merged),
                "transactions": merged,
                "bankTransactions": txs_b,
                "usdtTransactions": txs_u,
                "raw": {"bank": raw_b, "usdt": raw_u},
            }

        if target_ch == "usdt":
            raw_u, txs_u = _fetch_usdt()
            return {"channel": "usdt", "count": len(txs_u), "transactions": txs_u, "raw": raw_u}

        raw_b, txs_b = _fetch_bank()
        return {"channel": "bank", "count": len(txs_b), "transactions": txs_b, "raw": raw_b}

    def match_payment(
        self,
        transactions: Iterable[Mapping[str, Any]],
        *,
        order_code: str = "",
        expected_amount: float = 0.0,
        channel: str = "all",
        processed_ids: Optional[Set[str]] = None,
        mutate_processed_ids: bool = False,
    ) -> List[Dict[str, Any]]:
        return match_unified_transactions(
            transactions,
            channel=channel,
            expected_amount=expected_amount,
            order_code=order_code,
            processed_ids=processed_ids,
            mutate_processed_ids=mutate_processed_ids,
        )

    def build_v3_get_url(
        self,
        *,
        bank: Optional[str] = None,
        password: Optional[str] = None,
        account_number: Optional[str] = None,
        phone: Optional[str] = None,
        pin: Optional[str] = None,
        token: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> str:
        eff_token = token or self.api_token
        spec = resolve_bank_spec(bank) if bank else None
        is_vtm = bool((spec and spec.get("v3UsesPhonePin")) or (phone and pin and not password))
        seg1 = (phone or account_number or "") if is_vtm else (password or pin or "")
        seg2 = (pin or password or "") if is_vtm else (account_number or phone or "")
        if not seg1 or not seg2 or not eff_token:
            raise RPayError("Thiếu thông tin xác thực V3 (password/accountNumber/token hoặc phone/pin/token).", code="MISSING_V3_CREDENTIALS")
        slug = spec["primarySlug"] if spec else (str(bank).lower() if bank else "")
        prefix = f"/historyapi{slug}v3" if slug else "/v3"
        origin = normalize_base_url(domain or self.base_url)
        return f"{origin}{prefix}/{encode_url_segment(seg1)}/{encode_url_segment(seg2)}/{encode_url_segment(eff_token)}"

    def verify_webhook(
        self,
        *,
        payload: Optional[Union[Mapping[str, Any], str, bytes]] = None,
        raw_body: Optional[Union[str, bytes]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        return verify_webhook(
            payload=payload,
            raw_body=raw_body,
            headers=headers,
            secret=secret or self.webhook_secret,
        )

    def route(self, **options: Any) -> Dict[str, Any]:
        if "payload" in options or "raw_body" in options or "headers" in options:
            res = self.verify_webhook(
                payload=options.get("payload"),
                raw_body=options.get("raw_body"),
                headers=options.get("headers"),
                secret=options.get("secret"),
            )
            return {"ok": res["verified"], "mode": "webhook", "provider": options.get("provider", "9ROUTER"), "security": "HMAC_256", **res}

        if options.get("amount") is not None or options.get("bank") is not None or options.get("network") is not None:
            spec = resolve_bank_spec(options.get("bank")) if options.get("bank") else None
            if (self.api_token and options.get("bank")) or options.get("network"):
                inv = self.create_invoice(**options)
                return {"ok": True, "mode": "payment", "provider": options.get("provider", "9ROUTER"), "security": "HMAC_256", "invoice": inv}
            return {
                "ok": True,
                "mode": "payment",
                "provider": options.get("provider", "9ROUTER"),
                "security": "HMAC_256",
                "bank": spec,
                "amount": float(options.get("amount") or 0),
            }

        coalesced = str(options.get("coalesced") or "498.310 req")
        return {
            "ok": True,
            "mode": "router",
            "provider": str(options.get("provider") or "9ROUTER"),
            "security": str(options.get("security") or "HMAC_256"),
            "coalesced": coalesced,
            "socketLive": True,
            "connectedBanksCount": 10,
            "totalBanksCount": len(RPAY_BANKS),
            "badge": f"10/{len(RPAY_BANKS)} BANK",
        }


def create_client(**config: Any) -> RPayClient:
    return RPayClient(**config)


rpay = RPayClient()
