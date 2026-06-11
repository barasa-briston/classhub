import re
import os

file_path = r'c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates\lecturer_dashboard.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check for split {% ... %}
    if '{%' in line and '%}' not in line:
        joined_tag = line.strip()
        i += 1
        while i < len(lines) and '%}' not in lines[i]:
            joined_tag += ' ' + lines[i].strip()
            i += 1
        if i < len(lines):
            joined_tag += ' ' + lines[i].strip()
        new_lines.append(joined_tag + '\n')
    # Check for split {{ ... }}
    elif '{{' in line and '}}' not in line:
        joined_tag = line.strip()
        i += 1
        while i < len(lines) and '}}' not in lines[i]:
            joined_tag += ' ' + lines[i].strip()
            i += 1
        if i < len(lines):
            joined_tag += ' ' + lines[i].strip()
        new_lines.append(joined_tag + '\n')
    else:
        new_lines.append(line)
    i += 1

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(new_lines)

print("Definitively joined all split tags in lecturer_dashboard.html")
