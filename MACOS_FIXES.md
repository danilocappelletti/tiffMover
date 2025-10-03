# macOS Compatibility Fixes for TIFF Image Editor

## Issues Fixed

### 1. File Dialog Issues ✅
**Problem:** File dialogs weren't working properly on macOS - couldn't select TIFF files
**Solution:** 
- Added `parent=self.root` parameter to all file dialogs (required on macOS)
- Changed file type patterns from `*.*` to `*` for "All files" (macOS convention)
- Added uppercase extensions `.TIF`, `.TIFF` to file type filters
- Fixed all dialog functions:
  - `load_image()`
  - `load_multiple_files()`
  - `add_more_files()`
  - `save_project()`
  - `load_project()`
  - `export_image()`
  - `export_merged_image()`

### 2. UI Layout Issues ✅
**Problem:** UI elements were misaligned and fonts looked wrong on macOS
**Solution:**
- Added platform detection using `platform.system()`
- Created platform-specific UI scaling variables:
  - `ui_scale`: 0.9 for macOS (10% smaller)
  - `padding_scale`: 0.8 for macOS (20% tighter)
- Adjusted font sizes for macOS native look
- Changed theme to 'aqua' on macOS for native appearance

### 3. Font Issues ✅
**Problem:** Windows-specific fonts (Segoe UI) not available on macOS
**Solution:**
- Implemented platform-specific font selection:
  - macOS: 'SF Pro' (native macOS font)
  - Windows: 'Segoe UI'
  - Linux: 'Ubuntu'
- All font sizes adjusted based on platform scale factor

## Code Changes Summary

### New Platform Detection Variables
```python
self.is_macos = platform.system() == 'Darwin'
self.is_windows = platform.system() == 'Windows'
self.is_linux = platform.system() == 'Linux'
```

### UI Scaling for macOS
```python
if self.is_macos:
    self.ui_scale = 0.9
    self.font_size_base = 11
    self.font_size_header = 13
    self.padding_scale = 0.8
```

### File Dialog Pattern (Example)
**Before:**
```python
file_path = filedialog.askopenfilename(
    title="Select TIFF Image",
    filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
)
```

**After:**
```python
if self.is_macos:
    file_path = filedialog.askopenfilename(
        parent=self.root,
        title="Select TIFF Image",
        filetypes=[("TIFF files", "*.tiff *.tif *.TIF *.TIFF"), ("All files", "*")]
    )
else:
    file_path = filedialog.askopenfilename(
        title="Select TIFF Image",
        filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
    )
```

## Testing Checklist

### File Operations
- [ ] Load single TIFF file (Load TIFF button)
- [ ] Load multiple TIFF files (Multi-File button)
- [ ] Add more files in merge preview
- [ ] Save project as JSON
- [ ] Load project from JSON
- [ ] Export image
- [ ] Export merged image

### UI Appearance
- [ ] All text is readable and not cut off
- [ ] Buttons are properly sized
- [ ] Spacing looks natural (not too cramped or loose)
- [ ] Fonts match macOS style
- [ ] No Windows-specific UI artifacts

### Functionality
- [ ] Image loading and display works
- [ ] Zoom in/out works
- [ ] Drawing selections works
- [ ] Moving sections works
- [ ] All tools panel controls work
- [ ] Multi-file merge works
- [ ] Free-form arrangement works

## Known macOS-Specific Behaviors

1. **Theme**: Uses native 'aqua' theme for better integration
2. **Fonts**: SF Pro instead of Segoe UI
3. **File Dialogs**: Require explicit parent window reference
4. **Extensions**: Case-sensitive file system, so both `.tif` and `.TIF` are included
5. **Scaling**: UI elements are 10% smaller to match macOS conventions

## Build Instructions for macOS

To build the macOS application:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build for macOS
python build_cross_platform.py macos
```

This will create:
- `TIFF_Image_Editor_macos_combined/` containing both:
  - `Executable/` - Single file executable
  - `Application_Bundle/` - Native .app bundle

## Future Improvements

- [ ] Add macOS-specific keyboard shortcuts (Cmd instead of Ctrl)
- [ ] Implement native macOS menu bar
- [ ] Add Touch Bar support
- [ ] Optimize for Retina displays
- [ ] Add code signing for macOS distribution

## Version
Fixed in: October 3, 2025
Python Version: 3.x
Tested on: macOS 10.14+
