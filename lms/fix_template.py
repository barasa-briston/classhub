
import os

file_path = r"c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates\lecturer_dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Check for the specific split case
    if stripped.startswith('{% with st=sub.student.username') and not stripped.endswith('%}'):
        # Look ahead for the next line
        if i + 1 < len(lines):
            next_line = lines[i+1]
            if next_line.strip().startswith('gr='):
                combined = line.rstrip() + ' ' + next_line.strip() + '\n'
                new_lines.append(combined)
                i += 2 # Skip next line
                continue
    
    new_lines.append(line)
    i += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File updated successfully.")
