
W = 64
SEL = 8

def is_taker(calldata: str | None, wallet: str):
    if calldata is None:
        return 
    data = calldata.lower().removeprefix("0x").strip()
    wallet_word = wallet.lower().removeprefix("0x").zfill(64)

    def w(n: int):
        return data[SEL + W * n: SEL + W * (n + 1)]

    return w(8) == wallet_word
