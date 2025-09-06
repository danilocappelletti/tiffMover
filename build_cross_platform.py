#!/usr/bin/env python3
"""
Cross-platform build script for TIFF Image Editor
Builds executables for Windows, macOS, and Linux from image_editor.py
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

class CrossPlatformBuilder:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.main_file = self.script_dir / "image_editor.py"
        self.app_name = "TIFF_Image_Editor"
        
    def check_requirements(self):
        """Check if all requirements are met."""
        if not self.main_file.exists():
            print("❌ image_editor.py not found!")
            return False
            
        # Check Python packages
        try:
            import tkinter
            import PIL
            print("✅ Required packages found")
        except ImportError as e:
            print(f"❌ Missing required package: {e}")
            print("💡 Install with: pip install Pillow")
            return False
            
        # Check PyInstaller
        try:
            import PyInstaller
            print("✅ PyInstaller found")
        except ImportError:
            print("❌ PyInstaller not found")
            print("💡 Install with: pip install pyinstaller")
            return False
            
        return True
        
    def build_windows(self):
        """Build Windows executable."""
        print("\n🪟 Building for Windows...")
        
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed", 
            "--name=" + self.app_name,
            "--distpath=dist/windows",
            str(self.main_file)
        ]
        
        # Add icon if available
        icon_path = self.script_dir / "icon.ico"
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])
            
        return self._run_build(cmd, "windows", ".exe")
        
    def build_macos(self):
        """Build macOS application with both executable and .app bundle."""
        print("\n🍎 Building for macOS...")
        
        # First build: Regular executable
        print("📦 Building regular executable...")
        cmd_exe = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            "--name=" + self.app_name,
            "--distpath=dist/macos",
            str(self.main_file)
        ]
        
        # Add icon if available
        icon_path = self.script_dir / "icon.icns"
        if icon_path.exists():
            cmd_exe.extend(["--icon", str(icon_path)])
        
        # Build executable
        exe_result = self._run_build(cmd_exe, "macos", "")
        
        # Second build: .app bundle
        print("📱 Building .app bundle...")
        cmd_app = [
            "pyinstaller",
            "--onedir",  # Create directory bundle
            "--windowed",
            "--name=" + self.app_name + "_App",
            "--distpath=dist/macos_app",
            str(self.main_file)
        ]
        
        if icon_path.exists():
            cmd_app.extend(["--icon", str(icon_path)])
            
        app_result = self._run_build_app(cmd_app, "macos_app", ".app")
        
        # Create combined package
        if exe_result and app_result:
            self._create_macos_combined_package()
        
        return exe_result or app_result
        
    def build_linux(self):
        """Build Linux executable."""
        print("\n🐧 Building for Linux...")
        
        cmd = [
            "pyinstaller",
            "--onefile",
            "--name=" + self.app_name,
            "--distpath=dist/linux",
            str(self.main_file)
        ]
        
        return self._run_build(cmd, "linux", "")
        
    def _run_build(self, cmd, platform_name, extension):
        """Run the build command and create portable package."""
        try:
            print(f"▶️ Running PyInstaller for {platform_name}...")
            result = subprocess.run(cmd, cwd=self.script_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Find the created executable
                dist_dir = self.script_dir / "dist" / platform_name
                exe_name = self.app_name + extension
                exe_path = dist_dir / exe_name
                
                if exe_path.exists() or (extension == ".app" and exe_path.is_dir()):
                    size = self._get_size(exe_path)
                    print(f"✅ {platform_name.capitalize()} build successful!")
                    print(f"📦 File: {exe_path}")
                    print(f"📏 Size: {size}")
                    
                    # Create portable package
                    self._create_portable_package(platform_name, exe_path, extension)
                    return True
                else:
                    print(f"❌ Executable not found: {exe_path}")
                    return False
            else:
                print(f"❌ Build failed for {platform_name}")
                print("STDERR:", result.stderr[:500])
                return False
                
        except Exception as e:
            print(f"❌ Build error for {platform_name}: {e}")
            return False
            
    def _run_build_app(self, cmd, platform_name, extension):
        """Run build command specifically for .app bundle creation."""
        try:
            print(f"▶️ Running PyInstaller for {platform_name} .app bundle...")
            result = subprocess.run(cmd, cwd=self.script_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Find the created .app bundle
                dist_dir = self.script_dir / "dist" / platform_name
                app_bundle = None
                
                # Look for .app bundle in the dist directory
                for item in dist_dir.iterdir():
                    if item.is_dir() and item.name.endswith('.app'):
                        app_bundle = item
                        break
                
                if app_bundle:
                    size = self._get_size(app_bundle)
                    print(f"✅ {platform_name.capitalize()} .app bundle successful!")
                    print(f"📦 Bundle: {app_bundle}")
                    print(f"📏 Size: {size}")
                    return True
                else:
                    print(f"❌ .app bundle not found in: {dist_dir}")
                    # List what was actually created
                    created_items = list(dist_dir.iterdir())
                    if created_items:
                        print("Files/folders found:")
                        for item in created_items:
                            print(f"   📁 {item.name}")
                    return False
            else:
                print(f"❌ .app bundle build failed for {platform_name}")
                print("STDERR:", result.stderr[:500])
                return False
                
        except Exception as e:
            print(f"❌ .app bundle build error for {platform_name}: {e}")
            return False
    
    def _create_macos_combined_package(self):
        """Create a combined macOS package with both executable and .app bundle."""
        try:
            print("📦 Creating combined macOS package...")
            combined_dir = self.script_dir / f"{self.app_name}_macos_combined"
            
            # Clean and create combined directory
            if combined_dir.exists():
                shutil.rmtree(combined_dir)
            combined_dir.mkdir()
            
            # Copy executable version
            exe_source = self.script_dir / "dist" / "macos"
            if exe_source.exists() and list(exe_source.iterdir()):
                exe_dest = combined_dir / "Executable"
                shutil.copytree(exe_source, exe_dest, dirs_exist_ok=True)
                print(f"✅ Copied executable to: {exe_dest}")
            
            # Copy .app bundle version
            app_source = self.script_dir / "dist" / "macos_app"
            if app_source.exists() and list(app_source.iterdir()):
                app_dest = combined_dir / "Application_Bundle"
                shutil.copytree(app_source, app_dest, dirs_exist_ok=True)
                print(f"✅ Copied .app bundle to: {app_dest}")
            
            # Copy test image if available
            test_image = self.script_dir / "test_image.tiff"
            if test_image.exists():
                shutil.copy2(test_image, combined_dir)
                print(f"✅ Copied test image")
            
            # Create comprehensive README
            readme_content = f"""# {self.app_name} - macOS Complete Package

This package contains two versions of the TIFF Image Editor for maximum compatibility:

## 📱 Application Bundle (Application_Bundle/)
- Native macOS .app format
- Drag to Applications folder for permanent installation
- Better integration with macOS system
- Recommended for regular use

## ⚡ Executable Version (Executable/)
- Single file executable: {self.app_name}
- No installation needed - run directly
- Smaller file size and faster startup
- Useful for portable/temporary use

## 🚀 How to Use

### For Installation:
1. Go to Application_Bundle/ folder
2. Drag the .app file to your Applications folder
3. Launch from Applications or Spotlight

### For Quick Use:
1. Go to Executable/ folder  
2. Double-click {self.app_name} to run
3. Or run from Terminal: `./{self.app_name}`

## ✨ Features
- Load and edit TIFF images
- Draw selections and move image sections
- Comprehensive editing tools
- Save/load projects
- Export processed images

## 📋 System Requirements
- macOS 10.14 (Mojave) or later
- No additional software installation required

Both versions contain identical functionality - choose based on your preference!

Built from image_editor.py using PyInstaller
"""
            
            readme_path = combined_dir / "README.txt"
            readme_path.write_text(readme_content)
            
            total_size = self._get_size(combined_dir)
            print(f"✅ Combined macOS package created: {combined_dir}")
            print(f"📏 Total package size: {total_size}")
            
        except Exception as e:
            print(f"❌ Failed to create combined macOS package: {e}")
            
    def _get_size(self, path):
        """Get human-readable size of file or directory."""
        if path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        else:
            size = path.stat().st_size
        return f"{size / (1024 * 1024):.1f} MB"
        
    def _create_portable_package(self, platform_name, exe_path, extension):
        """Create a portable package with the executable and documentation."""
        package_name = f"{self.app_name}_{platform_name}"
        package_dir = self.script_dir / package_name
        
        # Clean and create package directory
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir()
        
        # Copy executable/app
        if exe_path.is_dir():  # macOS .app bundle
            shutil.copytree(exe_path, package_dir / exe_path.name)
        else:
            shutil.copy2(exe_path, package_dir)
            
        # Copy test image if available
        test_image = self.script_dir / "test_image.tiff"
        if test_image.exists():
            shutil.copy2(test_image, package_dir)
            
        # Create README
        readme_content = f"""# TIFF Image Editor - {platform_name.capitalize()} Edition

## How to Run
"""
        
        if platform_name == "windows":
            readme_content += f"- Double-click `{self.app_name}.exe`\n"
        elif platform_name == "macos":
            readme_content += f"- Double-click `{self.app_name}.app`\n"
        else:  # linux
            readme_content += f"- Run `./{self.app_name}` from terminal\n- Or make executable: `chmod +x {self.app_name}` then double-click\n"
            
        readme_content += """
## Features
- Load and edit high-resolution TIFF images
- Free-form selection tool with drawing
- Color overlays on selected sections  
- Move and rearrange image sections
- Vertical guide lines with precise positioning
- Grid snapping and precision movement controls
- Smooth movement animations
- Save/load projects
- Export processed images

## Usage
1. Click "Load TIFF" to open an image
2. Use mouse to draw selections around areas
3. Switch to "Move" mode to reposition sections
4. Use the comprehensive tools panel for advanced features
5. Export your edited image when done

## System Requirements
- Modern operating system (Windows 10+, macOS 10.14+, Ubuntu 18.04+)
- No additional software installation required

Built from image_editor.py using PyInstaller
"""
        
        readme_file = "README.txt"
        with open(package_dir / readme_file, "w") as f:
            f.write(readme_content)
            
        print(f"📁 Portable package: {package_dir}")
        
    def build_all(self):
        """Build for all supported platforms."""
        print("🌍 Cross-Platform Build for TIFF Image Editor")
        print("=" * 50)
        
        if not self.check_requirements():
            return False
            
        current_os = platform.system().lower()
        print(f"🖥️  Current OS: {current_os}")
        
        results = {}
        
        # Build for current platform first
        if current_os == "windows":
            results["windows"] = self.build_windows()
        elif current_os == "darwin":
            results["macos"] = self.build_macos()  
        elif current_os == "linux":
            results["linux"] = self.build_linux()
            
        # Clean up build artifacts
        self._cleanup()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Build Summary:")
        for platform_name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"  {platform_name.capitalize()}: {status}")
            
        successful_builds = sum(results.values())
        total_builds = len(results)
        
        if successful_builds == total_builds:
            print(f"\n🎉 All {total_builds} builds completed successfully!")
        else:
            print(f"\n⚠️  {successful_builds}/{total_builds} builds successful")
            
        return successful_builds > 0
        
    def _cleanup(self):
        """Clean up build artifacts."""
        build_dirs = ["build", "dist"]
        spec_files = list(self.script_dir.glob("*.spec"))
        
        for build_dir in build_dirs:
            dir_path = self.script_dir / build_dir
            if dir_path.exists():
                shutil.rmtree(dir_path)
                
        for spec_file in spec_files:
            spec_file.unlink()
            
def main():
    builder = CrossPlatformBuilder()
    
    if len(sys.argv) > 1:
        platform_arg = sys.argv[1].lower()
        if platform_arg == "windows":
            success = builder.build_windows()
        elif platform_arg == "macos":
            success = builder.build_macos()
        elif platform_arg == "linux":
            success = builder.build_linux()
        else:
            print("❌ Invalid platform. Use: windows, macos, or linux")
            sys.exit(1)
    else:
        success = builder.build_all()
        
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
