
import os
import glob

# Files to check
files = [
    r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms/accounts/__init__.py",
    r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms/__init__.py",
    r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms/config/__init__.py"
]

print("Checking init files for null bytes...")

for file_path in files:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} (not found)")
        continue
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        original_size = len(content)
        new_content = content.replace(b'\x00', b'')
        new_size = len(new_content)

        if original_size != new_size:
            print(f"Found null bytes in {os.path.basename(file_path)}. ORIGINAL: {original_size}, NEW: {new_size}")
            with open(file_path, 'wb') as f:
                f.write(new_content)
            print(f"File {os.path.basename(file_path)} cleaned.")
        else:
            print(f"{os.path.basename(file_path)}: No null bytes found.")

    except Exception as e:
        print(f"Error checking {os.path.basename(file_path)}: {e}")
