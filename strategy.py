class RemediationStrategy:
    """
    Strategy Pattern base class
    Different strategies for fixing incidents
    """
    def execute(self, service_name):
        raise NotImplementedError


class RestartStrategy(RemediationStrategy):
    """Strategy for restarting crashed services"""
    
    def execute(self, service_name):
        print(f"  🔄 Strategy: Restarting {service_name}")
        return {
            "strategy": "RestartStrategy",
            "action": "restart",
            "service": service_name,
            "status": "success",
            "message": f"Service {service_name} restarted"
        }


class ScaleUpStrategy(RemediationStrategy):
    """Strategy for scaling up resources"""
    
    def execute(self, service_name):
        print(f"  📈 Strategy: Scaling up {service_name}")
        return {
            "strategy": "ScaleUpStrategy",
            "action": "scale_up",
            "service": service_name,
            "status": "success",
            "message": f"Scaled up {service_name} by 1 instance"
        }


class RollbackStrategy(RemediationStrategy):
    """Strategy for rolling back deployments"""
    
    def execute(self, service_name):
        print(f"  ⏪ Strategy: Rolling back {service_name}")
        return {
            "strategy": "RollbackStrategy",
            "action": "rollback",
            "service": service_name,
            "status": "success",
            "message": f"Rolled back {service_name} to previous version"
        }


class StrategySelector:
    """
    Selects the right remediation strategy
    based on the root cause diagnosis
    """
    
    @staticmethod
    def select(root_cause):
        root_cause_lower = root_cause.lower()
        
        if "deployment" in root_cause_lower:
            return RollbackStrategy()
        elif "cpu" in root_cause_lower or "load" in root_cause_lower:
            return ScaleUpStrategy()
        elif "crash" in root_cause_lower or "restart" in root_cause_lower:
            return RestartStrategy()
        else:
            return RestartStrategy()