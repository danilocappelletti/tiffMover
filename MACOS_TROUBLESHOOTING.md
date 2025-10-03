# Quick macOS Troubleshooting Guide

## Problem: Can't Select TIFF Files

### Symptoms:
- File dialog opens but TIFF files are grayed out
- Only some files are selectable
- Dialog closes without selecting file

### Solution:
✅ **FIXED** - The file dialog now includes:
- `parent=self.root` parameter (required on macOS)
- Both `.tif` and `.TIF` extensions (case-sensitive filesystem)
- Proper wildcard `*` instead of `*.*`

### Test:
```bash
python test_macos_compatibility.py
```
Click "Test Open File Dialog" - you should be able to select .tif/.tiff/.TIF/.TIFF files

---

## Problem: UI Looks Wrong/Messy

### Symptoms:
- Text is cut off
- Buttons are too small or too large
- Fonts look wrong
- Spacing is inconsistent
- UI elements overlap

### Solution:
✅ **FIXED** - The UI now uses:
- Native 'aqua' theme on macOS
- SF Pro font (macOS system font)
- 0.9× UI scale for macOS
- 0.8× padding scale for macOS
- Platform-specific adjustments

### Test:
```bash
python test_macos_compatibility.py
```
Click "Test UI Elements" - window should look native and clean

---

## Problem: Application Crashes on Launch

### Possible Causes:
1. Missing dependencies
2. Python version incompatibility
3. Pillow/PIL issues

### Solutions:

#### 1. Check Python Version
```bash
python --version  # Should be 3.8 or higher
```

#### 2. Reinstall Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Check PIL Installation
```bash
python -c "from PIL import Image; print('PIL OK')"
```

#### 4. Check tkinter
```bash
python -c "import tkinter; print('tkinter OK')"
```

---

## Problem: Can't Run test_macos_compatibility.py

### Solution:
```bash
# Make it executable
chmod +x test_macos_compatibility.py

# Run with python
python test_macos_compatibility.py
```

---

## Problem: Performance Issues on macOS

### Tips:
1. **Enable Fast Zoom Mode**
   - Click "🚀 Fast Zoom" button in toolbar
   - Or check "Fast Zoom Mode" in tools panel

2. **Clear Cache Regularly**
   - Click "🗑️ Clear Cache" button
   - Helps with memory management

3. **Use Smaller Images for Testing**
   - Start with small TIFF files
   - Scale up after confirming it works

4. **Monitor Memory**
   - Click "📊 Update Stats" in tools panel
   - Check cache memory usage

---

## Problem: Building macOS Application Fails

### Requirements:
```bash
pip install pyinstaller
```

### Build Command:
```bash
python build_cross_platform.py macos
```

### Common Issues:

#### Issue: "PyInstaller not found"
```bash
pip install pyinstaller
```

#### Issue: "Icon file not found"
- Not critical, build will continue without icon
- Create `icon.icns` for macOS app icon

#### Issue: Build succeeds but app won't run
1. Check console for errors:
```bash
./dist/macos/TIFF_Image_Editor
```

2. Check permissions:
```bash
chmod +x ./dist/macos/TIFF_Image_Editor
```

---

## Quick Command Reference

### Run Application
```bash
python image_editor.py
```

### Run Tests
```bash
python test_macos_compatibility.py
```

### Build for macOS
```bash
python build_cross_platform.py macos
```

### Check Dependencies
```bash
pip list | grep -i "pillow\|numpy\|psutil"
```

### Clear Python Cache
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

---

## Still Having Issues?

### 1. Check the Logs
Look for error messages in terminal output

### 2. Verify File Structure
```bash
ls -la
# Should see: image_editor.py, build_cross_platform.py, etc.
```

### 3. Check Python Path
```bash
which python
python --version
```

### 4. Virtual Environment
If using venv:
```bash
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows
```

### 5. Test Individual Components
```python
# Test PIL
python -c "from PIL import Image; img = Image.new('RGB', (100, 100)); print('PIL works')"

# Test tkinter
python -c "import tkinter as tk; root = tk.Tk(); print('tkinter works'); root.destroy()"

# Test file operations
python -c "import os; print('CWD:', os.getcwd())"
```

---

## macOS-Specific Notes

### File System
- macOS uses HFS+ or APFS (case-insensitive by default, but case-preserving)
- File extensions matter: `.tif` ≠ `.TIF` on some systems
- Solution: Code now handles both cases

### Security
- macOS may ask for permission to access files
- Grant access when prompted
- Check System Preferences > Security & Privacy if blocked

### Gatekeeper
If app is blocked:
```bash
xattr -cr TIFF_Image_Editor.app
```

### Retina Displays
- App should handle high DPI automatically
- If images look blurry, check the DPI setting in tools panel

---

## Success Indicators

✅ File dialog shows TIFF files and they're selectable
✅ UI looks clean with proper spacing
✅ Fonts are readable (SF Pro on macOS)
✅ No overlapping UI elements
✅ Application responds to clicks and keyboard
✅ Images load and display correctly
✅ All features work as expected

---

**Last Updated:** October 3, 2025
**Tested On:** macOS 10.14+
