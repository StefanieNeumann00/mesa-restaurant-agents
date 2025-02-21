from enum import Enum

# Enum to track the status of customer orders
class EnvironmentDefinition(Enum):
    FREE = 0
    OCCUPIED = 1
    FREE_TABLE = 2
    OCCUPIED_TABLE = 3
    KITCHEN = 4
