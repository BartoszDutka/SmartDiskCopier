import PyInstaller.__main__
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

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
