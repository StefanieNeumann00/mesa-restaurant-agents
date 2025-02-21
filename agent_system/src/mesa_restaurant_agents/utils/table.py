class Table:
    """Represents a restaurant table with fixed capacity and customer tracking"""
    def __init__(self, table_id):
        self.table_id = table_id
        self.occupied = False  # Track if the table is occupied
        self.customer = None  # The customer occupying the table

    def is_available(self):
        """Check if the table is available"""
        return not self.occupied

    def add_customer(self, customer):
        """
        Attempt to seat a customer at this table
        Returns True if successful, False if table is occupied
        """
        if self.is_available():
            self.customer = customer
            self.occupied = True
            customer.table = self
            return True
        return False

    def remove_customer(self, customer):
        """Remove customer from table when they leave"""
        if self.customer == customer:
            self.customer = None
            self.occupied = False
            customer.table = None