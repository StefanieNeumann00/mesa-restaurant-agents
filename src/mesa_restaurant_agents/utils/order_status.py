from enum import Enum

# Enum to track the status of customer orders
class OrderStatus(Enum):
    WAITING = 0    # Customer hasn't ordered yet
    ORDERED = 1    # Order has been placed
    PREPARING = 2  # Food is being prepared
    SERVED = 3     # Food has been delivered

# Available food options in the restaurant
food_options = ["vegetarian", "meat", "gluten free"]