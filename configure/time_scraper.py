import os
import argparse

# Create an argument parser
argParser = argparse.ArgumentParser()
argParser.add_argument("-p", "--path", help="path to test dirs")
args = argParser.parse_args()
path = args.path

# Check if the path is provided
if not path:
    print("\033[91mPlease provide a path using the -p or --path argument.\033[0m")
else:
    # Check if the provided path exists
    if os.path.exists(path):
        # Define the path for the output file
        times_file_path = os.path.join(path, "time.txt")

        # Function to scrape time information
        def time_scraper(path):
            time_lines = []
            for dirpath, dirnames, filenames in os.walk(path):
                for dirname in dirnames:
                    time_file_path = os.path.join(dirpath, dirname, "time")
                    if os.path.exists(time_file_path):
                        with open(time_file_path, "r") as input_file:
                            lines = input_file.readlines()
                            for line in lines:
                                time_lines.append(line.strip())

            # Sort the time lines by timestamp
            time_lines.sort(key=lambda line: line.split(",")[0])

            # Write the sorted lines to the output file
            with open(times_file_path, "w") as output_file:
                for line in time_lines:
                    output_file.write(line + "\n")

        # Call the function to scrape and save time information
        time_scraper(path)
        print(f"\033[92mTime information scraped, sorted, and saved to {times_file_path}.\033[0m")
    else:
        print("\033[91mThe provided path does not exist.\033[0m")
