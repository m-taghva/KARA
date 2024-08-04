import json
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
from alive_progress import alive_bar

# variable dirs
result_dir = "query_results"

# Convert UTC times to Tehran time
def convert_to_tehran_time(utc_time):
    utc_time = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = pytz.timezone('UTC').localize(utc_time)
    tehran_time = utc_time.astimezone(pytz.timezone('Asia/Tehran'))
    return tehran_time

def image_maker(query_output, server_name, parent_dir):
    data = json.loads(query_output)
    # Create a directory for the server's images if it doesn't exist
    server_dir = os.path.join(parent_dir, result_dir, f"{server_name}-images")
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    with alive_bar(title=f"Generating Image for {server_name}") as bar:
        # Extract data and create graphs for each time range
        for entry in data["results"]:
            for series in entry["series"]:
                metric_name = series["name"]
                value_column = series["columns"][1]  
                values = series["values"]
                # Extract time and value data
                tehran_timestamp = [convert_to_tehran_time(value[0]) for value in values]
                values = [value[1] for value in values]
                # Calculate min, max, and average values
                min_value = min(values)
                max_value = max(values)
                avg_value = sum(values) / len(values)
                # Get corresponding times for min, max, and average
                min_time = tehran_timestamp[values.index(min_value)]
                max_time = tehran_timestamp[values.index(max_value)]
                avg_time = tehran_timestamp[len(values) // 2]  # Approximation for average value
                plt.figure(figsize=(10, 6))
                plt.plot(tehran_timestamp, values, linestyle='-', linewidth=1, color='black', label='Values')
                # Highlight min, max, and avg with different colors
                plt.plot(min_time, min_value, 'ro', label=f'Min: {min_value}')
                plt.plot(max_time, max_value, 'go', label=f'Max: {max_value}')
                plt.plot(avg_time, avg_value, 'bo', label=f'Avg: {avg_value:.2f}')
                plt.ylabel("Value")
                plt.title(f"{metric_name} ({value_column}) - Server: {server_name}")
                plt.xticks(rotation=0)
                plt.legend()
                time_range_start = tehran_timestamp[0]
                time_range_end = tehran_timestamp[-1]
                total_duration = time_range_end - time_range_start
                # Determine an appropriate time interval based on the total duration
                if total_duration <= timedelta(minutes=15):
                    time_interval = timedelta(minutes=1)
                elif total_duration <= timedelta(minutes=30):
                    time_interval = timedelta(minutes=5)
                elif total_duration <= timedelta(hours=1):
                    time_interval = timedelta(minutes=10)
                elif total_duration <= timedelta(hours=2):
                    time_interval = timedelta(minutes=20)
                elif total_duration <= timedelta(hours=3):
                    time_interval = timedelta(minutes=30)
                else:
                    time_interval = timedelta(hours=1)

                x_ticks = []
                x_labels = []
                current_time = time_range_start
                last_label_date = current_time.date()
                date_changed = False  # Flag to indicate if the date changes
                while current_time < time_range_end:
                    x_ticks.append(current_time)
                    # Check if the date changes
                    if current_time.date() != last_label_date:
                        x_labels.append(current_time.strftime("%H:%M:%S\n%m-%d\n"))
                        last_label_date = current_time.date()
                        date_changed = True
                    else:
                        x_labels.append(current_time.strftime("%H:%M:%S\n"))
                    current_time += time_interval 

                # Set the xlabel based on the range of dates covered
                if date_changed:
                    plt.xlabel(f'Time_range ({time_range_start.strftime("%Y-%m-%d_%H:%M:%S")})  to  ({time_range_end.strftime("%Y-%m-%d_%H:%M:%S")})')
                else:
                    plt.xlabel(f'Time_range ({time_range_start.strftime("%Y-%m-%d_%H:%M:%S")}  to  {time_range_end.strftime("%Y-%m-%d_%H:%M:%S")})')
                plt.xticks(x_ticks, x_labels)
                plt.grid(True)
                plt.tight_layout()
                output_filename = f"{server_name}-{metric_name.replace('.', '-')}-{value_column}_{time_range_start.strftime('%Y-%m-%d-%H-%M-%S')}-{time_range_end.strftime('%Y-%m-%d-%H-%M-%S')}.png"
                output_filepath = os.path.join(server_dir, output_filename)
                plt.savefig(output_filepath, dpi=80)
                plt.close()
                print(f"\033[1;33m{output_filename}\033[0m saved")
                bar()
