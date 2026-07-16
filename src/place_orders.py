import asyncio
import os

from dotenv import load_dotenv
from polymarket import AsyncPublicClient, AsyncSecureClient, RelayerApiKey, OpenOrder, OrderResponse
from rich import print

load_dotenv()


async def get_order(client: AsyncSecureClient, order_id: str) -> OpenOrder:
    return await client.get_order(order_id=order_id)


async def BUY_limit_order(client: AsyncSecureClient, token_id: str, price: str, size: str) -> OrderResponse:
    return await client.place_limit_order(
        token_id=token_id,
        side="BUY",
        price=price,
        size=size,
    )

async def SELL_limit_order(client: AsyncSecureClient, token_id: str, price: str, size: str) -> OrderResponse:
    return await client.place_limit_order(
        token_id=token_id,
        side="SELL",
        price=price,
        size=size,
    )


async def BUY_market_order(client: AsyncSecureClient, token_id: str, usdc_amount: str) -> OrderResponse:
    return await client.place_market_order(
        token_id=token_id,
        side="BUY",
        amount=usdc_amount,
    )


async def init_client() -> AsyncSecureClient:
    return await AsyncSecureClient.create(
        private_key=os.getenv("PRIVATE_KEY", ""),
        wallet=os.getenv("WALLET", ""),
        api_key=RelayerApiKey(
            key=os.getenv("RELAYER_API_KEY", ""),
            address=os.getenv("RELAYER_ADDRESS", ""),
        ),
    )


async def main() -> None:
    token_id = "11171618905857319805355893398009978356002287408842633593535559412449299952250"

    # async with await init_client() as client:
    #     #print(await BUY_limit_order(client, token_id, "0.99", "10"))
    #     print(await client.cancel_all())
    client = await init_client()

    response = await BUY_limit_order(client, token_id, "0.9", "15")
    
    print(response)

if __name__ == "__main__":
    asyncio.run(main())