import os
import shutil

def export_project():
    source_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(source_dir, "LMS_DEPLOY_READY")
    
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    
    os.makedirs(target_dir)
    
    # Folders to copy
    to_copy = ["lms", "deployment_ubuntu"]
    # Patterns to exclude
    exclude = ["venv", ".venv", "__pycache__", "staticfiles", ".git", ".vscode", "lt.log", "cf.log", "cf_tunnel.log", "ngrok.log", "lt.log", "server_error.log"]

    for item in to_copy:
        s_path = os.path.join(source_dir, item)
        t_path = os.path.join(target_dir, item)
        
        if os.path.isdir(s_path):
            print(f"Copying {item}...")
            shutil.copytree(s_path, t_path, ignore=shutil.ignore_patterns(*exclude))
        elif os.path.isfile(s_path):
            shutil.copy2(s_path, t_path)

    # Copy root .env.example if it exists
    env_ex = os.path.join(source_dir, "deployment_ubuntu", ".env.example")
    if os.path.exists(env_ex):
        shutil.copy2(env_ex, os.path.join(target_dir, ".env.example"))

    print(f"\nDone! All files ready in: {target_dir}")
    print("You can now copy the 'LMS_DEPLOY_READY' folder to your flash drive.")

if __name__ == "__main__":
    export_project()
