from enum import Enum
from datetime import datetime, timedelta

class ShiftType(Enum):
    FULL = 8    # 8-hour shift
    HALF = 4    # 4-hour shift

class Shift:
    """Represents a work shift for waiters"""
    def __init__(self, start_time, shift_type):
        self.start_time = start_time
        self.duration = shift_type.value      # Hours
        self.end_time = start_time + timedelta(hours=self.duration)
        self.hourly_wage = 25                 # Euros per hour
        self.total_wage = self.duration * self.hourly_wage

    def is_active(self, current_time):
        """Check if shift is currently active"""
        return self.start_time <= current_time < self.end_time
