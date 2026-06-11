
import os

file_path = r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms/accounts/views.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Truncate strictly to 1346 lines
new_lines = lines[:1346]

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"File truncated to {len(new_lines)} lines.")
