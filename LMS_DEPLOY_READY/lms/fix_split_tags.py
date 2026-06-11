
import os

file_path = r"c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates\lecturer_dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Check if a tag is split
    if '{{' in line and '}}' not in line:
        # It's split. Find the closing brace.
        combined_line = line.rstrip() # keep indentation
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            combined_line += " " + next_line.strip()
            if '}}' in next_line:
                new_lines.append(combined_line + "\n")
                i = j + 1
                break
            j += 1
        else:
            # Didn't find closing brace? just append line
            new_lines.append(line)
            i += 1
    else:
        new_lines.append(line)
        i += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File updated successfully.")
