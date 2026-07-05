"""Bróker de mensajería sobre Redis: listas por agente para bandejas de entrada
privadas y un hash compartido para el tablón de ofertas del mercado."""

from __future__ import annotations

from redis.asyncio import Redis

from enclave.models import InboxMessage, MarketOffer

_MARKET_OFFERS_KEY = "enclave:market:offers"


def _inbox_key(agent_id: str) -> str:
    return f"enclave:inbox:{agent_id}"


class RedisMessageBroker:
    """Implementación de `MessageBroker` contra Redis."""

    def __init__(self, redis_url: str) -> None:
        self._redis: Redis = Redis.from_url(redis_url, decode_responses=True)

    async def send_direct_message(self, to_agent: str, message: InboxMessage) -> None:
        await self._redis.rpush(_inbox_key(to_agent), message.model_dump_json())

    async def fetch_inbox(self, agent_id: str) -> list[InboxMessage]:
        key = _inbox_key(agent_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.lrange(key, 0, -1)
            pipe.delete(key)
            raw_messages, _ = await pipe.execute()
        return [InboxMessage.model_validate_json(raw) for raw in raw_messages]

    async def publish_offer(self, offer: MarketOffer) -> None:
        await self._redis.hset(_MARKET_OFFERS_KEY, offer.offer_id, offer.model_dump_json())

    async def fetch_open_offers(self) -> list[MarketOffer]:
        raw_offers = await self._redis.hvals(_MARKET_OFFERS_KEY)
        return [MarketOffer.model_validate_json(raw) for raw in raw_offers]

    async def withdraw_offer(self, offer_id: str) -> None:
        await self._redis.hdel(_MARKET_OFFERS_KEY, offer_id)

    async def aclose(self) -> None:
        await self._redis.aclose()
