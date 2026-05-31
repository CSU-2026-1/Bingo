import asyncio
import logging

from app.db.init_db import init_db
from app.services.events import consume_user_registered_events


RECONNECT_DELAY_SECONDS = 5
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    while True:
        try:
            await consume_user_registered_events()
            await asyncio.Future()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "User events consumer stopped. Reconnecting in %s seconds.",
                RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
