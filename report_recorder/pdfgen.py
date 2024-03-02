import argparse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import csv
import math

def add_images_to_pdf(pdf_path, image_paths, csv_paths):
    # Create a PDF file
    c = canvas.Canvas(pdf_path, pagesize=letter)
    # Add CSV data to the PDF
    for csv_path in csv_paths:
        try:
            with open(csv_path, 'r') as csv_file:
                # Extract the CSV file name without the extension
                file_name = csv_path.split('/')[-1].split('.')[0]
                # Add file name as header
                c.drawString(10, 770, f"csv file name: {file_name}")
                c.drawString(10, 760, "-" * 80)  # Add a separator line
                c.drawString(250, 740, "Extracted Value of csv file")
                # Create a CSV reader
                csv_reader = csv.DictReader(csv_file)
                # Calculate the total height of the CSV content
                total_height = sum(12 * len(row) + 12 for row in csv_reader)
                # Set the initial y-coordinate for the first row
                y_coordinate = 720
                pages_needed = math.ceil(total_height / 720)  # Round up to the nearest whole page
                # Reset the CSV reader to read the file again
                csv_file.seek(0)
                csv_reader = csv.DictReader(csv_file)
                # Iterate through each row in the CSV file
                for page in range(pages_needed):
                    # Iterate through each row on the current page
                    for _ in range(10):  # Assuming n rows fit on one page, adjust as needed
                        try:
                            row = next(csv_reader)
                            for key, value in row.items():
                                # Add the key (column name) and value to the PDF
                                c.drawString(10, y_coordinate, f"{key}: {value}")
                                y_coordinate -= 12  # Move the y-coordinate up for the next row
                            # Add a blank line between rows
                            y_coordinate -= 12
                        except StopIteration:
                            break
                    # Check if a new page is needed
                    if page < pages_needed - 1:
                        c.showPage()
                        y_coordinate = 720  # Reset the y-coordinate for the next page
                # Add a new page for each CSV file
                c.showPage()
        except Exception as e:
            print(f"Error adding CSV file '{csv_path}': {e}")
    # Add images to the PDF
    for image_path in image_paths:
        try:
            c.drawString(250, 740, "Graph of csv value")
            # Draw the image on the PDF
            c.drawInlineImage(image_path, 10, 200)  # Adjust the coordinates as needed
            # Add a new page for each image
            c.showPage()
        except Exception as e:
            print(f"Error adding image '{image_path}': {e}")
    # Save the PDF
    c.save()

def main():
    parser = argparse.ArgumentParser(description="Create a PDF by adding images and CSV data.")
    parser.add_argument("--pdf", required=True, help="Output PDF file path")
    parser.add_argument("--img", required=True, help="Comma-separated paths to images")
    parser.add_argument("--csv", required=False, help="Comma-separated paths to CSV files")
    args = parser.parse_args()
    pdf_path = args.pdf
    image_paths = args.img.split(",")
    csv_paths = args.csv.split(",") if args.csv else []

    add_images_to_pdf(pdf_path, image_paths, csv_paths)

if __name__ == "__main__":
    main()
