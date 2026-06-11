import re
import os

templates_dir = r'c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates'

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                i = 0
                changed = False
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
                        changed = True
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
                        changed = True
                    else:
                        new_lines.append(line)
                    i += 1
                
                if changed:
                    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.writelines(new_lines)
                    print(f"Fixed split tags in: {os.path.relpath(file_path, templates_dir)}")
            except Exception as e:
                print(f"Error processing {file}: {e}")

print("Global template syntax repair complete.")
