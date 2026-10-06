import asyncio
import logging
from datetime import datetime, timezone

from websockets.asyncio.client import connect

from metis.contracts.registration import (
    AgentRegister,
    AgentRegisterHeader,
    AgentRegisterPayload,
    AgentRegistered,
)

from metis.agent.generic import GenericAgent

logger = logging.getLogger(__name__)


async def connect_to_central(
    agent: GenericAgent,
    url: str,
    retry_interval: float = 3.0,
) -> None:
    """Centralへ接続・登録し、切断時には再接続する。"""
    while True:
        try:
            async with connect(url) as websocket:
                registration = AgentRegister(
                    header=AgentRegisterHeader(
                        sent_at=datetime.now(timezone.utc),
                    ),
                    payload=AgentRegisterPayload.model_validate(
                        agent.describe(),
                    ),
                )

                await websocket.send(
                    registration.model_dump_json(),
                )

                raw = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=10.0,
                )
                response = AgentRegistered.model_validate_json(raw)

                if response.payload.agent_id != agent.agent_id:
                    raise ValueError(
                        "Registration response has a different agent_id"
                    )

                logger.info(
                    "Registered with Central: %s",
                    agent.agent_id,
                )

                # 登録後は接続を維持する。
                # 次の段階で操作要求の受信処理を追加する。
                async for message in websocket:
                    logger.warning(
                        "Unexpected message from Central: %s",
                        message,
                    )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Central connection failed: %s",
                agent.agent_id,
            )

        await asyncio.sleep(retry_interval)