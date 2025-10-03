#!/usr/bin/env python3
"""
Quick test script to verify macOS compatibility fixes
Run this to check if platform detection and file dialogs work correctly
"""

import platform
import tkinter as tk
from tkinter import filedialog, messagebox

def test_platform_detection():
    """Test platform detection"""
    print("=" * 50)
    print("PLATFORM DETECTION TEST")
    print("=" * 50)
    
    system = platform.system()
    print(f"Platform: {system}")
    
    is_macos = system == 'Darwin'
    is_windows = system == 'Windows'
    is_linux = system == 'Linux'
    
    print(f"Is macOS: {is_macos}")
    print(f"Is Windows: {is_windows}")
    print(f"Is Linux: {is_linux}")
    
    if is_macos:
        print("✅ Running on macOS - special handling enabled")
    elif is_windows:
        print("✅ Running on Windows - standard handling")
    elif is_linux:
        print("✅ Running on Linux - standard handling")
    else:
        print("⚠️  Unknown platform")
    
    print()
    return is_macos

def test_file_dialog(root, is_macos):
    """Test file dialog functionality"""
    print("=" * 50)
    print("FILE DIALOG TEST")
    print("=" * 50)
    
    print("Testing file open dialog...")
    
    if is_macos:
        print("Using macOS-specific dialog settings...")
        file_path = filedialog.askopenfilename(
            parent=root,
            title="Test: Select a TIFF Image (macOS)",
            filetypes=[("TIFF files", "*.tiff *.tif *.TIF *.TIFF"), ("All files", "*")]
        )
    else:
        print("Using standard dialog settings...")
        file_path = filedialog.askopenfilename(
            title="Test: Select a TIFF Image",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
        )
    
    if file_path:
        print(f"✅ File selected: {file_path}")
        messagebox.showinfo("Success", f"File dialog works!\n\nSelected: {file_path}")
        return True
    else:
        print("⚠️  No file selected (user cancelled)")
        return False

def test_save_dialog(root, is_macos):
    """Test save dialog functionality"""
    print("=" * 50)
    print("SAVE DIALOG TEST")
    print("=" * 50)
    
    print("Testing file save dialog...")
    
    if is_macos:
        print("Using macOS-specific dialog settings...")
        file_path = filedialog.asksaveasfilename(
            parent=root,
            title="Test: Save File (macOS)",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*")]
        )
    else:
        print("Using standard dialog settings...")
        file_path = filedialog.asksaveasfilename(
            title="Test: Save File",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff"), ("All files", "*.*")]
        )
    
    if file_path:
        print(f"✅ Save location selected: {file_path}")
        messagebox.showinfo("Success", f"Save dialog works!\n\nLocation: {file_path}")
        return True
    else:
        print("⚠️  No location selected (user cancelled)")
        return False

def test_ui_elements(root, is_macos):
    """Test UI element creation with platform-specific settings"""
    print("=" * 50)
    print("UI ELEMENTS TEST")
    print("=" * 50)
    
    # Create test window
    test_window = tk.Toplevel(root)
    test_window.title("UI Test - " + ("macOS" if is_macos else "Other Platform"))
    test_window.geometry("400x300")
    
    # Platform-specific settings
    if is_macos:
        ui_scale = 0.9
        padding_scale = 0.8
        font_family = 'SF Pro'
        print(f"Using macOS UI settings:")
        print(f"  - UI Scale: {ui_scale}")
        print(f"  - Padding Scale: {padding_scale}")
        print(f"  - Font: {font_family}")
    else:
        ui_scale = 1.0
        padding_scale = 1.0
        font_family = 'Segoe UI' if platform.system() == 'Windows' else 'Ubuntu'
        print(f"Using standard UI settings:")
        print(f"  - UI Scale: {ui_scale}")
        print(f"  - Padding Scale: {padding_scale}")
        print(f"  - Font: {font_family}")
    
    # Create test elements
    frame = tk.Frame(test_window, bg='#f0f0f0')
    frame.pack(fill=tk.BOTH, expand=True, padx=int(20 * padding_scale), pady=int(20 * padding_scale))
    
    label = tk.Label(frame, 
                     text="UI Test Window", 
                     font=(font_family, int(14 * ui_scale), 'bold'),
                     bg='#f0f0f0')
    label.pack(pady=int(10 * padding_scale))
    
    button = tk.Button(frame,
                       text="Test Button",
                       font=(font_family, int(10 * ui_scale)),
                       bg='#2563eb',
                       fg='white',
                       padx=int(15 * padding_scale),
                       pady=int(8 * padding_scale))
    button.pack(pady=int(5 * padding_scale))
    
    text_label = tk.Label(frame,
                          text="This is a test label with normal text.\nIt should be readable and properly sized.",
                          font=(font_family, int(9 * ui_scale)),
                          bg='#f0f0f0',
                          justify='center')
    text_label.pack(pady=int(10 * padding_scale))
    
    info_text = "✅ UI elements created successfully!\n\n"
    info_text += f"Font: {font_family}\n"
    info_text += f"Scale: {ui_scale}\n"
    info_text += f"Padding: {padding_scale}"
    
    info_label = tk.Label(frame,
                          text=info_text,
                          font=(font_family, int(8 * ui_scale)),
                          bg='#e0e0e0',
                          fg='#333',
                          justify='left',
                          padx=int(10 * padding_scale),
                          pady=int(10 * padding_scale))
    info_label.pack(pady=int(10 * padding_scale), fill=tk.X)
    
    close_btn = tk.Button(frame,
                          text="Close",
                          command=test_window.destroy,
                          font=(font_family, int(9 * ui_scale)),
                          bg='#6c757d',
                          fg='white',
                          padx=int(10 * padding_scale),
                          pady=int(5 * padding_scale))
    close_btn.pack(pady=int(10 * padding_scale))
    
    print("✅ UI test window created")
    print("    Check if text is readable and elements are properly sized")

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("macOS COMPATIBILITY TEST SUITE")
    print("=" * 50)
    print()
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Test platform detection
    is_macos = test_platform_detection()
    
    # Create visible test window
    root.deiconify()
    root.title("macOS Compatibility Tests")
    root.geometry("500x400")
    
    # Create main frame
    main_frame = tk.Frame(root, bg='#f0f0f0')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    title = tk.Label(main_frame,
                     text="macOS Compatibility Tests",
                     font=('Arial', 16, 'bold'),
                     bg='#f0f0f0')
    title.pack(pady=10)
    
    status = tk.Label(main_frame,
                      text=f"Platform: {platform.system()}",
                      font=('Arial', 12),
                      bg='#f0f0f0')
    status.pack(pady=5)
    
    # Test buttons
    btn_frame = tk.Frame(main_frame, bg='#f0f0f0')
    btn_frame.pack(pady=20)
    
    tk.Button(btn_frame,
              text="Test Open File Dialog",
              command=lambda: test_file_dialog(root, is_macos),
              font=('Arial', 11),
              bg='#2563eb',
              fg='white',
              padx=15,
              pady=8).pack(pady=5, fill=tk.X)
    
    tk.Button(btn_frame,
              text="Test Save File Dialog",
              command=lambda: test_save_dialog(root, is_macos),
              font=('Arial', 11),
              bg='#059669',
              fg='white',
              padx=15,
              pady=8).pack(pady=5, fill=tk.X)
    
    tk.Button(btn_frame,
              text="Test UI Elements",
              command=lambda: test_ui_elements(root, is_macos),
              font=('Arial', 11),
              bg='#7c3aed',
              fg='white',
              padx=15,
              pady=8).pack(pady=5, fill=tk.X)
    
    tk.Button(btn_frame,
              text="Exit",
              command=root.quit,
              font=('Arial', 11),
              bg='#dc2626',
              fg='white',
              padx=15,
              pady=8).pack(pady=15, fill=tk.X)
    
    instructions = tk.Label(main_frame,
                            text="Click the buttons above to test each feature.\n"
                                 "All tests should work smoothly on macOS.",
                            font=('Arial', 9),
                            bg='#f0f0f0',
                            fg='#666',
                            justify='center')
    instructions.pack(pady=10)
    
    print("\n✅ Test suite ready!")
    print("📝 Click the buttons in the window to run tests")
    print()
    
    root.mainloop()

if __name__ == "__main__":
    main()
