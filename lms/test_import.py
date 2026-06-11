
import os
import sys

# Add project root to path
sys.path.append(r"c:/Users/BRISTON/Desktop/CCNA CLASSES/lms/lms")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import config.urls
    print("Successfully imported config.urls")
except Exception as e:
    print(f"Failed to import config.urls: {e}")
except SyntaxError as e:
    print(f"SyntaxError importing config.urls: {e}")
