# rpay-sdk (Python) — Thư viện Tích hợp Thanh toán Tự động RPAY (Bank VietQR VNĐ & Crypto USDT/USDC)

Thư viện Python chính thức cho cổng thanh toán **RPAY (`https://api.rpay.vn` & hệ thống Web con / Multi-Domain)** dành cho **FastAPI, Flask, Django, Tornado & Cronjob Workers**.

- **Zero-Config (Tự động đọc `.env` / `os.environ`)**: Không cần viết code khởi tạo rườm rà.
- **Không phụ thuộc ngoài (Zero External Dependencies)**: Chỉ dùng thư viện chuẩn của Python (`urllib.request`, `hmac`, `hashlib`, `json`).
- **Hợp nhất Cả Bank (15 cổng VietQR VNĐ) & Crypto (USDT/USDC trên 18 mạng lưới)**: Dùng chung 4 hàm `rpay.pay(...)`, `rpay.check(...)`, `rpay.lsgd(...)`, `rpay.qr(...)`.
- **Hỗ trợ Đa Tên Miền (`Multi-Domain`)**: `rpay.for_domain("pay.shopa.vn")` hoặc truyền `domain="pay.shopb.com"` ngay trong từng hàm.

---

## 1. Cài đặt & Cấu hình `.env`

```bash
pip install rpay-sdk
```

Khai báo biến môi trường trong `.env` (hoặc `os.environ`):

```env
RPAY_DOMAIN=https://api.rpay.vn
RPAY_BANK_TOKEN=rpay_vcb_live_123456_abcdef123456
RPAY_MERCHANT_ID=MRCH-0001
RPAY_USDT_API_KEY=ukey_live_xxxxxxxxxxxxxxxx
RPAY_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxx
```

---

## 2. 4 Hàm Cốt lõi Dễ Dùng Nhất (`pay`, `check`, `lsgd`, `qr`)

```python
import rpay_sdk as rpay

# 1. Tạo hóa đơn Ngân hàng (VietQR VNĐ)
bank_order = rpay.pay(
    channel="bank",
    amount=250000,
    orderId="DH1001",
    description="Nạp tiền tài khoản",
    callbackUrl="https://webcuaban.com/api/webhooks/rpay",
)

# 2. Tạo hóa đơn Crypto (USDT / USDC trên 18 mạng lưới)
crypto_order = rpay.pay(
    channel="usdt",
    network="TRC20",  # TRC20, BEP20, ERC20, SOLANA, TON, POLYGON, ARBITRUM, BASE...
    token="USDT",
    amount=50,
    orderId="DH1002",
    callbackUrl="https://webcuaban.com/api/webhooks/rpay",
)

print(bank_order["invoiceCode"], bank_order["paymentUrl"], bank_order["qrImageUrl"])

# 3. Kiểm tra & Gạch nợ tức thì (Tự phân biệt RPINV... của Bank và USINV.../USTX... của USDT)
checked = rpay.check(bank_order["invoiceCode"])
if checked["isPaid"]:
    print("Khách đã thanh toán:", checked["paidAmount"], checked["currency"])

# 4. Tạo nhanh mã VietQR động
qr = rpay.qr(bank="MB", account="0123456789", amount=150000, memo="DH1001")
print(qr["qrDataUrl"], qr["qrImageUrl"])
```

---

## 3. Lấy Lịch sử Giao dịch (LSGD) & Đối soát Chống Trùng (`rpay.lsgd` & `rpay.match_payment`)

```python
import rpay_sdk as rpay

processed_ids = set()

# Lấy đồng thời cả LSGD Ngân hàng (V2) + LSGD USDT trong 1 lệnh:
history = rpay.lsgd(channel="all", bank="VCB", limit=50)

matches = rpay.match_payment(
    history["transactions"],
    order_code="DH1001",
    expected_amount=250000,
    processed_ids=processed_ids,
    mutate_processed_ids=True,  # Tự động thêm transactionID vào processed_ids
)

if matches:
    tx = matches[0]
    print(f"Đã khớp đơn qua {tx['channel']}: +{tx['amount']} {tx['currency']} (Mã GD: {tx['transactionID']})")
```

---

## 4. Tích hợp Nhận Webhook `HMAC-SHA256` (FastAPI / Flask / Django)

### Ví dụ với FastAPI:

```python
from fastapi import FastAPI, HTTPException, Request
import rpay_sdk as rpay

app = FastAPI()

@app.post("/api/webhooks/rpay")
async def rpay_webhook(request: Request):
    raw_body = await request.body()
    event = rpay.verify_webhook(
        raw_body=raw_body,
        headers=dict(request.headers),
    )
    if not event["verified"]:
        raise HTTPException(status_code=401, detail=event["reason"])

    # Tự động chuẩn hóa chung cho cả Bank Invoice (VND) và Crypto Invoice (USDT/USDC):
    print("Kênh:", event["channel"], "Đơn:", event["orderId"], "Thực nhận:", event["paidAmount"], event["currency"])
    return {"success": True, "received": True}
```

---

## 5. Dùng trên Nhiều Tên Miền (`Multi-Domain`)

```python
import rpay_sdk as rpay

shop_a = rpay.for_domain("pay.shopa.vn", bank_token="rpay_vcb_live_shopA...")
shop_b = rpay.for_domain("pay.shopb.com", bank_token="rpay_mb_live_shopB...")

inv_a = shop_a.pay(channel="bank", amount=200000, orderId="A-01")
inv_b = shop_b.pay(channel="usdt", network="BEP20", amount=30, orderId="B-01")
```

---

## 6. Xuất bản lên PyPI

```bash
cd C:\Users\kotin\Desktop\rpayv2\plugin\python
python -m unittest discover -s tests
pip install build twine
python -m build
twine upload dist/*
```
