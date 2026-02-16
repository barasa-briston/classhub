import re

filepath = r'c:\Users\BRISTON\Desktop\CCNA CLASSES\lms\lms\templates\admin_dashboard.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace pp==NUMBER with pp == "NUMBER" (string comparison)
for num in ['10', '20', '30', '50', '100', '150']:
    old = '{{% if pp=={} %}}'.format(num)
    new = '{{% if pp == "{}" %}}'.format(num)
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed! Verifying...")
for i, line in enumerate(content.split('\n'), 1):
    if 'pp' in line and 'if' in line:
        print(f"  Line {i}: {line.strip()}")
