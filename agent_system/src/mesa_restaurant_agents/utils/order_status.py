from enum import Enum

# Define food options with their prices
food_options = {
    "vegetarian": {"price": 20, "cost": 10},  # Cost is 50% of price
    "meat": {"price": 30, "cost": 15},
    "gluten_free": {"price": 25, "cost": 12.5}
}

# Enum to track the status of customer orders
class OrderStatus(Enum):
    # WAITING = 0    # Customer hasn't ordered yet
    ORDERED = 1    # Order has been placed
    DELIVERING = 2  # Food is being delivered
    SERVED = 3     # Food has been delivered
