# Create a new file: schedule_optimizer.py
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import os

class ScheduleOptimizer:
    def __init__(self, training_data_path="training_data_customers.csv"):
        self.training_data_path = training_data_path
        self.rf_model = RandomForestRegressor(random_state=42, n_estimators=50)
        self.training_data = pd.DataFrame()
        self._initialize_training_data()
        self._train_model()

    def _initialize_training_data(self):
        """Initialize or load customer training data"""
        if os.path.exists(self.training_data_path):
            self.training_data = pd.read_csv(self.training_data_path)
        else:
            # Create initial training data if none exists
            self.training_data = pd.DataFrame({
                'Group': [1, 1, 1],
                'Shift': [1, 2, 3],
                'Customers': [45, 70, 35]
            })
            self.training_data.to_csv(self.training_data_path, index=False)

    def _train_model(self):
        """Train the random forest model using available data"""
        if self.training_data.empty:
            return

        X = self.training_data[['Shift']]
        y = self.training_data['Customers']
        self.rf_model.fit(X, y)

    def predict_customer_demand(self):
        """Predict customer demand for each shift"""
        shifts = [1, 2, 3]
        customer_data = np.array([[1], [2], [3]])
        predictions = self.rf_model.predict(customer_data)
        return {shift: round(predictions[i-1], 0) for i, shift in enumerate(shifts, 1)}

    def update_training_data(self, actual_customer_counts):
        """Add actual customer data to training dataset and retrain model"""
        if len(actual_customer_counts) != 3:
            return

        # Get last group number and increment
        last_group = self.training_data['Group'].max() if not self.training_data.empty else 0
        new_group = last_group + 1

        # Create new rows with actual data
        new_rows = []
        for i, customers in enumerate(actual_customer_counts):
            new_rows.append({
                'Group': new_group,
                'Shift': i + 1,
                'Customers': round(customers)
            })

        # Add to training data and save
        self.training_data = pd.concat([self.training_data, pd.DataFrame(new_rows)],
                                      ignore_index=True)
        self.training_data.to_csv(self.training_data_path, index=False)

        # Retrain the model with updated data
        self._train_model()

    def create_waiter_schedule(self, waiters, predicted_demand):
        """Create a schedule based on predicted customer demand"""
        # Simple version - in a full implementation,
        # you'd include the linear programming code from the notebook
        waiters_available = [w for w in waiters if w.is_available]
        num_waiters = len(waiters_available)
        shifts = [1, 2, 3]

        # Simple allocation based on predicted demand
        total_demand = sum(predicted_demand.values())
        min_waiters_per_shift = 2

        schedule = {shift: [] for shift in shifts}

        for shift in shifts:
            shift_demand_ratio = predicted_demand[shift] / total_demand if total_demand > 0 else 1/3
            shift_waiters_count = max(min_waiters_per_shift,
                                     round(num_waiters * shift_demand_ratio))

            assigned = 0
            for waiter in waiters_available:
                if assigned >= shift_waiters_count:
                    break
                if shift not in waiter.assigned_shifts:
                    schedule[shift].append(waiter)
                    waiter.assigned_shifts.append(shift)
                    assigned += 1

        return schedule, {shift: len(waiters) for shift, waiters in schedule.items()}