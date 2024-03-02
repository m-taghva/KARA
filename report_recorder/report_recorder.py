import subprocess
import argparse
import re

def read_template_file(template_file_path):
    with open(template_file_path, 'r') as template_file:
        return template_file.read()

def create_html_template(template_content):
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
    # Generate <p> tags for each line in the content
    return "\n".join([f"<p>{line.strip()}</p>" for line in content])

def read_file_content(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.readlines()
    except FileNotFoundError:
        return [f"File not found: {file_path}"]

def main():
    parser = argparse.ArgumentParser(description="Generate HTML report with links to input text files.")
    parser.add_argument("-it", "--input_template", required=True, help="Template HTML file path.")
    parser.add_argument("-oh", "--html_output", required=True, help="Output HTML file path.")
    parser.add_argument("-kt", "--page_title", required=True, help="Kateb page title.")
    args = parser.parse_args()
    input_template_file = args.input_template
    html_output = args.html_output
    page_title = args.page_title

    # Read the HTML template from the user-specified file
    template_content = read_template_file(input_template_file)
    # Create HTML template
    html_content = create_html_template(template_content)
    # Save HTML file
    with open(html_output, 'w') as html_file:
        html_file.write(html_content)
    print(f"HTML template saved to: {html_output}")

    # Assuming that pwb.py is a Python script, you can run it directly without using subprocess
    pybot = f"python3 pwb.py ./scripts/userscripts/wikibot-html.py -H {html_output} -T {page_title}"
    subprocess.call(pybot, shell=True)

if __name__ == "__main__":
    main()
