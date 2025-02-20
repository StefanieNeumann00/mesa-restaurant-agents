class Table:
    """Represents a restaurant table with fixed capacity and customer tracking"""
    def __init__(self, table_id):
        self.table_id = table_id
        self.seats = 4                # Fixed number of seats per table
        self.occupied_seats = 0       # Current number of occupied seats
        self.customers = []           # List of customers at this table

    def is_available(self):
        """Check if table has any available seats"""
        return self.occupied_seats < self.seats

    def add_customer(self, customer):
        """
        Attempt to seat a customer at this table
        Returns True if successful, False if table is full
        """
        if self.is_available():
            self.customers.append(customer)
            self.occupied_seats += 1
            customer.table = self
            return True
        return False

    def remove_customer(self, customer):
        """Remove customer from table when they leave"""
        if customer in self.customers:
            self.customers.remove(customer)
            self.occupied_seats -= 1
            customer.table = None