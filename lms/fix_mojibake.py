import os

def fix_mojibake(file_path):
    replacements = {
        'ðŸ’³': '<i class="fa-solid fa-credit-card"></i>',
        'â†“': '↓',
        'â— ': '●',
        'â€“': '–', # en dash
        'â€"': '—', # em dash
        'â€˜': "'", # left single quote
        'â€™': "'", # right single quote
        'â€œ': '"', # left double quote
        'â€?': '"', # right double quote
        'â€¦': '...', # ellipsis
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        for bad, good in replacements.items():
            content = content.replace(bad, good)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file_path}")
            return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
    return False

templates_dir = 'templates'
for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            fix_mojibake(os.path.join(root, file))
