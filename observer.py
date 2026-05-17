class IncidentEvent:
    """Represents an incident event in the system"""
    
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data


class EventSystem:
    """
    Observer Pattern
    Agents subscribe to events and
    get notified when incidents happen
    """

    def __init__(self):
        self.subscribers = {}
        self.event_log = []

    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event_type, data):
        event = IncidentEvent(event_type, data)
        self.event_log.append({
            "type": event_type,
            "data": data
        })
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)
        return event

    def get_log(self):
        return self.event_log


# Global event system instance
event_system = EventSystem()