import argparse
import os
import pywikibot
from bs4 import BeautifulSoup
import logging

def upload_data(site, title, content):
    try:
        page = pywikibot.Page(site, title)
        page.text = content
        page.save("Uploaded data using Pywikibot")
        logging.info(f"Page '{title}' uploaded successfully.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"Error uploading page '{title}': {e}")

def read_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def convert_html_to_wiki(html_content):
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

def main():
    # Configure logging
    logging.basicConfig(filename='pywikibot.log', level=logging.INFO)

    # Set up the wiki site
    site = pywikibot.Site()

    # Login if necessary
    site.login()

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description='Upload HTML content to a MediaWiki page.')
    parser.add_argument('-H', '--html', help='Path to the HTML file', required=True)
    parser.add_argument('-T', '--title', help='Title of the wiki page', required=True)
    args = parser.parse_args()

    # Read HTML file
    html_content = read_html_file(args.html)

    # Convert HTML to wiki format
    wiki_content = convert_html_to_wiki(html_content)

    # Upload converted data to the wiki
    upload_data(site, args.title, wiki_content)

    # Upload images to the wiki
    upload_images(site, args.html)

if __name__ == "__main__":
    main()
