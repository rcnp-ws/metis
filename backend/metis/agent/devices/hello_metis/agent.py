# backend/src/metis/devices/hello_metis/agent.py

from metis.agent.generic import GenericAgent

from .driver import HelloMetisDriver
from .models import (
    HelloMetisConfig,
    HelloMetisState,
    RegisterNameRequest,
    RegisterNameResult,
)


def create_agent(
    *,
    agent_id: str,
    config: HelloMetisConfig | None = None,
) -> GenericAgent:
    """hello_metis の driver と GenericAgent を組み立てる。"""

    if config is None:
        config = HelloMetisConfig()

    driver = HelloMetisDriver(config)

    agent = GenericAgent(
        agent_id=agent_id,
        device_type="hello_metis",
        on_start=driver.start,
        on_stop=driver.stop,
    )

    agent.register_operation(
        name="register_name",
        request_model=RegisterNameRequest,
        result_model=RegisterNameResult,
        handler=driver.register_name,
    )

    agent.register_monitor(
        name="state",
        state_model=HelloMetisState,
        reader=driver.read_state,
    )

    return agent
