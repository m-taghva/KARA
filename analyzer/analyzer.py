import os
import re
import logging
import argparse
from glob import glob
import pandas as pd
import matplotlib.pyplot as plt

BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

####### MERGER #######
def merge_csv(selected_csv, io_directory, extracted_data, all_csv):
    logging.info("Executing status_analyzer merge_csv function")
    for file in selected_csv:
        try:
            csv_data = pd.read_csv(file)
            # add csv name as a column 
            csv_data.insert(0, 'File', os.path.basename(file).split('.')[0])
            if extracted_data:
                csv_data.insert(1, 'config', extracted_data)
            all_csv.append(csv_data)
        except FileNotFoundError:
            print(f"File '{file}' not found. Skipping...")
    if len(all_csv) > 0:
        merged_csv = pd.concat(all_csv, ignore_index=True)
        if not os.path.exists(io_directory):
            os.makedirs(io_directory)
        merged_csv.to_csv(f'{io_directory}/merged.csv', index=False)
        print(f"CSV files merged successfully. Merged file saved as {YELLOW}'{io_directory}/merged.csv'{RESET}")
    else:
        print(f"\033[91mNo CSV files found for merging\033[0m")

def extract_string_number_pairs(target_directory):
    logging.info("Executing status_analyzer extract_string_number_pairs function")
    keys = re.findall("(?<=#)[^:]*(?=:)", target_directory)
    values = re.findall("(?<=:)[^#]*(?=#)", target_directory)
    return list(zip(keys, values))

def csv_process(io_directory, selected_csv):
    logging.info("Executing status_analyzer csv_process function")
    if os.path.exists(f'{io_directory}/merged.csv'):
       os.remove(f'{io_directory}/merged.csv')
    all_csv = []
    if '*' in selected_csv:
        for subdirectory in sorted(os.listdir(io_directory)):
            subdirectory_path = os.path.join(io_directory, subdirectory)
            if os.path.isdir(subdirectory_path):
                pairs = extract_string_number_pairs(subdirectory_path)
                if pairs:
                    extracted_data = str(pairs)
                    csv_file_paths = glob(os.path.join(subdirectory_path, 'query_results', selected_csv))
                    if csv_file_paths:
                        merge_csv(csv_file_paths, io_directory, extracted_data, all_csv)
                    else:
                        print(f"\033[91mNo CSV files found in {subdirectory_path}\033[0m")
                        exit(1)
    else:
        merge_csv(selected_csv, io_directory, extracted_data=None, all_csv=all_csv)
    
####### ANALYZER #######
def read_txt_file(file_path):
    logging.info("Executing status_analyzer read_txt_file function")
    with open(file_path, 'r') as txt_file:
        operation, new_column_name = txt_file.readline().strip().split(':')
        selected_columns = txt_file.read().splitlines()
    return operation, new_column_name, selected_columns

def process_csv_file(csv_data, operation, new_column_name, selected_columns):
    logging.info("Executing status_analyzer process_csv_file function")
    if operation == 'sum':
        new_column_name = f"sum.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].sum(axis=1)
    elif operation == 'avg':
        new_column_name = f"avg.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].mean(axis=1)
    return csv_data

def analyze_and_save_csv(csv_original, transformation_directory):
    logging.info("Executing status_analyzer analyze_and_save_csv function")
    csv_intermediate = pd.read_csv(csv_original)
    selected_column_names = set()
    for txt_file in os.listdir(transformation_directory):
        if txt_file.startswith('t') and txt_file.endswith('.txt'):
            txt_file_path = os.path.join(transformation_directory, txt_file)
            operation, new_column_name, selected_columns = read_txt_file(txt_file_path)
            csv_intermediate = process_csv_file(csv_intermediate, operation, new_column_name, selected_columns)
            selected_column_names.update(selected_columns)
    keep_columns = [col for col in csv_intermediate.columns if col not in selected_column_names]
    csv_final = csv_intermediate[keep_columns]
    final_output_csv_name = f"{os.path.splitext(os.path.basename(csv_original))[0]}-{os.path.basename(transformation_directory)}.csv"
    final_output_csv_path = os.path.join(os.path.dirname(csv_original), final_output_csv_name)
    csv_final.to_csv(final_output_csv_path, index=False)
    print(f"\n{BOLD}Analyzed CSV file:{RESET}{YELLOW} '{final_output_csv_path}' {RESET}{BOLD}has been created with the extracted values.{RESET}\n")
    intermediate_csv_path = os.path.join(os.path.dirname(csv_original), "intermediate.csv")
    if os.path.exists(intermediate_csv_path):
        os.remove(intermediate_csv_path)

###### Make graph and image ######
def plot_and_save_graph(selected_csv, x_column, y_column):
    logging.info("Executing status_analyzer plot_and_save_graph function")
    # Read CSV file into a DataFrame
    data = pd.read_csv(selected_csv)
    # Extract x and y values from DataFrame
    x_values = data[x_column]
    y_values = data[y_column]
    # Plot the data
    plt.plot(x_values, y_values, marker='o')
    # Set plot labels and title
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    file_name = os.path.basename(selected_csv)
    time_of_graph = file_name.replace('.csv','')
    title = f'Time of Report: {time_of_graph}'
    plt.title(title)
    # Save the plot as an image in the same directory as the CSV file
    image_file_path = selected_csv.replace('.csv', '_graph.png')
    plt.savefig(image_file_path)

def main(merge, analyze, graph, csv_original, transformation_directory, io_directory, selected_csv, x_column, y_column):
    os.makedirs('/var/log/kara/', exist_ok=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("\033[92m****** status_analyzer main function start ******\033[0m")
    if analyze:
        analyze_and_save_csv(csv_original, transformation_directory)
    if merge:
        csv_process(io_directory, selected_csv)
    if graph:
        plot_and_save_graph(selected_csv, x_column, y_column)
    logging.info("\033[92m****** status_analyzer main function end ******\033[0m")
           
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform CSV operations and merge files.')
    parser.add_argument('-M', '--merge', action='store_true', help='Merge CSV files')
    parser.add_argument('-io', '--io_directory', help='Path to the directory containing CSV files or output for merged csv file (required for -M)')
    parser.add_argument('-sc', '--selected_csv', help='Name of the selected CSV files or "*.csv" (required for -M)')
    parser.add_argument('-A', '--analyze', action='store_true', help='Analyze CSV files')
    parser.add_argument('-c', '--csv_org', help='Custom CSV file for analysis (required for -A)')
    parser.add_argument('-t', '--transformation_directory', help='Path to transformation directory (required for -A)')
    parser.add_argument('-G', '--graph', action='store_true', help='make graph of CSV file')
    parser.add_argument('-x', '--x_column', type=str, help='Name of the X column (required for -G)')
    parser.add_argument('-y', '--y_column', type=str, help='Name of the Y column (required for -G)')
    args = parser.parse_args()
    
    # Check required arguments based on operation
    if args.merge and (args.io_directory is None or args.selected_csv is None):
        print("Error: Both -io (--input_directory) and -sc (--selected_csv) switches are required for merge operation -M")
        exit(1)
    if args.analyze and (args.csv_org is None or args.transformation_directory is None):
        print("Error: Both -c (--csv_org) and -t (--transformation_directory) switches are required for analyze operation -A")
        exit(1)
    if args.graph and (args.x_column is None or args.y_column is None):
        print("Error: Both -x (--x_column) and -y (--y_column) switches are required for make graph operation -G")
        exit(1)

    # Set values to None if not provided
    merge = args.merge ; analyze = args.analyze ; graph = args.graph
    x_column = args.x_column ; y_column = args.y_column
    io_directory = args.io_directory.strip() if args.io_directory else None 
    if '*' in args.selected_csv:
        selected_csv = args.selected_csv.strip() if args.selected_csv else None
    else:
        selected_csv = args.selected_csv.split(',')
    csv_original = args.csv_org.strip() if args.csv_org else None
    transformation_directory = args.transformation_directory.strip() if args.transformation_directory else None

    main(merge, analyze, graph, csv_original, transformation_directory, io_directory, selected_csv, x_column, y_column)
