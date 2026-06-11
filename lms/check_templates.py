
import os
import django
from django.conf import settings
from django.template import Template, Context, loader

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check_templates():
    template_dir = os.path.join(settings.BASE_DIR, 'templates')
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, template_dir)
                try:
                    loader.get_template(rel_path)
                    print(f"[PASS] {rel_path}")
                except Exception as e:
                    print(f"[FAIL] {rel_path}: {e}")

if __name__ == "__main__":
    check_templates()
