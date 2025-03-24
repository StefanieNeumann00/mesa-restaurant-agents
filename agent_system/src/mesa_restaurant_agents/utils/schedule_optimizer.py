import numpy as np
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import pyoptinterface as poi
from pyoptinterface import highs
from ..utils.waiter_definfitions import WaiterDefinition


class ScheduleOptimizer:
    def __init__(self, rf_model=None):
        # Initialize the random forest model
        best_params = {'max_depth': None, 'min_samples_leaf': 1, 'min_samples_split': 2, 'n_estimators': 50}
        self.rf_model = RandomForestRegressor(random_state=42, **best_params)
        # Initialize the optimization model
        self.opt_model = highs.Model()
        self.waiter_vars = {}

        # Initialize model attributes using WaiterDefinition class
        self.waiter_types = [t.value for t in WaiterDefinition.Type]
        self.shifts = WaiterDefinition.SHIFTS
        self.capacity_waiter = WaiterDefinition.CAPACITY_WAITER
        self.waiter_name = WaiterDefinition.WAITER_NAMES
        self.waiter_total = WaiterDefinition.WAITER_TOTAL
        self.group_A = WaiterDefinition.GROUP_A
        self.group_B = WaiterDefinition.GROUP_B
        self.eligible_waiters_by_shift = WaiterDefinition.ELIGIBLE_WAITERS_BY_SHIFT

        # Direct access to waiter lists
        self.fulltime_waiters = WaiterDefinition.get_fulltime_waiters()
        self.parttime_waiters = WaiterDefinition.get_parttime_waiters()

        # Initialize waiter_vars as a class variable
        self.waiter_vars = {}
        for waiter_type in self.waiter_types:
            for waiter in self.waiter_name[waiter_type]:
                for shift in self.shifts:
                    var_name = f"{waiter}_{shift}"
                    self.waiter_vars[var_name] = self.opt_model.add_variable(lb=0, ub=1,
                                                                             domain=poi.VariableDomain.Integer,
                                                                             name=var_name)

        self.training_data = pd.DataFrame()
        self._initialize_training_data()
        self._train_model()

    def _initialize_training_data(self):
        """Initialize training data with default values"""
        # Create initial training data if none exists
        self.training_data = pd.DataFrame({
            'Group': [1, 1, 1],
            'Shift': [1, 2, 3],
            'Customers': [45, 70, 35]
        })

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

        # Default values in case prediction fails
        default_prediction = {1: 30, 2: 50, 3: 40}

        try:
            X_pred = pd.DataFrame({'Shift': shifts})
            predictions = self.rf_model.predict(X_pred)

            # Create prediction dictionary from model outputs
            predicted_demand = {shift: max(20, round(predictions[i - 1]))
                                for i, shift in enumerate(shifts)}

            return predicted_demand
        except Exception as e:
            print(f"Warning: Customer prediction failed with error: {e}")
            return default_prediction

    def update_training_data(self, df, actual_customer_counts):
        """Add actual customer data to training dataset and retrain model"""
        if len(actual_customer_counts) != 3:
            return

        rounded_counts = np.round(actual_customer_counts).astype(int)

        # Get last group number and increment
        last_group = self.training_data['Group'].max()
        if pd.isna(last_group):
            new_group = 1
        else:
            new_group = last_group + 1

        # Create new rows with actual data
        new_rows = []
        for i, customers in enumerate(rounded_counts):
            new_rows.append({
                'Group': new_group,
                'Shift': i + 1,
                'Customers': customers
            })

        # Update the class's training_data
        self.training_data = pd.concat([self.training_data, pd.DataFrame(new_rows)], ignore_index=True)
        return self.training_data

    def retrain_model(self, df):

        X = df[['Shift']]
        y = df['Customers']

        self.rf_model.fit(X, y)

        # Retrain the model with updated data
        self._train_model()

    def create_waiter_schedule(self, waiters, predicted_demand, relax_constraints=False):
        """Create optimal schedule using linear programming"""
        # Get availability information
        waiter_availability = {w.unique_id: w.is_available for w in waiters}
        waiter_vars = {}

        # Convert waiters to proper format for solver
        fulltime_waiters = [w.unique_id for w in waiters if hasattr(w, 'is_fulltime') and w.is_fulltime]
        parttime_waiters = [w.unique_id for w in waiters if hasattr(w, 'is_fulltime') and not w.is_fulltime]

        # Try solving with strict constraints first
        model = self.solve_scheduling_problem(waiter_vars, waiter_availability,
                                              predicted_demand, fulltime_waiters,
                                              parttime_waiters, relax_constraints=relax_constraints)

        # Extract schedule from model solution
        schedule = {shift: [] for shift in [1, 2, 3]}
        for var_name, var in waiter_vars.items():
            if model.get_value(var) > 0.5:
                waiter_id, shift = var_name.rsplit('_', 1)
                schedule[int(shift)].append(next(w for w in waiters if str(w.unique_id) == waiter_id))

        return schedule, {shift: len(waiters) for shift, waiters in schedule.items()}

    def process_actual_data(self, actual_customer_counts):
        # Update training data with actual counts
        self.update_training_data(self.training_data, actual_customer_counts)

        # Retrain the model with updated data
        self.retrain_model(self.training_data)

        # Return updated predictions for next day
        return self.predict_customer_demand()

    def solve_scheduling_problem(self, waiter_vars, waiter_availability,
                                 predicted_demand, fulltime_waiters,
                                 parttime_waiters, relax_constraints=False):
        """
        Solves the scheduling problem for assigning waiters to shifts based on various constraints.

        Parameters:
        waiter_vars (dict): Dictionary to store the decision variables for each waiter in each shift.
        waiter_availability (dict): Dictionary indicating the availability of each waiter.
        relax_constraints (bool): Flag to indicate whether to relax certain constraints for feasibility.
        customer_demands (dict): Dictionary indicating the number of customer demands

        Returns:
        model: The optimized model with the scheduling solution.

        Description:
        This function creates and solves an optimization model to assign waiters to shifts while satisfying
        several constraints. The constraints include:
        1. Each full-time waiter can work at most 2 shifts per day.
        2. Each part-time waiter can work at most 1 shift per day (or 2 if constraints are relaxed).
        3. The total capacity in each shift must meet or exceed customer demands.
        4. Each shift must have at least 2 waiters.
        5. Only specific waiters can work in each shift.
        6. People in Group A and Group B cannot work together in the same shift.
        7. Only available waiters can be assigned to shifts.

        The objective of the model is to minimize the total number of waiters assigned to shifts.

        The function returns the optimized model with the scheduling solution.
        """
        model = highs.Model()  # Create a new instance of the model

        # Define variables for each waiter in each shift
        for waiter in waiter_availability:
            for shift in self.shifts:
                var_name = f"{waiter}_{shift}"
                waiter_vars[var_name] = model.add_variable(
                    lb=0, ub=1, domain=poi.VariableDomain.Integer, name=var_name)

        # Constraint 1: Each full-time waiter can work at most 2 shifts per day
        for waiter in fulltime_waiters:
            model.add_linear_constraint(
                poi.quicksum(waiter_vars[f"{waiter}_{shift}"] for shift in self.shifts),
                poi.Leq,
                2,
                name=f"{waiter}_fulltime_max_two_shifts"
            )

        # Constraint 2: Each part-time waiter can work at most 1 shift per day
        for waiter in parttime_waiters:
            model.add_linear_constraint(
                poi.quicksum(waiter_vars[f"{waiter}_{shift}"] for shift in self.shifts),
                poi.Leq,
                1 if not relax_constraints else 2,  # Relax constraint if needed
                name=f"{waiter}_parttime_max_one_shift"
            )

        # Constraint 3: The total capacity in each shift must meet or exceed customer demands
        for shift in self.shifts:
            model.add_linear_constraint(
                poi.quicksum(waiter_vars[f"{waiter}_{shift}"] * self.capacity_waiter for waiter in
                             fulltime_waiters + parttime_waiters),
                poi.Geq,
                predicted_demand[shift],
                name=f"shift_{shift}_demand"
            )

        # Constraint 4: Each shift must have at least 2 waiters
        for shift in self.shifts:
            model.add_linear_constraint(
                poi.quicksum(
                    waiter_vars[f"{waiter}_{shift}"] for waiter in fulltime_waiters + parttime_waiters),
                poi.Geq,
                2,
                name=f"shift_{shift}_min_two_waiters"
            )

        # Constraint 5: Only specific waiters can work in each shift
        if not relax_constraints:  # Relax Constraint 2, less critical prioritization
            for shift in self.shifts:
                for waiter in fulltime_waiters + parttime_waiters:
                    if waiter not in self.eligible_waiters_by_shift[shift]:
                        model.add_linear_constraint(
                            waiter_vars[f"{waiter}_{shift}"],
                            poi.Eq,
                            0,
                            name=f"{waiter}_not_in_shift_{shift}"
                        )

        # Constraint 6: People in Group A and Group B cannot work together in the same shift
        if not relax_constraints:  # Relax Constraint 2, less critical prioritization
            for shift in self.shifts:
                for waiter_A in self.group_A:
                    for waiter_B in self.group_B:
                        model.add_linear_constraint(
                            waiter_vars[f"{waiter_A}_{shift}"] + waiter_vars[f"{waiter_B}_{shift}"],
                            poi.Leq,
                            1,
                            name=f"group_A_B_not_together_shift_{shift}"
                        )

        # Constraint 7: Only available waiters can be assigned to shifts
        if not relax_constraints:
            for waiter in fulltime_waiters + parttime_waiters:
                if not waiter_availability[waiter]:
                    for shift in self.shifts:
                        model.add_linear_constraint(
                            waiter_vars[f"{waiter}_{shift}"],
                            poi.Eq,
                            0,
                            name=f"{waiter}_not_available"
                        )

        # Objective: Minimize the total number of waiters assigned
        model.set_objective(
            poi.quicksum(waiter_vars[var] for var in waiter_vars),
            poi.ObjectiveSense.Minimize
        )

        model.set_model_attribute(poi.ModelAttribute.Silent, False)
        model.optimize()

        return model
