from enum import Enum
from typing import Dict, List


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
        Type.FULLTIME.value: ["Ana", "Bob", "Alice", "Putri", "Lala", "Peter", "Karl", "Stefan", "Max",
                              "Michael", "Sarah", "David", "Emma", "Daniel", "Olivia", "James", "Sophia"
                              ],
        Type.PARTTIME.value: ["Laura", "Bill", "Feni", "Steffi", "Johannes",
                              "Alex", "Nina", "Tomas", "Maria", "Chris", "Ava", "Leo", "Hannah"
                              ]
    }

    # Define groups for constraint
    GROUP_A = ["Ana", "Bob", "Alice", "Michael", "Sarah", "David"]
    GROUP_B = ["Putri", "Lala", "Laura", "Emma", "Alex", "Nina"]

    # Waiters per shift preferences
    ELIGIBLE_WAITERS_BY_SHIFT: Dict[int, List[str]] = {
        1: ["Ana", "Bob", "Putri", "Lala", "Laura", "Bill", "Johannes", "Steffi", "Peter", "Max",
            "Michael", "Sarah", "Emma", "Alex", "Nina", "Tomas", "Chris", "Leo"],
        2: ["Ana", "Bob", "Alice", "Putri", "Lala", "Johannes", "Steffi", "Feni", "Karl", "Max",
            "David", "Olivia", "James", "Maria", "Chris", "Ava", "Hannah", "Daniel"],
        3: ["Ana", "Bob", "Alice", "Putri", "Lala", "Steffi", "Feni", "Karl",
            "Michael", "Sarah", "David", "Emma", "Daniel", "Sophia", "Maria", "Ava", "Leo"]
    }

    # Minimum waiters per shift
    # MIN_WAITERS_PER_SHIFT = 2

    @classmethod
    def get_fulltime_waiters(cls) -> List[str]:
        return cls.WAITER_NAMES[cls.Type.FULLTIME.value]

    @classmethod
    def get_parttime_waiters(cls) -> List[str]:
        return cls.WAITER_NAMES[cls.Type.PARTTIME.value]

