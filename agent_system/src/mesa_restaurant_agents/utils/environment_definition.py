from enum import Enum

# Enum to track the status of customer orders
class EnvironmentDefinition(Enum):
    FREE = 0
    WAITER = 1
    FREE_TABLE = 2
    CUSTOMER = 3
    MANAGER = 4
    KITCHEN = 5

    @classmethod
    def get_designations(cls):
        return {
            cls.FREE.value: "",
            cls.FREE_TABLE.value: "",
            cls.KITCHEN.value: "",
            cls.CUSTOMER.value: "C",
            cls.WAITER.value: "W",
            cls.MANAGER.value: "M"
        }
