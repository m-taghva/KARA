import sys
import os
import json
import re

# Read IP and port from the "ip_port_list.txt" file
try:
    with open("ip_port_list.txt", 'r') as ip_port_file:
        ip_port = ip_port_file.readline().strip()
except FileNotFoundError:
    print("File 'ip_port_list.txt' not found.")
    ip_port = "localhost:8086"  # Default value

# Construct the InfluxDB URL
url = f"http://{ip_port}/query"
db_name = "opentsdb"

# Read host names from the "host_names.txt" file
try:
    with open("host_names.txt", 'r') as host_file:
        host_names = [host.strip() for host in host_file.readlines()]
except FileNotFoundError:
    print("File 'host_names.txt' not found.")
    host_names = []

# Process command-line arguments
if len(sys.argv) < 2:
    print("Usage: python my-script.py input1 input2 ...")
    sys.exit(1)

inputs = sys.argv[1].split(',')
processed_files = []  # Store processed file names

all_inputs = []  # Store all input items

for input_item in inputs:
    input_item = input_item.strip()

    if os.path.isfile(input_item) and 'metric' in input_item:
        with open(input_item, 'r') as file:
            has_w_pattern = False

            for line in file:
                measurement = line.strip()
                if re.search(r'\\w\*', measurement):
                    has_w_pattern = True
                    break

            if has_w_pattern:
                # Process metric file
                print("========================================")
                print(f"Processing metric file: {input_item}")
                unique_measurement_names = set()
                with open(input_item, 'r') as metric_file:
                    lines = metric_file.readlines()
                    new_lines = []
                    for line in lines:
                        measurement = line.strip()
                        if re.search(r'\\w\*', measurement):
                            for host in host_names:
                                query = f'SELECT max("value") FROM /"{measurement}/" WHERE ("host" =~ /^{host}$/) AND time >= now() - 10s AND time <= now() GROUP BY time(10s) fill(none)'
                                curl_command = f'curl -sG --data-urlencode "db={db_name}" --data-urlencode "q={query}" {url}'
                                try:
                                    output = os.popen(curl_command).read()
                                    response_data = json.loads(output)
                                    for result in response_data["results"]:
                                        for series in result.get("series", []):
                                            for entry in series.get("values", []):
                                                name = series.get("name", "")
                                                if name:
                                                    unique_measurement_names.add(name)
                                except Exception as e:
                                    print(f"Error executing curl command: {e}")
                        else:
                            new_lines.append(line.strip())
                    new_lines.extend(unique_measurement_names)
                    with open(input_item, 'w') as metric_file:
                        metric_file.write("\n".join(filter(None, new_lines)))
                processed_files.append(input_item)
            else:
                print("========================================")
                print(f"Skipping metric file: {input_item} (no processing)")
    elif 'time' in input_item:
        # Skip time files
        print("========================================")
        print(f"Skipping time file: {input_item}")
    else:
        # Skip paths or directory names
        print("========================================")
        print(f"Skipping path/directory: {input_item}")

    all_inputs.append(input_item)

# Print processed input items
print("========================================")
print("Processed input items:",",".join(processed_files))
print("========================================")

# Remove duplicate lines from processed files
for file_name in processed_files:
    seen_lines = set()
    updated_lines = []
    with open(file_name, 'r') as infile:
        for line in infile:
            stripped_line = line.strip()
            if stripped_line not in seen_lines:
                seen_lines.add(stripped_line)
                updated_lines.append(stripped_line)

    with open(file_name, 'w') as outfile:
        outfile.writelines(line + '\n' for line in updated_lines)

# Call the other bash script with all the input as arguments
other_script_command = f'./status-reporter.sh {",".join(all_inputs)}'
os.system(other_script_command)
