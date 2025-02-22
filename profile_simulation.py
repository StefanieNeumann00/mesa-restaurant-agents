import os
import cProfile
import pstats
from agent_system.src.mesa_restaurant_agents.model.restaurant_model import RestaurantModel

def run_profiler():
    # Create model instance
    model = RestaurantModel(
        n_waiters=2,
        grid_width=10,
        grid_height=10
    )

    # Set up profiler
    profiler = cProfile.Profile()
    profiler.enable()

    # Run simulation
    for i in range(15):
        print(f"Step {i}")
        model.step()

    profiler.disable()

    # Save with absolute path
    current_dir = os.getcwd()
    profile_path = os.path.join(current_dir, 'profile_results.prof')

    # Create and save stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('time')
    stats.dump_stats(profile_path)
    stats.print_stats(10)

    print(f"\nProfile saved to: {profile_path}")

if __name__ == '__main__':
    run_profiler()