import argparse
import re
import os
import pywikibot
from bs4 import BeautifulSoup
import logging

#### make HTML template ####
def read_template_file(template_file_path):
    logging.info("Executing report_recorder read_template_file function")
    with open(template_file_path, 'r') as template_file:
        return template_file.read()

def create_html_template(template_content):
    logging.info("Executing report_recorder create_html_template function")
    # Find all occurrences of {input_config} placeholders in the template
    input_config_placeholders = re.finditer(r'{input_config}:(.+)', template_content)
    # Iterate over the placeholders and replace them with content
    for match in input_config_placeholders:
        placeholder = match.group(0)
        file_path = match.group(1).strip()
        input_config_content = read_file_content(file_path)
        template_content = template_content.replace(placeholder, generate_p_tags(input_config_content))
    return template_content

def generate_p_tags(content):
    logging.info("Executing report_recorder generate_p_tags function")
    # Generate <p> tags for each line in the content
    return "\n".join([f"<p>{line.strip()}</p>" for line in content])

def read_file_content(file_path):
    logging.info("Executing report_recorder read_file_content function")
    try:
        with open(file_path, 'r') as file:
            return file.readlines()
    except FileNotFoundError:
        return [f"File not found: {file_path}"]

#### upload data and make wiki page ####
def upload_data(site, title, content):
    logging.info("Executing report_recorder upload_data function")
    try:
        page = pywikibot.Page(site, title)
        page.text = content
        page.save("Uploaded data using Pywikibot")
        logging.info(f"Page '{title}' uploaded successfully.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"Error uploading page '{title}': {e}")

def read_html_file(html_output):
    logging.info("Executing report_recorder read_html_file function")
    with open(html_output, 'r', encoding='utf-8') as file:
        return file.read()

def convert_html_to_wiki(html_content):
    logging.info("Executing report_recorder convert_html_to_wiki function")
    # Use BeautifulSoup to parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        if 'href' in a_tag.attrs:
            href = a_tag['href']
            a_tag.replace_with(f'[{href}|{a_tag.text}]')
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            src = img_tag['src']
            img_tag.replace_with(f'[[File:{src}]]')
    return str(soup)

def upload_images(site, html_file_path):
    logging.info("Executing report_recorder upload_images function")
    # Use BeautifulSoup to parse the HTML
    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    # Find image filenames in <img> tags
    image_filenames = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_filename in image_filenames:
        image_path = os.path.join(os.path.dirname(html_file_path), image_filename)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            # Create a FilePage object
            file_page = pywikibot.FilePage(site, page.title())
            # Check if the file already exists
            if file_page.exists():
                raise ValueError("File already exists!")
            # Upload the file
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' using Pywikibot")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
            else:
                print("Upload failed.")
            logging.info(f"Image '{image_filename}' uploaded successfully.")
        else:
            logging.warning(f"Image '{image_filename}' already exists on the wiki.")

def main(input_template_file, html_output, page_title):
    os.makedirs('/var/log/kara/', exist_ok=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    # Read the HTML template from the user-specified file
    template_content = read_template_file(input_template_file)
    # Create HTML template
    html_content = create_html_template(template_content)
    # Save HTML file
    with open(html_output, 'w') as html_file:
        html_file.write(html_content)
    print(f"HTML template saved to: {html_output}")

    # Set up the wiki site
    site = pywikibot.Site()
    # Login if necessary
    site.login()
    # Read HTML file
    html_content = read_html_file(html_output)
    # Convert HTML to wiki format
    wiki_content = convert_html_to_wiki(html_content)
    # Upload converted data to the wiki
    upload_data(site, page_title, wiki_content)
    # Upload images to the wiki
    upload_images(site, html_output)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate HTML report with links to input text files.")
    parser.add_argument("-it", "--input_template", required=True, help="Template HTML file path.")
    parser.add_argument("-oh", "--html_output", required=True, help="Output HTML file path.")
    parser.add_argument("-kt", "--page_title", required=True, help="Kateb page title.")
    args = parser.parse_args()
    input_template_file = args.input_template
    html_output = args.html_output
    page_title = args.page_title

    main(input_template_file, html_output, page_title)
