import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import argparse
import os

def csv_to_image(csv_file, output_image):
    # Read CSV file into a DataFrame
    df = pd.read_csv(csv_file)
    # Convert DataFrame to an image
    image = create_image_from_dataframe(df)
    # Save the image with the same name as the CSV file
    image.save(output_image)

def create_image_from_dataframe(df):
    # Get the dimensions of the DataFrame
    num_rows, num_cols = df.shape
    # Set image properties
    cell_width = 150
    cell_height = 20
    font_size = 15
    # Create a blank image
    image_width = num_cols * cell_width
    image_height = (num_rows + 1) * cell_height  # +1 for header row
    image = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(image)
    # Use the default font that comes with Pillow
    font = ImageFont.load_default()
    # Draw the header row
    for col, column_name in enumerate(df.columns):
        draw.rectangle([col * cell_width, 0, (col + 1) * cell_width, cell_height], outline='black', fill='lightgray')
        draw.text((col * cell_width + 5, 5), str(column_name), font=font, fill='black')
    # Draw the data rows
    for row in range(num_rows):
        for col, value in enumerate(df.iloc[row]):
            draw.rectangle([col * cell_width, (row + 1) * cell_height, (col + 1) * cell_width, (row + 2) * cell_height],outline='black', fill='white')
            draw.text((col * cell_width + 5, (row + 1) * cell_height + 5), str(value), font=font, fill='black')
    return image

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Convert CSV file to image')
    parser.add_argument('-c', '--csv', help='Input CSV file', required=True)
    args = parser.parse_args()
    # Check if the CSV file exists
    if not os.path.exists(args.csv):
        print(f"Error: The specified CSV file '{args.csv}' does not exist.")
        return
    # Create the output image file name based on the CSV file name
    output_image = os.path.splitext(args.csv)[0] + '.png'
    # Call the function to convert CSV to image
    csv_to_image(args.csv, output_image)
    print(f"Image '{output_image}' created successfully.")

if __name__ == "__main__":
    main()
