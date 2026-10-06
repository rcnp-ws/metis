import logging
from typing import Any

from metis.agent.generic import GenericAgent
from metis.agent.storage import AgentRecordStore

from metis.agent.devices.hello_metis.driver import HelloMetisDriver
from metis.agent.devices.hello_metis.models import GreetingValue, RegisterNameRequest

logger = logging.getLogger(__name__)


async def log_operation_error(
    trace_id: str,
    reason: dict[str, Any],
) -> None:
    logger.error(
        "hello_metis operation error: trace_id=%s reason=%s",
        trace_id,
        reason,
    )


def create_agent(
    *,
    agent_id: str = "hello_metis",
    db_url: str = "sqlite:///hello_metis.db",
    interval: float = 1.0,
) -> tuple[GenericAgent, AgentRecordStore]:
    driver = HelloMetisDriver(interval=interval)
    store = AgentRecordStore(db_url)

    agent = GenericAgent(
        agent_id=agent_id,
        device_type="hello_metis",
        on_start=driver.start,
        on_stop=driver.stop,
        store=store,
        on_operation_error=log_operation_error,
    )

    agent.register_operation(
        name="register_name",
        request_model=RegisterNameRequest,
        handler=driver.register_name,
    )

    agent.register_monitor(
        name="greeting",
        value_model=GreetingValue,
        reader=driver.read_greeting,
    )

    return agent, store