
import os

file_path = r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms/accounts/views.py"

try:
    with open(file_path, 'rb') as f:
        content = f.read()

    # Log size before
    print(f"Original size: {len(content)} bytes")

    # Replace null bytes with nothing
    new_content = content.replace(b'\x00', b'')

    # Log size after
    print(f"New size: {len(new_content)} bytes")

    if len(content) != len(new_content):
        print("Obscure null bytes found and removed.")
        with open(file_path, 'wb') as f:
            f.write(new_content)
        print("File rewritten successfully.")
    else:
        print("No null bytes found.")

except Exception as e:
    print(f"Error: {e}")
