import os
import re

def join_split_with_tags(file_path):
    print(f"Checking {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find {% with ... %} that is split across lines
    # It looks for {% with followed by anything (non-greedy) until %}
    # The re.DOTALL flag makes . match newlines
    pattern = re.compile(r'\{% with\s+([^%]+?)\s*%\}', re.DOTALL)
    
    def replacer(match):
        inner = match.group(1)
        # Replace all newlines and multiple spaces with a single space
        inner_cleaned = re.sub(r'\s+', ' ', inner).strip()
        return f'{{% with {inner_cleaned} %}}'

    new_content = pattern.sub(replacer, content)

    if content != new_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Joined split tags in {file_path}")
    else:
        print(f"No split tags found in {file_path}")

if __name__ == "__main__":
    target = r'templates\student_dashboard.html'
    if os.path.exists(target):
        join_split_with_tags(target)
    else:
        print(f"Error: {target} not found")
