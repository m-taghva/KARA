import argparse
import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_and_save_graph(csv_file, x_column, y_column):
    # Read CSV file into a DataFrame
    data = pd.read_csv(csv_file)
    # Extract x and y values from DataFrame
    x_values = data[x_column]
    y_values = data[y_column]
    # Plot the data
    plt.plot(x_values, y_values, marker='o')
    # Set plot labels and title
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    file_name = os.path.basename(csv_file)
    time_of_graph = file_name.replace('.csv','')
    title = f'Time of Report: {time_of_graph}'
    plt.title(title)
    # Save the plot as an image in the same directory as the CSV file
    image_file_path = csv_file.replace('.csv', '_graph.png')
    plt.savefig(image_file_path)

def main():
    parser = argparse.ArgumentParser(description='Create a graph from a CSV file.')
    parser.add_argument('-c', '--csv', type=str, help='Path to the CSV file', required=True)
    parser.add_argument('-x', '--x_column', type=str, help='Name of the X column', required=True)
    parser.add_argument('-y', '--y_column', type=str, help='Name of the Y column', required=True)
    args = parser.parse_args()

    plot_and_save_graph(args.csv, args.x_column, args.y_column)

if __name__ == '__main__':
    main()
