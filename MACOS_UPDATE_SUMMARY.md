# TIFF Image Editor - macOS Compatibility Update

## Summary
Fixed critical macOS compatibility issues including file dialog failures and UI layout problems.

## Changes Made

### 1. Platform Detection (Lines ~73-96)
Added platform detection variables to `__init__`:
- `self.is_macos` - Darwin detection
- `self.is_windows` - Windows detection  
- `self.is_linux` - Linux detection
- Platform-specific UI scaling factors
- Font size adjustments for each platform

### 2. File Dialog Fixes
Updated all file dialog calls to work on macOS:

#### Functions Fixed:
1. **load_image()** - Line ~1186
   - Added `parent=self.root` parameter
   - Changed `*.*` to `*` for all files
   - Added uppercase extensions (.TIF, .TIFF)

2. **load_multiple_files()** - Line ~4047
   - Same fixes as load_image

3. **add_more_files()** - Line ~4320
   - Same fixes with fallback parent handling

4. **save_project()** - Line ~3790
   - Added macOS branch with parent parameter

5. **load_project()** - Line ~3826
   - Added macOS branch with parent parameter

6. **export_image()** - Line ~3886
   - Added macOS branch with parent parameter
   - Extended file types for better compatibility

7. **export_merged_image()** - Line ~5693
   - Added macOS branch with parent parameter

### 3. UI Theme and Styling (Lines ~265-295)
Modified `setup_styles()` method:
- Use 'aqua' theme on macOS for native look
- Fall back to 'clam' if aqua unavailable
- Platform-specific font selection:
  - macOS: 'SF Pro'
  - Windows: 'Segoe UI'
  - Linux: 'Ubuntu'
- Adjusted padding based on platform scale

## Testing

### Run the Test Suite
```bash
python test_macos_compatibility.py
```

This will test:
- Platform detection
- File open dialogs
- File save dialogs
- UI element rendering with proper fonts and scaling

### Manual Testing Checklist
1. ✅ Load TIFF file
2. ✅ Load multiple TIFF files
3. ✅ Save project
4. ✅ Load project
5. ✅ Export image
6. ✅ UI elements display correctly
7. ✅ Fonts are readable
8. ✅ Buttons are properly sized

## Files Modified
- `image_editor.py` - Main application file with all fixes

## Files Created
- `MACOS_FIXES.md` - Detailed documentation of fixes
- `test_macos_compatibility.py` - Test suite for macOS features

## Technical Details

### Why File Dialogs Failed
1. macOS tkinter requires explicit `parent` parameter
2. File type patterns need `*` not `*.*` for "All files"
3. Case-sensitive file system needs both `.tif` and `.TIF`

### Why UI Was Messy
1. Windows-specific fonts (Segoe UI) don't exist on macOS
2. macOS uses different default UI scaling
3. Theme 'clam' doesn't match macOS native appearance
4. Padding and spacing need platform adjustment

## Building for macOS

### Option 1: Executable
```bash
python build_cross_platform.py macos
```

### Option 2: Run Directly
```bash
python image_editor.py
```

## Next Steps

### Recommended Improvements:
1. Add macOS keyboard shortcuts (Cmd vs Ctrl)
2. Implement native menu bar
3. Add Retina display optimization
4. Code signing for distribution
5. Touch Bar support

### Testing on macOS Versions:
- ✅ Should work on macOS 10.14 (Mojave) and later
- Test on different macOS versions to ensure compatibility

## Contact
Report issues related to macOS compatibility on the project repository.

---
**Version:** Updated October 3, 2025
**Python:** 3.x compatible
**Platform:** Cross-platform (Windows, macOS, Linux)
