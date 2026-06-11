import re
import os

templates_dir = r'c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates'

# Only match {% ... %} or {{ ... }} that contain a newline
SPLIT_TAG_PATTERN = re.compile(r'(\{%[^%]*?\n[^%]*?%\}|\{\{[^}]*?\n[^}]*?\}\})', re.DOTALL)

def join_match(match):
    tag = match.group(0)
    # Collapse the newline + surrounding whitespace to a single space
    # Use a careful replacement that only collapses internal whitespace around newlines
    cleaned = re.sub(r'\s*\n\s*', ' ', tag)
    return cleaned

fixed_files = []

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if SPLIT_TAG_PATTERN.search(content):
                    new_content = SPLIT_TAG_PATTERN.sub(join_match, content)
                    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.write(new_content)
                    fixed_files.append(os.path.relpath(file_path, templates_dir))
            except Exception as e:
                print(f"Error processing {file}: {e}")

if fixed_files:
    print("Fixed split tags in:")
    for f in fixed_files:
        print(f" - {f}")
else:
    print("No split tags found in any templates.")

print("Global Repair Complete.")
