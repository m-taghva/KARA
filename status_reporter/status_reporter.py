import os
import json
import subprocess
import sys
from datetime import datetime
import argparse
import yaml

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

# Constants
START_TIME_SUM = 10  # increase your report start time
END_TIME_SUBTRACT = 10  # decrease your report end time
TIME_GROUP = 10  # time group for query 2
CONFIG_FILE = "/etc/KARA/status.conf"

def load_config(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    tehran_timestamp_seconds = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds = tehran_timestamp_seconds + add_seconds
    utc_timestamp = datetime.utcfromtimestamp(utc_timestamp_seconds).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp

# Function to extract metrics from files
def get_metrics_from_file(metric_file_path):
    metrics = []
    with open(metric_file_path, 'r') as f:
        metrics = [metric.strip() for metric in f if metric.strip() and not metric.strip().startswith('#')]
    return metrics
                            
def main(metric_file=None, path_dir=".", time_range=None, img=False):
    # Load configuration from config file
    data_loaded = load_config(CONFIG_FILE)

    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("") 

    # Create the output parent directory
    output_parent_dir= os.path.join(path_dir, "query_results")
    os.makedirs(output_parent_dir, exist_ok=True)

    # Split time_range and generate output_csv
    time_range_parts = time_range.split(',')
    start_time, end_time = time_range_parts[0], time_range_parts[1]
    start_time_csv = start_time.replace(" ", "-")
    end_time_csv = end_time.replace(" ", "-")
    output_csv = os.path.join(output_parent_dir, f"{start_time_csv}_{end_time_csv}.csv")
    
    if os.path.exists(output_csv):
        os.remove(output_csv)

    # Generate metric_operation_mapping
    metric_operation_mapping = {}
    metric_operations = []
    if metric_file:
        # Extract metric operations from file names in the command-line argument
        metric_files_command = metric_file
        metric_operations = [os.path.basename(metric_file).split('_')[0] for metric_file in metric_files_command]
        metric_operation_mapping = dict(zip(metric_files_command, metric_operations))
    else:
        # Read metric file paths and operations from the configuration file
        for metric_operation, metric_file in data_loaded.get('metrics', {}).items():
            metric_operations.append(metric_operation)
            metric_files_config = [metric_file.get('path', '')]
            metric_operation_mapping[metric_file.get('path', '')] = metric_operation

    output_csv_str = ["Host_alias"]  # name of the first column in csv
    csvi = 0
    # Loop through each combination of time range, host, IP, PORT, and execute the curl command
    for mc_server, config in data_loaded.get('influxdbs', {}).items():
        ip = config.get('ip')
        influx_port = config.get('influx_port')
        for db_name, db_data in config.get('databases', {}).items():
            hostls = db_data.get('hostls', {})
            for host_name, alias in hostls.items():
                alias = alias if alias and len(alias) > 1 else host_name
                start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
                end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
                output_csv_str.append(alias)  # value inside the first column of csv
                csvi += 1
                for metric_file, metric_operation in metric_operation_mapping.items():
                    if os.path.isfile(metric_file):
                        metrics = get_metrics_from_file(metric_file)
                        for metric_name in metrics:
                            metric_name = metric_name.strip()
                            if csvi == 1:
                                metric_name = metric_name.replace(" ", "")
                                output_csv_str[0] += f",{metric_operation}_{metric_name.replace('netdata.', '')}"
                            # Construct the curl command for query 1
                            query1_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                            query_result = subprocess.getoutput(query1_curl_command)
                            values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                            values = [str(v[1]) for v in values]
                            output_csv_str[csvi] += "," + ",".join(values)
                            print(f"{BOLD}Add metrics to CSV, please wait ...{RESET}")
                            # Construct the curl command for query 2
                            if img:
                                query2_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time({TIME_GROUP}s) fill(none)"'
                                query2_output = subprocess.getoutput(query2_curl_command)
                                os.system(f"python3 ./../status_reporter/image_renderer.py '{query2_output}' '{host_name}' '{path_dir}'")
    # Write the CSV file for each time range
    with open(output_csv, 'a') as csv_file:
        for line in output_csv_str:
            csv_file.write(line + "\n")        
                           
    print("")
    print(f"{BOLD}Done! Csv and Images are saved in the {RESET}{YELLOW}'{output_parent_dir}'{RESET}{BOLD} directory{RESET}")
    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("")

if __name__ == "__main__":
    # Parse command-line arguments for your new script
    parser = argparse.ArgumentParser(description="Your Script Description")
    parser.add_argument("-m", "--metric_file", help="Comma-separated list of metric file paths")
    parser.add_argument("-o", "--path_dir", help="Path to the parent directory")
    parser.add_argument("-t", "--time_range", help="Time range in the format 'start_time,end_time'")
    parser.add_argument("--img", action="store_true", help="Create images and graphs")
    args = parser.parse_args()
    metric_file = args.metric_file.split(',') if args.metric_file else [] 
    path_dir = args.path_dir if args.path_dir else "." 
    time_range = args.time_range if args.time_range else load_config(CONFIG_FILE).get('time', [])[0]
    img=args.img
    
    # Call your main function with the provided arguments
    main(metric_file, path_dir, time_range, img)
