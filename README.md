# Professional TIFF Image Editor

A comprehensive Python application for editing high-resolution TIFF images with professional measurement tools, precision controls, and advanced navigation. Made to manage big tiff files.

## ✨ Features

### 🎯 **Core Functionality**
- **Load High-Resolution TIFF Images**: Support for large TIFF files with automatic DPI detection
- **Free Drawing Selection Tool**: Draw freehand selections around areas of interest  
- **Color Assignment & Overlays**: Assign custom colors with opacity control to selected sections
- **Clipped Sections**: Cut out sections with transparency and colored overlays
- **Professional Section Management**: Move, rearrange, duplicate, and manage multiple selections

### 📐 **Professional Measurement Tools**
- **Centimeter-Based Grid System**: Professional grid with major/minor lines and cm labels
- **DPI-Aware Measurements**: Automatic DPI detection from TIFF metadata
- **Movable Ruler**: Drag-to-measure ruler with real-time distance calculation
- **Precision Movement Controls**: Move sections by exact centimeter values
- **Real-time Coordinate Display**: All positions shown in professional cm units

### 🎮 **Advanced Navigation**
- **Mouse Wheel Zoom**: Zoom in/out centered on cursor position
- **WASD + Arrow Key Navigation**: Pan around the image with keyboard
- **Smart Focus System**: Click on image to enable navigation, click UI to disable
- **Keyboard Shortcuts**: Professional keyboard controls for all operations
- **Speed Controls**: Hold Shift for faster navigation and movement

### 🎨 **Advanced Tools**
- **Vertical Guide Lines**: Configurable guide lines for alignment
- **Brush Size Control**: Adjustable selection brush with visual feedback
- **Grid Snapping**: Snap movements to grid for precise positioning
- **Sub-pixel Precision Mode**: Ultra-precise positioning when needed
- **Real-time Status Feedback**: Live coordinate display and operation status

## 🚀 **Quick Start**

### Prerequisites
1. **Install Python 3.11+**: Download from [python.org](https://www.python.org/downloads/)
   - ✅ Make sure to check "Add Python to PATH" during installation
   - ✅ Verify installation: `python --version`

### Option 1: Run from Source
1. **Create virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate it
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   
   # Windows Command Prompt:
   .\.venv\Scripts\activate.bat
   
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python image_editor.py
   ```

### Option 2: Build Executable
Build a standalone executable for distribution:

1. **Activate virtual environment**: `.\.venv\Scripts\Activate.ps1`
2. **Install requirements**: `pip install -r requirements.txt`  
3. **Build executable**: `python build_cross_platform.py`
4. **Find executable**: In `dist/windows/` or `TIFF_Image_Editor_windows/`

## 📖 **Usage Guide**

### Basic Workflow
1. **Load Image**: Click "Load TIFF" and select your TIFF file (DPI auto-detected)
2. **Enable Navigation**: Click on image to enable mouse wheel zoom and WASD navigation
3. **Select Areas**: Use Clip mode to draw selections around areas of interest
4. **Assign Colors**: Choose colors from picker with opacity control  
5. **Move Sections**: Switch to Move mode, select sections, use gamepad controls or arrow keys
6. **Measure**: Use the ruler tool for precise measurements in centimeters
7. **Export**: Save your edited image with professional measurements

### 🎮 **Navigation Controls**
- **🖱️ Mouse Wheel**: Zoom in/out at cursor location
- **WASD / Arrow Keys**: Navigate around image (click on image first to enable)
- **Shift + Navigation**: Faster panning/movement  
- **Click Image**: Enable navigation mode (✅ green status)
- **Click UI Elements**: Disable navigation mode (❌ red status)

### 🎯 **Professional Features**
- **Centimeter Grid**: All measurements in professional cm units
- **Ruler Tool**: Drag to measure distances accurately
- **DPI Detection**: Automatic extraction from TIFF metadata
- **Precision Movement**: Move sections by exact cm values using gamepad controls
- **Section Coordinates**: All positions displayed in centimeters

## 🛠️ **Technical Details**

### Project Structure
```
mover/
├── image_editor.py            # Main application (2800+ lines, complete)
├── build_cross_platform.py   # Cross-platform executable builder  
├── requirements.txt           # Python dependencies
├── BUILD_INSTRUCTIONS.md     # Detailed build documentation
├── test_image.tiff           # Sample TIFF for testing
├── .venv/                    # Python virtual environment
└── README.md                 # This documentation
```

### Dependencies
- **Python 3.11+**: Core runtime with tkinter GUI
- **Pillow (PIL)**: Advanced image processing and TIFF handling
- **PyInstaller**: For building standalone executables

### Key Improvements
- **Centimeter-Only Workflow**: Removed pixel options for professional consistency
- **Mouse Wheel Zoom**: Smooth zooming centered on cursor
- **Smart Navigation**: WASD/arrow key panning with focus control
- **DPI-Aware Measurements**: All measurements in real-world units
- **Professional UI**: Clean, organized interface with clear feedback

## 📦 **Building Executables**

### All Platforms
```bash
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Build for current platform
python build_cross_platform.py

# Cross-platform builds (if dependencies available)
python build_cross_platform.py windows
python build_cross_platform.py macos  
python build_cross_platform.py linux
```

**Output**: Standalone executable (~28MB) with all dependencies included

## 🔧 **Troubleshooting**

### Setup Issues
- **"Python not found"**: Download Python from [python.org](https://www.python.org/downloads/) and add to PATH
- **"venv not working"**: Make sure you're using Python 3.7+ and try `python -m venv .venv`
- **PowerShell execution policy**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **Virtual environment not activating**: Check you're in the project directory and using correct path

### Common Issues
- **"Module not found" errors**: Activate venv and run `pip install -r requirements.txt`
- **Build fails**: Ensure virtual environment is activated before building
- **Navigation not working**: Click on the image canvas to enable navigation
- **Image won't load**: Ensure file is valid TIFF format with proper metadata
- **Performance issues**: Use "Fit Window" and close other memory-intensive applications

### Professional Tips
- **DPI Accuracy**: TIFF metadata DPI is auto-detected for precise measurements
- **Grid Alignment**: Use 1cm grid spacing for standard professional measurements
- **Section Movement**: Use gamepad controls for precise cm-based positioning
- **Focus Management**: Red ❌ = navigation disabled, Green ✅ = navigation enabled
- **Measurement Consistency**: Ruler and grid now use identical cm calculations

## 🎯 **Professional Workflow**

### For Technical Documentation
1. **Load TIFF**: High-resolution technical drawings or scanned documents
2. **Set DPI**: Automatic detection ensures accurate cm measurements  
3. **Enable Grid**: 1cm grid with major/minor lines for professional alignment
4. **Measure Components**: Use ruler tool for precise distance measurements
5. **Section Selection**: Select components with accurate boundary detection
6. **Color Coding**: Assign colors to different component types or categories
7. **Export**: Generate professional documentation with measured annotations

### Architecture & Engineering
- **Scale Accuracy**: True-to-scale measurements in centimeters
- **Component Analysis**: Color-code different building elements or systems
- **Dimension Verification**: Cross-check measurements with ruler tool
- **Professional Output**: Clean, measured drawings ready for documentation

## 📄 **License**

This project is open source. Free to use, modify, and distribute for personal and commercial purposes.

---

**🚀 Ready for professional TIFF editing with precision measurements!**
