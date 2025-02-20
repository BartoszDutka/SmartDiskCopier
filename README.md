# SmartDiskCopier

A modern Windows application for automated CD/DVD disc copying with multi-drive support and real-time progress tracking.


## Key Features

✨ Modern, user-friendly interface  
📀 Support for multiple CD/DVD drives  
🔄 Automatic disc ejection after copying  
🌍 Multilingual (English and Polish)  
📊 Real-time progress monitoring  
📝 Detailed operation logging

## Requirements

- Windows operating system
- Python 3.7 or newer
- CD/DVD drive(s)

## Quick Start Guide

1. **Install Python**
   - Download from [python.org](https://www.python.org/downloads/)
   - ⚠️ During installation, check "Add Python to PATH"

2. **Install Dependencies**
   ```bash
   pip install ttkthemes wmi pywin32
   ```

3. **Run the Application**
   ```bash
   python SmartDiskCopier.py
   ```

## How to Use

1. Launch the application
2. Select your preferred language (English/Polish)
3. Choose destination folder for copied files
4. Insert a disc into any CD/DVD drive
5. The application will automatically:
   - Detect the disc
   - Create a timestamped folder
   - Copy all contents
   - Eject the disc when finished
6. Repeat with next disc if needed

## Screenshots

### Main Window
![Main Interface](screenshots/main_interface.png)

### Active Copying Process
![Copying Process](screenshots/copying_process.png)

## Common Issues & Solutions

### Installation Problems

**WMI Module Error**
```bash
pip install --upgrade wmi
```

**PyWin32 Installation Failed**
- Download installer from [PyWin32 Releases](https://github.com/mhammond/pywin32/releases)
- Choose version matching your Python installation

**Missing Tkinter**
- Reinstall Python and select "tcl/tk and IDLE" during installation

### Runtime Issues

- Ensure you have administrative privileges
- Check if your CD/DVD drive is recognized by Windows
- Verify disc is not damaged
- Confirm sufficient disk space in destination folder

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source, available under the MIT License.

## Author

Created with ❤️ for making disc copying easier

