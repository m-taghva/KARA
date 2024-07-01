import sys
import json
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
from alive_progress import alive_bar

YELLOW = '\033[1;33m'
END = '\033[0m'

# Read InfluxDB query result, server name, and parent directory from command-line arguments
query_output = sys.argv[1]
server_name = sys.argv[2]
parent_dir = sys.argv[3] 
data = json.loads(query_output)

# Convert UTC times to Tehran time
def convert_to_tehran_time(utc_time):
    utc_time = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = pytz.timezone('UTC').localize(utc_time)
    tehran_time = utc_time.astimezone(pytz.timezone('Asia/Tehran'))
    return tehran_time

# Create a directory for the server's images if it doesn't exist
server_dir = os.path.join(parent_dir, "query_results", f"{server_name}-images")
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
            times_utc = [convert_to_tehran_time(value[0]) for value in values]
            values = [value[1] for value in values]
            plt.figure(figsize=(10, 6))
            plt.plot(times_utc, values, marker='o', linestyle='-', linewidth=2)
            plt.xlabel("Time (Asia/Tehran)")
            plt.ylabel("Value")
            plt.title(f"{metric_name} ({value_column.capitalize()}) - Server: {server_name}")
            plt.xticks(rotation=90)
            # Show x-axis labels every 1 minute
            time_range_start = times_utc[0]
            time_range_end = times_utc[-1]
            time_interval = timedelta(minutes=1)
            x_ticks = []
            x_labels = []
            current_time = time_range_start
            while current_time < time_range_end:
                x_ticks.append(current_time)
                x_labels.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                current_time += time_interval 
            # Ensure the last time is included in the x-axis
            x_ticks.append(time_range_end)
            x_labels.append(time_range_end.strftime("%Y-%m-%d %H:%M:%S"))
            plt.xticks(x_ticks, x_labels)
            plt.grid(True)
            plt.tight_layout()
            output_filename = f"{server_name}-{metric_name.replace('.', '-')}-{value_column}_{time_range_start.strftime('%Y-%m-%d-%H-%M-%S')}-{time_range_end.strftime('%Y-%m-%d-%H-%M-%S')}.png"
            output_filepath = os.path.join(server_dir, output_filename)
            plt.savefig(output_filepath, dpi=300)
            plt.close()
            print(f"{YELLOW}{output_filename}{END}")
            bar()
