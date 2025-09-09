# 🎯 Advanced TIFF Image Editor & Multi-Image Merger

A comprehensive Python application for editing gigapixel TIFF images with professional measurement tools, advanced multi-image merging capabilities, and performance-optimized workflows. Handle ANY size TIFF files with ease!

## ✨ Features

### 🚀 **Multi-Image Merge System (NEW!)**
- **Drag & Drop Interface**: Visual positioning of multiple TIFF images on a large canvas
- **Freeform Arrangement**: Position images anywhere with precise control
- **Performance Optimized**: 15% preview scaling for smooth interaction with gigapixel images
- **Dynamic Canvas Sizing**: Automatically calculates optimal canvas size to fit all images
- **Smart Coordinate System**: Preview positioning scales perfectly to full-resolution export
- **Orange Selection Borders**: Clear visual indication of selected images during positioning
- **Real-time Preview**: See exactly how your merged image will look

### 🎯 **Single Image Editing**
- **Load Gigapixel TIFF Images**: Support for ANY size TIFF files with automatic DPI detection
- **Intelligent Performance Scaling**: Automatic preview scaling for large images (>25MP gets performance mode)
- **Free Drawing Selection Tool**: Draw freehand selections around areas of interest  
- **Color Assignment & Overlays**: Assign custom colors with opacity control to selected sections
- **Clipped Sections**: Cut out sections with transparency and colored overlays
- **Professional Section Management**: Move, rearrange, duplicate, and manage multiple selections

### 🎛️ **Performance & Quality Management**
- **Smart Performance Scaling**: 
  - >100MP images: 30% preview for smooth interaction
  - >50MP images: 50% preview scaling  
  - >25MP images: 70% preview scaling
  - <25MP images: Full resolution display
- **Full Quality Exports**: Always exports at full resolution regardless of preview scaling
- **Export Verification**: Confirmation dialog shows exact export resolution and megapixels
- **Visibility-First Design**: Ensures images remain visible and usable at all scales

### 📐 **Professional Measurement Tools**
- **Centimeter-Based Grid System**: Professional grid with major/minor lines and cm labels
- **DPI-Aware Measurements**: Automatic DPI detection from TIFF metadata
- **Movable Ruler**: Drag-to-measure ruler with real-time distance calculation
- **Precision Movement Controls**: Move sections by exact centimeter values
- **Real-time Coordinate Display**: All positions shown in professional cm units

### 🎮 **Advanced Navigation**
- **Mouse Wheel Zoom**: Zoom in/out centered on cursor position (both single & multi-image modes)
- **WASD + Arrow Key Navigation**: Pan around images with keyboard
- **Smart Focus System**: Click on canvas to enable navigation, click UI to disable
- **Multi-Image Canvas**: Large 5000×4000px default canvas with 30% default zoom
- **Keyboard Shortcuts**: Professional keyboard controls for all operations
- **Speed Controls**: Hold Shift for faster navigation and movement

### 🎨 **Advanced Visual Tools**
- **Vertical Guide Lines**: Configurable guide lines for alignment
- **Brush Size Control**: Adjustable selection brush with visual feedback
- **Grid Snapping**: Snap movements to grid for precise positioning
- **Sub-pixel Precision Mode**: Ultra-precise positioning when needed
- **Real-time Status Feedback**: Live coordinate display and operation status
- **Visual Selection Indicators**: Orange borders for selected images in multi-image mode

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

### 🔀 **Multi-Image Merge Workflow (NEW!)**
1. **Load Multiple Images**: Click "Load Multiple Files" and select your TIFF files
2. **Automatic Performance Mode**: Large images automatically use preview scaling for smooth interaction
3. **Drag & Drop Positioning**: 
   - Click and drag images to position them on the canvas
   - Orange borders show selected images
   - Use mouse wheel to zoom in/out for precise positioning
4. **Arrange Layout**: Position images exactly where you want them in the final merge
5. **Preview & Export**: 
   - See real-time preview of your arrangement
   - Click "Export Merged Image" to create full-resolution composite
   - Dynamic canvas automatically sizes to fit all positioned images

### 🎯 **Single Image Editing Workflow**
1. **Load Image**: Click "Load TIFF" and select your TIFF file (DPI auto-detected)
2. **Automatic Performance Scaling**: Large images (>25MP) automatically use preview scaling
3. **Enable Navigation**: Click on image to enable mouse wheel zoom and WASD navigation
4. **Select Areas**: Use Clip mode to draw selections around areas of interest
5. **Assign Colors**: Choose colors from picker with opacity control  
6. **Move Sections**: Switch to Move mode, select sections, use gamepad controls or arrow keys
7. **Measure**: Use the ruler tool for precise measurements in centimeters
8. **Export**: Save your edited image with full resolution quality verification

### 🎮 **Navigation Controls**
- **🖱️ Mouse Wheel**: Zoom in/out at cursor location (works in both single & multi-image modes)
- **WASD / Arrow Keys**: Navigate around canvas (click on canvas first to enable)
- **Shift + Navigation**: Faster panning/movement  
- **Click Canvas**: Enable navigation mode (✅ green status)
- **Click UI Elements**: Disable navigation mode (❌ red status)
- **Drag & Drop**: Click and drag images in multi-image mode for positioning

### 🚀 **Performance Features**
- **Intelligent Scaling**: Automatic performance optimization based on image size
- **Smooth Interactions**: Preview scaling ensures responsive drag-and-drop
- **Quality Preservation**: Full resolution always maintained for exports
- **Memory Management**: Efficient handling of gigapixel images
- **Real-time Preview**: See exactly how your final merge will look

### 🎯 **Professional Features**
- **Multi-Image Compositing**: Merge multiple TIFF images with precise positioning
- **Dynamic Canvas Sizing**: Automatically calculates optimal output dimensions
- **Centimeter Grid**: All measurements in professional cm units (single image mode)
- **Ruler Tool**: Drag to measure distances accurately (single image mode)
- **DPI Detection**: Automatic extraction from TIFF metadata
- **Precision Movement**: Move sections by exact cm values using gamepad controls
- **Export Verification**: Detailed confirmation of export resolution and quality

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
- **Multi-Image Merge System**: Complete drag-and-drop interface for merging multiple TIFF files
- **Performance-Optimized Preview**: Intelligent scaling system for smooth interaction with gigapixel images
- **Dynamic Canvas Management**: Automatically sizes output canvas to fit positioned images
- **Quality Assurance**: Full resolution exports with verification dialogs
- **Smart Coordinate System**: Preview positioning perfectly scales to full-resolution output
- **Enhanced Navigation**: Mouse wheel zoom and WASD navigation work in both single and multi-image modes
- **Professional UI**: Clean, organized interface with clear visual feedback and selection indicators

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

## 🎯 **Professional Workflows**

### 🔀 **Multi-Image Compositing**
1. **Document Assembly**: Combine multiple scanned pages or sections into single composite
2. **Technical Drawing Merge**: Join multiple technical drawings with precise alignment
3. **Panoramic Creation**: Merge overlapping images into wide panoramic views
4. **Comparison Layouts**: Position multiple versions side-by-side for comparison
5. **Quality Control**: Performance preview ensures smooth positioning, full-resolution export ensures quality

### 📐 **Single Image Analysis** 
1. **Load TIFF**: High-resolution technical drawings or scanned documents
2. **Automatic Performance Mode**: Large images automatically optimized for smooth interaction
3. **Enable Grid**: 1cm grid with major/minor lines for professional alignment
4. **Measure Components**: Use ruler tool for precise distance measurements
5. **Section Selection**: Select components with accurate boundary detection
6. **Color Coding**: Assign colors to different component types or categories
7. **Full-Resolution Export**: Generate professional documentation with verified quality

### 🏗️ **Architecture & Engineering Applications**
- **Multi-Sheet Assembly**: Combine multiple architectural sheets into complete floor plans
- **Scale Accuracy**: True-to-scale measurements in centimeters (single image mode)
- **Component Analysis**: Color-code different building elements or systems
- **Dimension Verification**: Cross-check measurements with ruler tool
- **Professional Output**: Clean, measured drawings ready for documentation
- **Gigapixel Support**: Handle even the largest technical drawings with smooth performance

### 📊 **Performance Optimization Use Cases**
- **Large File Handling**: Smooth interaction with 100MP+ images
- **Memory Efficiency**: Work with multiple gigapixel images simultaneously  
- **Quality Assurance**: Export verification ensures no quality loss in final output
- **Workflow Efficiency**: Performance preview + full-resolution export = best of both worlds

## 📄 **License**

This project is open source. Free to use, modify, and distribute for personal and commercial purposes.

---

**🚀 Ready for professional TIFF editing with precision measurements!**
