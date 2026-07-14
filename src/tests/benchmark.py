from time import perf_counter
from src.parsers.hex_parser import parse_calldata
from src.tests.manage_hex_data import get_hex_data


def benchmark_func(func, num):
    start_time = perf_counter()
    for _ in range(num):
        func()
    total_time = perf_counter() - start_time
    return  total_time / num 

def format_time(seconds: int | float):
    suffix = ["s", "ms", "µs", "ns"]
    idx = 0
    while seconds < 1 and idx < len(suffix) - 1:
        idx += 1
        seconds *= 1000
    return f"{seconds:.3f}{suffix[idx]}"

def main():
    wallet = "0xf3531b23b504cf0aed4ff21325232b2a2d496685"
    tx_hash = "0x827af17195656ea3857777ffec2cd97fabaa76d682765c2e636365a62ee02e43"
    hex_data = get_hex_data(tx_hash)

    elapsed = benchmark_func(lambda: parse_calldata(hex_data, wallet), 100_000)
    print(format_time(elapsed))
if __name__ == "__main__":
    main()