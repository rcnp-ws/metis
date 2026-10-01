# alert class to contain the information of an alert, including its type, severity, message, and timestamp.
class Alert:
    def __init__(self, alert_type: str, severity: str, message: str, timestamp: float):
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.timestamp = timestamp

    def __repr__(self):
        return f"Alert(type={self.alert_type}, severity={self.severity}, message={self.message}, timestamp={self.timestamp})"
