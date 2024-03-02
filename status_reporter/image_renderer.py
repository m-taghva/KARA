import sys
import json
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import shutil
from tqdm import tqdm

class bcolors:
    YELLOW = '\033[1;33m'
    END = '\033[0m'
print (f"{bcolors.YELLOW}Query send ! wait for generate new image{bcolors.END}")

# Read InfluxDB query result, server name, and parent directory from command-line arguments
query_output = sys.argv[1]
server_name = sys.argv[2]
parent_dir = sys.argv[3]  # The user-specified parent directory

# Process the JSON data from the InfluxDB query
data = json.loads(query_output)

# Define UTC and Tehran time zones
utc = pytz.timezone('UTC')
tehran = pytz.timezone('Asia/Tehran')

# Convert UTC times to Tehran time
def convert_to_tehran_time(utc_time):
    utc_time = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc.localize(utc_time)
    tehran_time = utc_time.astimezone(tehran)
    return tehran_time

# Create a directory for the server's images if it doesn't exist
server_dir = os.path.join(parent_dir, "query_results", f"{server_name}-images")
if not os.path.exists(server_dir):
    os.makedirs(server_dir)

# Calculate the total number of time series
try:
    total_series = sum(len(entry["series"]) for entry in data["results"])
except (KeyError, TypeError):
    # Handle the exception silently (no print or logging)
    pass

# Initialize the tqdm progress bar
pbar = tqdm(total=total_series, desc="Generating Image")

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

        output_filename = f"{server_name}_{metric_name.replace('.', '_')}_{value_column}_{time_range_start.strftime('%Y%m%d_%H%M%S')}_{time_range_end.strftime('%Y%m%d_%H%M%S')}_graph.png"
        output_filepath = os.path.join(server_dir, output_filename)
        
        # Update the progress bar description to show the image name
        pbar.set_description(f"Generating {output_filename}")
        
        plt.savefig(output_filepath, dpi=300)
        plt.close()
   
        # Update the progress bar
        pbar.update(1)

pbar.close()
