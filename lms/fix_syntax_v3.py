import re
import os

file_path = r'c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates\lecturer_dashboard.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for {% ... %} split across lines
# Matches {% followed by any characters (including newlines) until %}
# Use non-greedy match to avoid eating up the whole file if multiple tags are on one line
def join_tags(match):
    return match.group(0).replace('\n', ' ').replace('\r', '').replace('  ', ' ')

# Join {% ... %}
content = re.sub(r'\{%.*?%\}', join_tags, content, flags=re.DOTALL)

# Join {{ ... }}
content = re.sub(r'\{\{.*?\}\}', join_tags, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully joined split tags in lecturer_dashboard.html")
