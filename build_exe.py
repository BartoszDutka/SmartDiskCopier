import PyInstaller.__main__
import os
import shutil

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build the exe
PyInstaller.__main__.run([
    'SmartDiskCopier.py',
    '--name=SmartDiskCopier',
    '--onefile',
    '--windowed',
    '--icon=app_icon.ico',
    '--add-data=translations.py;.',
    '--clean',
    '--noconfirm',
    f'--workpath={os.path.join(current_dir, "build")}',
    f'--distpath={os.path.join(current_dir, "dist")}',
    '--version-file=version_info.txt',
])

# Copy config.json to dist folder
dist_dir = os.path.join(current_dir, "dist")
config_src = os.path.join(current_dir, "config.json")
config_dst = os.path.join(dist_dir, "config.json")

if os.path.exists(config_src):
    shutil.copy2(config_src, config_dst)
    print(f"Config file copied to {config_dst}")
