from enum import Enum

# Enum to track the status of customer orders
class EnvironmentDefinition(Enum):
    FREE = 0
    FREE_TABLE = 1
    KITCHEN = 2
    CUSTOMER = 3
    WAITER = 4
    MANAGER = 5
    

    @classmethod
    def get_designations(cls):
        return {
            cls.FREE.value: "",
            cls.FREE_TABLE.value: "",
            cls.KITCHEN.value: "K",
            cls.CUSTOMER.value: "C",
            cls.WAITER.value: "W",
            cls.MANAGER.value: "M"
        }
