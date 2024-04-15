import os
import re
import csv
import argparse
from glob import glob
import pandas as pd

BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

####### MERGER #######
def extract_string_number_pairs(target_directory):
    keys = re.findall("(?<=#)[^:]*(?=:)", target_directory)
    values = re.findall("(?<=:)[^#]*(?=#)", target_directory)
    return list(zip(keys, values))

def read_csv_data(csv_file_path):
    with open(csv_file_path, mode='r') as input_csv:
        csv_reader = csv.reader(input_csv)
        headers = next(csv_reader)
        input_data = list(csv_reader)
    return headers, input_data

def merge_csv_files(input_directory, output_csv_writer, selected_csv):
    headers_written = False
    for subdirectory in os.listdir(input_directory):
        subdirectory_path = os.path.join(input_directory, subdirectory)
        if os.path.isdir(subdirectory_path):
            pairs = extract_string_number_pairs(subdirectory_path)
            if pairs:
                extracted_data = dict(pairs)
                csv_file_paths = glob(os.path.join(subdirectory_path, 'query_results', selected_csv))
                if not csv_file_paths:
                    print(f"No CSV files found in {subdirectory_path}")
                    continue
                for i, csv_file_path in enumerate(csv_file_paths):
                    if not headers_written:
                        headers, _ = read_csv_data(csv_file_path)
                        headers = ["Time Ranges"] + list(extracted_data.keys()) + headers
                        output_csv_writer.writerow(headers)
                        headers_written = True
                    _, input_data = read_csv_data(csv_file_path)
                    csv_name_without_extension = os.path.splitext(os.path.basename(csv_file_path))[0]
                    extracted_numbers = list(extracted_data.values())
                    output_csv_writer.writerows([csv_name_without_extension] + extracted_numbers + row for row in input_data)

def create_merged_csv(input_directory, selected_csv):
    selected_csv_name = os.path.splitext(selected_csv)[0]
    output_csv_path = os.path.join(input_directory, f"{selected_csv_name}-merge.csv")
    if os.path.exists(output_csv_path):
        os.remove(output_csv_path)
    with open(output_csv_path, mode='a', newline='') as output_csv:
        csv_writer = csv.writer(output_csv)
        merge_csv_files(input_directory, csv_writer, selected_csv)
    print(f"\n{BOLD}Merged CSV file:{RESET}{YELLOW} '{output_csv_path}' {RESET}{BOLD}has been created with the extracted values.{RESET}\n")
    return output_csv_path
    
####### ANALYZER #######
def read_txt_file(file_path):
    with open(file_path, 'r') as txt_file:
        operation, new_column_name = txt_file.readline().strip().split(':')
        selected_columns = txt_file.read().splitlines()
    return operation, new_column_name, selected_columns

def process_csv_file(csv_data, operation, new_column_name, selected_columns):
    if operation == 'sum':
        new_column_name = f"sum.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].sum(axis=1)
    elif operation == 'avg':
        new_column_name = f"avg.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].mean(axis=1)
    return csv_data

def analyze_and_save_csv(csv_original, transformation_directory):
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

def main_analyze(csv_original, transformation_directory):
    analyze_and_save_csv(csv_original, transformation_directory)

def main_merge(input_directory, selected_csv):
    create_merged_csv(input_directory, selected_csv)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform CSV operations and merge files.')
    parser.add_argument('-i', '--input_directory', help='Path to the directory containing CSV files (required for -M)')
    parser.add_argument('-c', '--selected_csv', help='Name of the selected CSV file or "*.csv" (required for -M)')
    parser.add_argument('-M', '--merge', action='store_true', help='Merge CSV files')
    parser.add_argument('-A', '--analyze', action='store_true', help='Analyze CSV files')
    parser.add_argument('-ct', '--csv_org', help='Custom CSV file for analysis (required for -A)')
    parser.add_argument('-t', '--transformation_directory', help='Path to transformation directory (required for -A)')
    args = parser.parse_args()
    
    # Check required arguments based on operation
    if args.merge and (args.input_directory is None or args.selected_csv is None):
        print("Error: Both -i (--input_directory) and -c (--selected_csv) switches are required for merge operation.")
        exit(1)
    if args.analyze and (args.csv_org is None or args.transformation_directory is None):
        print("Error: Both -ct (--csv_org) and -t (--transformation_directory) switches are required for analyze operation.")
        exit(1)

    # Set values to None if not provided
    input_directory = args.input_directory.strip() if args.input_directory else None
    selected_csv = args.selected_csv.strip() if args.selected_csv else None
    csv_original = args.csv_org.strip() if args.csv_org else None
    transformation_directory = args.transformation_directory.strip() if args.transformation_directory else None

    if input_directory and not os.path.isdir(input_directory):
        print(f"Error: Directory not found - {input_directory}")
        exit(1)

    if args.analyze:
       main_analyze(csv_original=csv_original, transformation_directory=transformation_directory)
    if args.merge:
       main_merge(input_directory=input_directory, selected_csv=selected_csv)
