from typing import Optional

from src.types import Transaction

DECIMALS = 1_000_000
W = 64
SEL = 8

def parse_calldata(calldata: str | None, target_wallet: str) -> Optional[Transaction]:
    if calldata is None:
        return None
    data = calldata.lower().removeprefix("0x").strip()
    wallet_word = target_wallet.lower().removeprefix("0x").zfill(64)
    target_wallet_lc = target_wallet.lower()

    if data[:SEL] != "3c2b4399":
        return None

    def w(n: int) -> str:
        return data[SEL + n * W : SEL + (n + 1) * W]

    def u(n: int) -> int:
        return int(w(n), 16)

    def addr(word: str) -> str:
        return "0x" + word[-40:]

    taker_fill = u(3)
    taker_fee = u(5)

    taker_maker_word = w(8)
    taker_token_id = "0x" + w(10)
    taker_maker_amount = u(11)
    taker_taker_amount = u(12)
    taker_side = u(13)
    taker_timestamp = u(15)

    makers_start = u(2) // 32
    maker_count = u(makers_start)

    fills_start = u(4) // 32
    fill_count = u(fills_start)
    maker_fill_amounts = [u(fills_start + 1 + i) for i in range(fill_count)]

    fees_start = u(6) // 32
    fee_count = u(fees_start)
    maker_fee_amounts = [u(fees_start + 1 + i) for i in range(fee_count)]

    maker_orders = []
    for i in range(maker_count):
        elem_offset_words = u(makers_start + 1 + i) // 32
        elem_start = makers_start + 1 + elem_offset_words

        maker_orders.append({
            "maker": addr(w(elem_start + 1)),
            "signer": addr(w(elem_start + 2)),
            "tokenId": "0x" + w(elem_start + 3),
            "makerAmount": u(elem_start + 4),
            "takerAmount": u(elem_start + 5),
            "side": u(elem_start + 6),
            "signatureType": u(elem_start + 7),
            "timestamp": u(elem_start + 8),
        })

    def shares_received_by_taker_BUY() -> int:
        shares_raw = 0
        wanted_token = taker_token_id.lower()

        for i, order in enumerate(maker_orders):
            fill = maker_fill_amounts[i]
            maker_token = order["tokenId"].lower()
            maker_amount = int(order["makerAmount"])
            taker_amount = int(order["takerAmount"])
            side = int(order["side"])

            if maker_token == wanted_token:
                if side == 1:
                    shares_raw += fill
            else:
                if side == 0 and maker_amount:
                    shares_raw += taker_amount * fill // maker_amount

        return shares_raw

    if taker_maker_word == wallet_word:
        if taker_side == 0:
            shares_raw = shares_received_by_taker_BUY()
            usdc_raw = taker_fill
            action = "BUY"

        elif taker_side == 1:
            shares_raw = taker_fill
            usdc_raw = taker_taker_amount * taker_fill // taker_maker_amount
            usdc_raw -= taker_fee
            action = "SELL"

        else:
            return None

        return Transaction(
            wallet=target_wallet_lc,
            token_id=taker_token_id,
            shares=shares_raw / DECIMALS,
            usdc_amount=usdc_raw / DECIMALS,
            fee=taker_fee / DECIMALS,
            action=action,
            timestamp=taker_timestamp / 1000
        )
    total_shares_raw = 0
    total_usdc_raw = 0
    token_id = None
    action = None
    maker_timestamp = 0

    for i, order in enumerate(maker_orders):
        if order["maker"].lower() != target_wallet_lc:
            continue

        fill = maker_fill_amounts[i]
        fee = maker_fee_amounts[i] if i < len(maker_fee_amounts) else 0

        maker_amount = int(order["makerAmount"])
        taker_amount = int(order["takerAmount"])
        side = int(order["side"])

        token_id = token_id or order["tokenId"]
        maker_timestamp = order["timestamp"]

        if side == 0:
            usdc_raw = fill
            shares_raw = taker_amount * fill // maker_amount if maker_amount else 0
            order_action = "BUY"

        elif side == 1:
            shares_raw = fill
            usdc_raw = taker_amount * fill // maker_amount if maker_amount else 0
            usdc_raw -= fee
            order_action = "SELL"

        else:
            continue

        action = action or order_action
        total_shares_raw += shares_raw
        total_usdc_raw += usdc_raw


    if token_id is None:
        return None
    
    return Transaction(
        wallet=target_wallet_lc,
        token_id=token_id,
        shares=total_shares_raw / DECIMALS,
        usdc_amount=total_usdc_raw / DECIMALS,
        fee=fee / DECIMALS,
        action=action, 
        timestamp=maker_timestamp / 1000
    )