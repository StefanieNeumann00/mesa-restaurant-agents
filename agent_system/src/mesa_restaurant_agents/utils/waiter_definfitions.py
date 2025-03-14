from enum import Enum
from typing import Dict, List, Set

class WaiterDefinition:
    # Shifts definitions
    SHIFTS = [1, 2, 3]

    # Waiter capacity
    CAPACITY_WAITER = 20

    # Waiter type definitions
    class Type(Enum):
        FULLTIME = "Fulltime"
        PARTTIME = "Parttime"

    # Waiter names by type
    WAITER_NAMES: Dict[str, List[str]] = {
        Type.FULLTIME.value: ["Ana", "Bob", "Alice", "Putri", "Lala"],
        Type.PARTTIME.value: ["Laura", "Bill", "Feni", "Steffi", "Johannes"]
    }

    # Waiter totals by type
    WAITER_TOTAL: Dict[str, int] = {
        Type.FULLTIME.value: 5,
        Type.PARTTIME.value: 5
    }

    # Define groups for constraint
    GROUP_A = ["Ana", "Bob", "Alice"]
    GROUP_B = ["Putri", "Lala", "Laura"]

    # Waiters per shift preferences
    ELIGIBLE_WAITERS_BY_SHIFT: Dict[int, List[str]] = {
        1: ["Ana", "Bob", "Putri", "Lala", "Laura", "Bill", "Johannes", "Steffi"],
        2: ["Ana", "Bob", "Alice", "Putri", "Lala", "Johannes", "Steffi", "Feni"],
        3: ["Ana", "Bob", "Alice", "Putri", "Lala", "Steffi", "Feni"]
    }

    # Minimum waiters per shift
    MIN_WAITERS_PER_SHIFT = 2

    @classmethod
    def get_fulltime_waiters(cls) -> List[str]:
        return cls.WAITER_NAMES[cls.Type.FULLTIME.value]

    @classmethod
    def get_parttime_waiters(cls) -> List[str]:
        return cls.WAITER_NAMES[cls.Type.PARTTIME.value]

    @classmethod
    def get_all_waiters(cls) -> List[str]:
        return cls.get_fulltime_waiters() + cls.get_parttime_waiters()