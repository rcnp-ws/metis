# generic agent to treat devices such as power supplier, environmental monitors, data acquisition system and so on.
# This agent is designed to be flexible and adaptable to different types of devices and their specific requirements.


# definition of interfaces
# - registration of operations with handler and schema of parameters
# - registration of monitoring with handler and schema of outputs
# - publishing of alerts
# - start and stop


from common.models.alert import Alert


class GenericAgent:
    def __init__(self):
        self.operations = {}
        self.monitoring = {}
        self.alerts = []

    def register_operation(self, name: str, handler: callable, schema: dict) -> None:
        self.operations[name] = {"handler": handler, "schema": schema}

    def register_monitoring(self, name: str, handler: callable, schema: dict) -> None:
        self.monitoring[name] = {"handler": handler, "schema": schema}

    def publish_alert(self, alert: Alert):
        self.alerts.append(alert)

    def start(self):
        # Start the agent's main loop or threads for monitoring and handling operations
        pass

    def stop(self):
        # Stop the agent's main loop or threads
        pass
