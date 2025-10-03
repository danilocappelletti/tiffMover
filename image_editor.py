"""
High-Resolution TIFF Image Editor with Free Drawing Selection and Color Assignment

🚫 NO SIZE LIMITS: All PIL/Pillow image size restrictions removed - load any size TIFF!

NEW FEATURES:
- 🎨 FREE-FORM DRAG & DROP ARRANGEMENT: Arrange multiple images freely on a blank canvas
- 📁 MULTI-FILE MERGE: Load multiple TIFF files and merge them with different arrangements
- 🖱️ INTERACTIVE PREVIEW: Real-time drag and drop positioning with visual feedback
- 🔍 ZOOM IN DRAG & DROP: Mouse wheel zoom (10%-500%) in free-form canvas for precision work
- 🎛️ FLEXIBLE CANVAS: Custom canvas sizes with no dimension limitations
- 🎨 BACKGROUND COLORS: Choose custom background colors for merged images
- 📐 PRECISE POSITIONING: Manual position and scale controls for each image
- 🚫 UNLIMITED SIZE: Bypassed all PIL size limits - load massive TIFF files without restrictions

CORE FEATURES:
- Load single or multiple TIFF images of ANY SIZE (gigapixel images supported)
- Multi-file merge with preview (horizontal, vertical, grid, or free-form arrangement)
- Drag & drop interface for free-form image positioning
- Image scaling and positioning controls
- Free drawing selection tool
- Color assignment to selected sections
- Move and rearrange sections
- Clip/cut selected sections
- Precision movement with grid snapping and ruler tools
- Export functionality for both single and merged images
- Export with overlays: Save images WITH grid lines, vertical guides, and colored selections

TECHNICAL NOTES:
- PIL MAX_IMAGE_PIXELS set to None (removes ~89MP default limit)
- Warnings for large images suppressed
- Memory-efficient handling of gigapixel images
- Progress feedback for large image operations
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, font
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import json
import os
import time
import threading
import gc
from concurrent.futures import ThreadPoolExecutor
import weakref
from collections import OrderedDict
import psutil
import io
from functools import lru_cache
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List
import numpy as np
import platform

# Check for GPU acceleration libraries
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

# Remove PIL image size limits to handle very large TIFF files
Image.MAX_IMAGE_PIXELS = None  # Remove the default ~89MP limit
import warnings
warnings.filterwarnings("ignore", ".*exceeds limit.*", module="PIL")

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("📸 Advanced TIFF Image Editor - No Size Limits")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')
        
        # Detect platform for UI adjustments
        self.is_macos = platform.system() == 'Darwin'
        self.is_windows = platform.system() == 'Windows'
        self.is_linux = platform.system() == 'Linux'
        
        # Platform-specific UI adjustments
        if self.is_macos:
            # macOS uses smaller default fonts and different padding
            self.ui_scale = 0.9
            self.font_size_base = 11
            self.font_size_header = 13
            self.padding_scale = 0.8
        else:
            self.ui_scale = 1.0
            self.font_size_base = 9
            self.font_size_header = 12
            self.padding_scale = 1.0
        
        # Define color scheme for modern UI
        self.colors = {
            'primary': '#2563eb',      # Blue
            'secondary': '#7c3aed',    # Purple
            'success': '#059669',      # Green
            'warning': '#d97706',      # Orange
            'danger': '#dc2626',       # Red
            'dark': '#1f2937',         # Dark gray
            'light': '#f8fafc',        # Light gray
            'white': '#ffffff',
            'border': '#e5e7eb',
            'hover': '#3b82f6'
        }
        
        # Configure custom styles
        self.setup_styles()
        
        # Image variables
        self.original_image = None
        self.photo_image = None
        self.working_image = None
        self.image_scale = 1.0
        self.canvas_width = 1000
        self.canvas_height = 700
        
        # Drawing variables
        self.drawing = False
        self.selection_path = []
        self.current_selections = []
        self.selected_color = "#FF0000"
        self.brush_size = 3
        self.color_opacity = 0.3  # 30% opacity
        
        # Vertical lines variables
        self.show_lines = False
        self.num_lines = 5
        self.line_spacing_cm = 5.0  # Spacing between lines in centimeters
        self.lines_confirmed = False  # Track if lines are locked
        self.line_positions = []  # Store actual line x positions
        
        # Individual line dragging variables
        self.dragging_line = None  # Index of line being dragged
        self.line_drag_start = None  # Starting position of line drag
        self.line_objects = []  # Store canvas line object IDs for interaction
        self.line_drag_tolerance = 10  # Pixels tolerance for line selection
        
        # UI variables for lines (will be set during UI creation)
        self.lines_var = None
        self.lines_count_label = None
        self.spacing_value_label = None
        self.spacing_var = None
        
        # Mode variables
        self.current_mode = "none"  # none, select, move
        self.selected_section = None
        self.drag_start = None
        self.clipped_sections = []  # Store clipped sections as separate images
        self.resize_mode = False  # Track if we're resizing
        self.resize_corner = None  # Which corner is being dragged for resize
        
        # Precision movement variables
        self.snap_to_grid = False  # Enable grid snapping
        self.show_grid = False  # Show grid overlay
        self.precise_mode = False  # Enable sub-pixel precision
        self.last_mouse_pos = None  # Track last mouse position for smooth movement
        
        # DPI and measurement settings
        self.image_dpi = 300  # Default DPI for measurements (can be read from TIFF metadata)
        self.grid_size_cm = 1.0  # Grid size in centimeters (default 1cm)
        
        # Ruler variables
        self.show_ruler = False  # Show movable ruler
        self.ruler_start = None  # Ruler start point (x, y)
        self.ruler_end = None  # Ruler end point (x, y)
        self.ruler_dragging = False  # Track if ruler is being dragged
        self.ruler_drag_point = None  # Which point is being dragged: "start", "end", or "line"
        
        # Movement buffering for fluid motion
        self.movement_buffer = []  # Buffer for smooth movement
        self.buffer_size = 3  # Reduced buffer size for faster response
        self.last_update_time = 0  # Track time for frame rate limiting
        self.min_update_interval = 8  # Faster updates (125 FPS) for responsive movement
        self.movement_interpolation = False  # Disable interpolation for faster movement
        self.interpolation_steps = 1  # Reduced interpolation steps
        
        # Multi-file merge variables
        self.loaded_files = []  # List of file paths for merging
        self.loaded_images = []  # List of PIL Image objects
        self.merge_preview_window = None  # Preview window for merge arrangement
        self.merge_arrangement = "horizontal"  # horizontal, vertical, grid, freeform
        self.merge_spacing = 10  # Pixels between images when merging
        self.is_merged_image = False  # Track if current image is result of merge
        
        # Free-form arrangement variables
        self.image_positions = []  # List of (x, y) positions for each image
        self.image_scales = []  # List of scale factors for each image
        self.dragging_image = None  # Index of image being dragged
        self.potential_drag_image = None  # Image that might be dragged if mouse moves
        self.drag_start_pos = None  # Starting position of drag
        self.canvas_background_color = "white"  # Background color for free-form canvas
        self.freeform_canvas_size = (5000, 4000)  # Much larger default canvas size for free-form arrangement
        
        # Performance optimization variables for drag-and-drop
        self.preview_images = []  # Downscaled images for fast drag-and-drop visualization
        self.preview_photos = []  # PhotoImage objects for preview images
        self.preview_scale_factor = 0.15  # Scale factor for preview images (15% of original)
        self.selected_image_index = None  # Currently selected image index
        self.selection_border_width = 4  # Width of selection border
        
        # Freeform canvas zoom variables
        self.freeform_zoom = 0.3  # Start zoomed out to see more of the large canvas
        self.freeform_zoom_min = 0.05  # Minimum zoom level (zoom out more)
        self.freeform_zoom_max = 5.0  # Maximum zoom level
        self.freeform_canvas_original_size = (5000, 4000)  # Original canvas size before zoom
        
        # 🚀 ADVANCED PERFORMANCE OPTIMIZATION VARIABLES
        self.enable_fast_zoom = True  # Enable high-performance zoom system
        self.enable_gpu_acceleration = HAS_OPENCV  # Use GPU when available
        self.viewport_culling = True  # Only render visible portions
        self.async_rendering = True  # Use background threads for large operations
        self.max_display_pixels = 16_000_000  # Max pixels for display (4K = ~8MP, this is 16MP)
        self.lazy_loading_enabled = True  # Lazy load image regions
        self.adaptive_quality = True  # Adjust quality based on zoom speed
        
        # Enhanced image pyramid system with GPU support
        self.image_pyramid = OrderedDict()  # LRU cache for pyramid levels
        self.pyramid_levels = [0.025, 0.05, 0.1, 0.2, 0.5, 0.75, 1.0]  # Enhanced resolution levels
        self.current_pyramid_level = 1.0  # Current level being used
        self.pyramid_cache_limit = min(psutil.virtual_memory().total // 4, 4 * 1024**3)  # Dynamic limit
        
        # Advanced caching and performance tracking
        self.display_cache = OrderedDict()  # LRU cache for display images
        self.cache_max_size = 8  # Increased cache size
        self.cache_total_memory = 0  # Track memory usage
        self.cache_hit_count = 0  # Performance metrics
        self.cache_miss_count = 0
        self.last_viewport = None  # Track viewport changes
        
        # Memory management
        available_ram_gb = psutil.virtual_memory().total // (1024**3)
        self.memory_limit_mb = min(available_ram_gb * 512, 6144)  # Use half RAM, max 6GB
        self.memory_pool = {}  # Reusable memory buffers
        self.last_gc_time = time.time()
        
        # Performance profiling
        self.performance_stats = {'render_times': [], 'memory_usage': [], 'cache_efficiency': []}
        self.enable_profiling = False
        
        # GPU acceleration setup
        self.gpu_context = None
        if self.enable_gpu_acceleration:
            # GPU initialization disabled temporarily
            pass
        
        # Async rendering variables
        self.render_thread = None
        self.render_queue = []
        self.rendering_in_progress = False
        
        # Memory management
        self.memory_limit_mb = 2048  # 2GB limit for image processing
        self.auto_garbage_collect = True
        
        self.setup_ui()
        
    def setup_styles(self):
        """Setup custom ttk styles for modern UI"""
        style = ttk.Style()
        # Use aqua theme on macOS for native look, clam on other platforms
        if self.is_macos:
            try:
                style.theme_use('aqua')
            except:
                style.theme_use('clam')
        else:
            style.theme_use('clam')
        
        # Platform-specific font
        if self.is_macos:
            ui_font = ('SF Pro', int(10 * self.ui_scale), 'bold')
            ui_font_normal = ('SF Pro', int(9 * self.ui_scale))
        elif self.is_windows:
            ui_font = ('Segoe UI', 10, 'bold')
            ui_font_normal = ('Segoe UI', 9)
        else:
            ui_font = ('Ubuntu', 10, 'bold')
            ui_font_normal = ('Ubuntu', 9)
        
        # Configure modern button styles
        padding_h = int(15 * self.padding_scale)
        padding_v = int(10 * self.padding_scale)
        
        style.configure('Modern.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(padding_h, padding_v),
                       font=ui_font)
        
        style.map('Modern.TButton',
                 background=[('active', self.colors['hover']),
                            ('pressed', self.colors['dark'])])
        
        # Success button style
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 10),
                       font=('Segoe UI', 10, 'bold'))
        
        style.map('Success.TButton',
                 background=[('active', '#047857'),
                            ('pressed', '#065f46')])
        
        # Warning button style
        style.configure('Warning.TButton',
                       background=self.colors['warning'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 10),
                       font=('Segoe UI', 10, 'bold'))
        
        style.map('Warning.TButton',
                 background=[('active', '#b45309'),
                            ('pressed', '#92400e')])
        
        # Danger button style
        style.configure('Danger.TButton',
                       background=self.colors['danger'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 10),
                       font=('Segoe UI', 10, 'bold'))
        
        style.map('Danger.TButton',
                 background=[('active', '#b91c1c'),
                            ('pressed', '#991b1b')])
        
        # Frame styles
        style.configure('Card.TLabelFrame',
                       background=self.colors['white'],
                       borderwidth=1,
                       relief='solid',
                       labelmargins=(20, 10, 20, 10))
        
        style.configure('Card.TLabelFrame.Label',
                       background=self.colors['white'],
                       foreground=self.colors['dark'],
                       font=('Segoe UI', 11, 'bold'))
        
        # Notebook styles
        style.configure('Modern.TNotebook',
                       background=self.colors['light'],
                       borderwidth=0)
        
        style.configure('Modern.TNotebook.Tab',
                       background=self.colors['border'],
                       foreground=self.colors['dark'],
                       padding=(20, 10),
                       font=('Segoe UI', 9))
        
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', self.colors['white']),
                            ('active', self.colors['light'])])
        
        # Scale styles
        style.configure('Modern.Horizontal.TScale',
                       background=self.colors['white'],
                       troughcolor=self.colors['border'],
                       borderwidth=0,
                       lightcolor=self.colors['primary'],
                       darkcolor=self.colors['primary'])
        
    def setup_ui(self):
        """Setup the simple user interface"""
        # Create main container
        main_container = tk.Frame(self.root, bg='#e0e0e0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title bar
        self.create_title_bar(main_container)
        
        # Main toolbar
        self.create_toolbar(main_container)
        
        # Content area
        content_frame = tk.Frame(main_container, bg='#e0e0e0')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create three-panel layout
        self.create_tools_panel(content_frame)      # Left: Tools
        self.create_canvas(content_frame)           # Center: Canvas
        self.create_sections_panel(content_frame)   # Right: Sections
        
        # Status bar at bottom
        self.create_status_bar(main_container)
        
    def create_title_bar(self, parent):
        """Create a simple title bar"""
        title_frame = tk.Frame(parent, bg='#e0e0e0', height=40)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="TIFF Image Editor",
                              font=('Arial', 14, 'bold'),
                              bg='#e0e0e0',
                              fg='#333')
        title_label.pack(expand=True)
        
    def create_status_bar(self, parent):
        """Create a simple status bar at the bottom"""
        self.status_frame = tk.Frame(parent, bg='#333', height=25)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame,
                                    text="Ready - Load any size TIFF image (no limits) • Multi-file merge with zoom & drag-drop available",
                                    font=('Arial', 9),
                                    bg='#333',
                                    fg='white',
                                    anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10, pady=3)
        
        # Coordinate display for precision
        self.coord_label = tk.Label(self.status_frame,
                                   text="",
                                   font=('Arial', 8),
                                   bg='#333',
                                   fg='#90EE90',  # Light green
                                   anchor=tk.E)
        self.coord_label.pack(side=tk.RIGHT, padx=10, pady=3)
    
    def update_status(self, message):
        """Update the status bar message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
    
    def update_image_info(self, info):
        """Update the image info in status bar"""
        if hasattr(self, 'image_info_label'):
            self.image_info_label.config(text=info)
        
    def create_toolbar(self, parent):
        """Create a simple, clean toolbar"""
        # Simple toolbar container
        toolbar_container = tk.Frame(parent, bg='#f5f5f5', relief='solid', bd=1)
        toolbar_container.pack(fill=tk.X, pady=(0, 10))
        
        # Single row of buttons with simple layout
        button_frame = tk.Frame(toolbar_container, bg='#f5f5f5')
        button_frame.pack(pady=10, padx=10)
        
        # File operations
        tk.Button(button_frame, text="Load TIFF", command=self.load_image,
                 bg='#4CAF50', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="📁 Multi-File", command=self.load_multiple_files,
                 bg='#9C27B0', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Save Project", command=self.save_project,
                 bg='#2196F3', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Load Project", command=self.load_project,
                 bg='#2196F3', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Export Image", command=self.export_image,
                 bg='#FF9800', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(button_frame, bg='#ddd', width=2, height=30).pack(side=tk.LEFT, padx=10)
        
        # View controls
        tk.Button(button_frame, text="Zoom In", command=self.zoom_in,
                 bg='#607D8B', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Zoom Out", command=self.zoom_out,
                 bg='#607D8B', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Fit Window", command=self.fit_to_window,
                 bg='#607D8B', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
        
        # Another separator
        tk.Frame(button_frame, bg='#ddd', width=2, height=30).pack(side=tk.LEFT, padx=10)
        
        # Performance controls
        perf_frame = tk.Frame(button_frame, bg='#f5f5f5')
        perf_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Button(perf_frame, text="🚀 Fast Zoom", command=self.toggle_fast_zoom,
                 bg='#4CAF50', fg='white', font=('Arial', 9), 
                 padx=8, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(perf_frame, text="🗑️ Clear Cache", command=self.clear_image_cache,
                 bg='#FF9800', fg='white', font=('Arial', 9), 
                 padx=8, pady=5).pack(side=tk.LEFT, padx=2)
        
        tk.Button(perf_frame, text="🔬 Analyze", command=self.analyze_performance,
                 bg='#2196F3', fg='white', font=('Arial', 9), 
                 padx=8, pady=5).pack(side=tk.LEFT, padx=2)
        
        # GPU indicator (if available)
        if HAS_OPENCV and hasattr(self, 'enable_gpu_acceleration'):
            gpu_text = "🚀 GPU" if self.enable_gpu_acceleration else "💻 CPU"
            tk.Label(perf_frame, text=gpu_text, bg='#f5f5f5', 
                    font=('Arial', 8), fg='#666').pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(button_frame, bg='#ddd', width=2, height=30).pack(side=tk.LEFT, padx=10)
        
        # Ruler controls at top right
        ruler_toolbar_frame = tk.Frame(button_frame, bg='#f5f5f5')
        ruler_toolbar_frame.pack(side=tk.LEFT, padx=5)
        
        # Ruler toggle button with proper icon
        self.ruler_show_var = tk.BooleanVar()
        self.ruler_button = tk.Checkbutton(ruler_toolbar_frame, text="📏 Ruler", 
                                         variable=self.ruler_show_var, command=self.toggle_show_ruler,
                                         font=('Arial', 9, 'bold'), bg='#E3F2FD', fg='#1976D2',
                                         selectcolor='#BBDEFB', relief='raised', bd=2,
                                         padx=8, pady=3, indicatoron=0)
        self.ruler_button.pack(side=tk.LEFT, padx=2)
        
        # Ruler measurement display in toolbar
        self.ruler_measurement_var = tk.StringVar(value="Ruler: Click & drag to measure")
        ruler_info_label = tk.Label(ruler_toolbar_frame, textvariable=self.ruler_measurement_var,
                                   font=('Arial', 9), bg='#f5f5f5', fg='#666', width=25)
        ruler_info_label.pack(side=tk.LEFT, padx=(5, 0))
        
    def create_tools_panel(self, parent):
        """Create a simple left tools panel with scrolling"""
        tools_container = tk.Frame(parent, bg='#f0f0f0', width=380, relief='solid', bd=1)
        tools_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tools_container.pack_propagate(False)
        
        # Simple header
        header = tk.Frame(tools_container, bg='#d0d0d0')
        header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(header, text="Tools", font=('Arial', 12, 'bold'),
                bg='#d0d0d0', fg='#333').pack(pady=8)
        
        # Create scrollable content area
        canvas_frame = tk.Frame(tools_container, bg='#f0f0f0')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas for scrolling
        tools_canvas = tk.Canvas(canvas_frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=tools_canvas.yview)
        scrollable_frame = tk.Frame(tools_canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: tools_canvas.configure(scrollregion=tools_canvas.bbox("all"))
        )
        
        tools_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        tools_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        tools_canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            tools_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        tools_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Now use scrollable_frame as content_frame
        content_frame = scrollable_frame
        
        # Add padding to content
        content_frame.configure(padx=10, pady=10)
        
        # === MODE SECTION ===
        mode_section = tk.LabelFrame(content_frame, text="🎯 Mode Selection", 
                                    font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                    padx=10, pady=10, relief='groove', bd=2)
        mode_section.pack(fill=tk.X, pady=(0, 15))
        
        self.mode_var = tk.StringVar(value="none")
        
        # Mode indicator with better styling
        self.mode_indicator = tk.Label(mode_section, 
                                      text="Mouse Mode - Navigate and interact", 
                                      font=('Arial', 9),
                                      bg='#607D8B', fg='white',
                                      padx=10, pady=5, relief='raised')
        self.mode_indicator.pack(fill=tk.X, pady=(0, 10))
        
        # Radio buttons in a frame
        radio_frame = tk.Frame(mode_section, bg='#f0f0f0')
        radio_frame.pack(fill=tk.X)
        
        tk.Radiobutton(radio_frame, text="🖱️ Mouse Mode", 
                      variable=self.mode_var, value="none",
                      command=self.change_mode,
                      font=('Arial', 9), bg='#f0f0f0', anchor='w').pack(fill=tk.X, pady=2)
        
        tk.Radiobutton(radio_frame, text="🖊️ Select Areas", 
                      variable=self.mode_var, value="select",
                      command=self.change_mode,
                      font=('Arial', 9), bg='#f0f0f0', anchor='w').pack(fill=tk.X, pady=2)
        
        tk.Radiobutton(radio_frame, text="🔄 Move Sections", 
                      variable=self.mode_var, value="move",
                      command=self.change_mode,
                      font=('Arial', 9), bg='#f0f0f0', anchor='w').pack(fill=tk.X, pady=2)
        
        # === DRAWING TOOLS SECTION ===
        drawing_section = tk.LabelFrame(content_frame, text="🎨 Drawing Tools", 
                                       font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                       padx=10, pady=10, relief='groove', bd=2)
        drawing_section.pack(fill=tk.X, pady=(0, 15))
        
        # Brush size with better layout
        brush_frame = tk.Frame(drawing_section, bg='#f0f0f0')
        brush_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(brush_frame, text="Brush Size:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(anchor=tk.W)
        
        brush_control_frame = tk.Frame(brush_frame, bg='#f0f0f0')
        brush_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.brush_scale = tk.Scale(brush_control_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                                   command=self.update_brush_size, bg='#f0f0f0', length=150)
        self.brush_scale.set(3)
        self.brush_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.brush_value_label = tk.Label(brush_control_frame, text="3px", 
                                         font=('Arial', 8), bg='#f0f0f0', fg='#666', width=4)
        self.brush_value_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Color selection with preview
        color_frame = tk.Frame(drawing_section, bg='#f0f0f0')
        color_frame.pack(fill=tk.X)
        
        tk.Label(color_frame, text="Selection Color:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(anchor=tk.W, pady=(0, 5))
        
        self.color_button = tk.Button(color_frame, bg=self.selected_color, 
                                     text="Choose Color", width=20, height=2,
                                     command=self.choose_color, relief='raised', bd=2)
        self.color_button.pack(fill=tk.X)
        
        # === PRECISION MOVEMENT SECTION ===
        movement_section = tk.LabelFrame(content_frame, text="📐 Precision Movement", 
                                        font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                        padx=10, pady=10, relief='groove', bd=2)
        movement_section.pack(fill=tk.X, pady=(0, 15))
        
        # Movement options with icons and better layout
        movement_options_frame = tk.Frame(movement_section, bg='#f0f0f0')
        movement_options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.snap_var = tk.BooleanVar()
        snap_check = tk.Checkbutton(movement_options_frame, text="🎯 Snap to Grid", 
                                   variable=self.snap_var, command=self.toggle_snap,
                                   font=('Arial', 9), bg='#f0f0f0', anchor='w')
        snap_check.pack(fill=tk.X, pady=2)
        
        self.grid_show_var = tk.BooleanVar(value=False)  # Default to off for cleaner interface
        grid_check = tk.Checkbutton(movement_options_frame, text="📋 Show Grid", 
                                   variable=self.grid_show_var, command=self.toggle_show_grid,
                                   font=('Arial', 9), bg='#f0f0f0', anchor='w')
        grid_check.pack(fill=tk.X, pady=2)
        
        self.precise_var = tk.BooleanVar()
        precise_check = tk.Checkbutton(movement_options_frame, text="🎯 Precise Mode (Sub-pixel)", 
                                      variable=self.precise_var, command=self.toggle_precise_mode,
                                      font=('Arial', 9), bg='#f0f0f0', anchor='w')
        precise_check.pack(fill=tk.X, pady=2)
        
        # Smooth movement option
        self.smooth_var = tk.BooleanVar(value=True)  # Enable by default
        smooth_check = tk.Checkbutton(movement_options_frame, text="🌊 Smooth Movement", 
                                     variable=self.smooth_var, command=self.toggle_smooth_movement,
                                     font=('Arial', 9), bg='#f0f0f0', anchor='w')
        smooth_check.pack(fill=tk.X, pady=2)
        
        # Grid size control with better styling
        grid_control_frame = tk.Frame(movement_section, bg='#f0f0f0')
        grid_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(grid_control_frame, text="Grid Size:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(anchor=tk.W)
        
        grid_size_frame = tk.Frame(grid_control_frame, bg='#f0f0f0')
        grid_size_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.grid_cm_var = tk.StringVar(value="1.0")
        grid_spinbox = tk.Spinbox(grid_size_frame, from_=0.1, to=5.0, increment=0.1,
                                 textvariable=self.grid_cm_var, width=8,
                                 command=self.update_grid_size_cm, font=('Arial', 9))
        grid_spinbox.pack(side=tk.LEFT)
        grid_spinbox.bind('<Return>', lambda e: self.update_grid_size_cm())
        
        tk.Label(grid_size_frame, text="cm", font=('Arial', 9), 
                bg='#f0f0f0').pack(side=tk.LEFT, padx=(2, 10))
        
        # DPI setting for accurate measurements
        dpi_frame = tk.Frame(grid_control_frame, bg='#f0f0f0')
        dpi_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(dpi_frame, text="Image DPI:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(side=tk.LEFT)
        
        self.dpi_var = tk.StringVar(value="300")
        dpi_spinbox = tk.Spinbox(dpi_frame, from_=1, to=50000, increment=1,
                                textvariable=self.dpi_var, width=8,
                                command=self.update_dpi, font=('Arial', 9))
        dpi_spinbox.pack(side=tk.LEFT, padx=(10, 5))
        dpi_spinbox.bind('<Return>', lambda e: self.update_dpi())
        
        # === VERTICAL LINES SECTION ===
        lines_section = tk.LabelFrame(content_frame, text="📏 Vertical Lines", 
                                     font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                     padx=10, pady=10, relief='groove', bd=2)
        lines_section.pack(fill=tk.X, pady=(0, 15))
        
        # Toggle lines with better styling
        lines_toggle_frame = tk.Frame(lines_section, bg='#f0f0f0')
        lines_toggle_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.lines_var = tk.BooleanVar()
        self.lines_count_label = None
        self.spacing_value_label = None
        self.spacing_var = None
        self.lines_scale = None
        self.confirm_lines_button = None
        self.unlock_lines_button = None
        
        lines_toggle = tk.Checkbutton(lines_toggle_frame, text="📐 Show Vertical Lines", 
                                     variable=self.lines_var, command=self.toggle_lines,
                                     font=('Arial', 9, 'bold'), bg='#f0f0f0', anchor='w')
        lines_toggle.pack(fill=tk.X)
        
        # Lines configuration frame
        lines_config_frame = tk.Frame(lines_section, bg='#f0f0f0')
        lines_config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Number of lines with value display
        lines_count_frame = tk.Frame(lines_config_frame, bg='#f0f0f0')
        lines_count_frame.pack(fill=tk.X, pady=(0, 8))
        
        lines_label_frame = tk.Frame(lines_count_frame, bg='#f0f0f0')
        lines_label_frame.pack(fill=tk.X)
        
        tk.Label(lines_label_frame, text="Number of Lines:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(side=tk.LEFT)
        
        self.lines_count_label = tk.Label(lines_label_frame, text="5", 
                                         font=('Arial', 9), bg='#e0e0e0', fg='#333', 
                                         width=3, relief='sunken')
        self.lines_count_label.pack(side=tk.RIGHT)
        
        self.lines_scale = tk.Scale(lines_count_frame, from_=2, to=20, orient=tk.HORIZONTAL,
                                   command=self.update_lines_count, bg='#f0f0f0',
                                   length=200, resolution=1)
        self.lines_scale.set(5)
        self.lines_scale.pack(fill=tk.X, pady=(5, 0))
        
        # Line spacing with more precision
        spacing_frame = tk.Frame(lines_config_frame, bg='#f0f0f0')
        spacing_frame.pack(fill=tk.X, pady=(0, 8))
        
        spacing_label_frame = tk.Frame(spacing_frame, bg='#f0f0f0')
        spacing_label_frame.pack(fill=tk.X)
        
        tk.Label(spacing_label_frame, text="Line Spacing:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(side=tk.LEFT)
        
        self.spacing_value_label = tk.Label(spacing_label_frame, text="5.0cm", 
                                           font=('Arial', 9), bg='#e0e0e0', fg='#333', 
                                           width=7, relief='sunken')
        self.spacing_value_label.pack(side=tk.RIGHT)
        
        spacing_control_frame = tk.Frame(spacing_frame, bg='#f0f0f0')
        spacing_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Cm-based spacing control
        self.spacing_var = tk.StringVar(value="5.0")
        spacing_spinbox = tk.Spinbox(spacing_control_frame, from_=0.5, to=50.0, increment=0.5,
                                    textvariable=self.spacing_var, width=8, format="%.1f",
                                    command=self.update_line_spacing, font=('Arial', 9))
        spacing_spinbox.pack(side=tk.LEFT)
        spacing_spinbox.bind('<Return>', lambda e: self.update_line_spacing())
        
        tk.Label(spacing_control_frame, text="cm spacing", font=('Arial', 9),
                bg='#f0f0f0', fg='#666').pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick spacing presets
        preset_frame = tk.Frame(lines_config_frame, bg='#f0f0f0')
        preset_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(preset_frame, text="Presets:", font=('Arial', 8, 'bold'),
                bg='#f0f0f0', fg='#666').pack(anchor=tk.W)
        
        preset_buttons_frame = tk.Frame(preset_frame, bg='#f0f0f0')
        preset_buttons_frame.pack(fill=tk.X, pady=(2, 0))
        
        presets = [("Tight", "1.0"), ("Normal", "3.0"), ("Wide", "5.0"), ("Very Wide", "10.0")]
        for text, value in presets:
            btn = tk.Button(preset_buttons_frame, text=text, 
                           command=lambda v=value: self.set_spacing_preset(v),
                           font=('Arial', 7), padx=5, pady=1,
                           bg='#e0e0e0', relief='raised', bd=1)
            btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Lines control buttons with better styling
        lines_buttons_frame = tk.Frame(lines_section, bg='#f0f0f0')
        lines_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.confirm_lines_button = tk.Button(lines_buttons_frame, text="✅ Confirm Lines", 
                                             command=self.confirm_lines,
                                             bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                                             padx=8, pady=3, relief='raised')
        self.confirm_lines_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        self.unlock_lines_button = tk.Button(lines_buttons_frame, text="🔓 Unlock", 
                                            command=self.unlock_lines,
                                            bg='#FF9800', fg='white', font=('Arial', 9, 'bold'),
                                            padx=8, pady=3, state='disabled', relief='raised')
        self.unlock_lines_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Additional line controls
        lines_extra_frame = tk.Frame(lines_section, bg='#f0f0f0')
        lines_extra_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Button(lines_extra_frame, text="↻ Reset Positions", command=self.reset_line_positions,
                 bg='#607D8B', fg='white', font=('Arial', 8, 'bold'),
                 padx=5, pady=2, relief='raised').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        tk.Button(lines_extra_frame, text="📐 Equal Spacing", command=self.reset_equal_spacing,
                 bg='#795548', fg='white', font=('Arial', 8, 'bold'),
                 padx=5, pady=2, relief='raised').pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Instructions for line dragging
        lines_help = tk.Label(lines_section, 
                             text="💡 Drag individual lines to reposition (when unlocked)",
                             font=('Arial', 8), bg='#f0f0f0', fg='#666',
                             wraplength=300, justify='center')
        lines_help.pack(pady=(5, 0))
        
        # === IMAGE SIZE SECTION ===
        size_section = tk.LabelFrame(content_frame, text="🖼️ Image Size", 
                                    font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                    padx=10, pady=10, relief='groove', bd=2)
        size_section.pack(fill=tk.X, pady=(0, 15))
        
        # Width and height controls in a grid
        size_grid_frame = tk.Frame(size_section, bg='#f0f0f0')
        size_grid_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Width control
        width_row = tk.Frame(size_grid_frame, bg='#f0f0f0')
        width_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(width_row, text="Width:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333', width=8, anchor='w').pack(side=tk.LEFT)
        
        self.width_var = tk.StringVar(value="100")
        width_spinbox = tk.Spinbox(width_row, from_=10, to=500, increment=10,
                                  textvariable=self.width_var, width=8,
                                  command=self.resize_image_to_fit, font=('Arial', 9))
        width_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        width_spinbox.bind('<Return>', lambda e: self.resize_image_to_fit())
        
        tk.Label(width_row, text="%", font=('Arial', 9),
                bg='#f0f0f0', fg='#666').pack(side=tk.LEFT)
        
        # Height control
        height_row = tk.Frame(size_grid_frame, bg='#f0f0f0')
        height_row.pack(fill=tk.X)
        
        tk.Label(height_row, text="Height:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333', width=8, anchor='w').pack(side=tk.LEFT)
        
        self.height_var = tk.StringVar(value="100")
        height_spinbox = tk.Spinbox(height_row, from_=10, to=500, increment=10,
                                   textvariable=self.height_var, width=8,
                                   command=self.resize_image_to_fit, font=('Arial', 9))
        height_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        height_spinbox.bind('<Return>', lambda e: self.resize_image_to_fit())
        
        tk.Label(height_row, text="%", font=('Arial', 9),
                bg='#f0f0f0', fg='#666').pack(side=tk.LEFT)
        
        # Quick resize buttons
        resize_buttons_frame = tk.Frame(size_section, bg='#f0f0f0')
        resize_buttons_frame.pack(fill=tk.X)
        
        tk.Button(resize_buttons_frame, text="📐 Fit Lines", command=self.fit_image_to_lines,
                 bg='#2196F3', fg='white', font=('Arial', 8, 'bold'),
                 padx=5, pady=2, relief='raised').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        tk.Button(resize_buttons_frame, text="🔄 Reset Size", command=self.reset_image_size,
                 bg='#607D8B', fg='white', font=('Arial', 8, 'bold'),
                 padx=5, pady=2, relief='raised').pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # === ACTION BUTTONS SECTION ===
        actions_section = tk.LabelFrame(content_frame, text="⚡ Actions", 
                                       font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                       padx=10, pady=10, relief='groove', bd=2)
        actions_section.pack(fill=tk.X, pady=(0, 15))
        
        # Action buttons with better styling
        tk.Button(actions_section, text="🗑️ Clear All Selections", command=self.clear_selections,
                 bg='#f44336', fg='white', font=('Arial', 9, 'bold'),
                 padx=10, pady=5, relief='raised').pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(actions_section, text="↶ Undo Last Selection", command=self.undo_last_selection,
                 bg='#FF9800', fg='white', font=('Arial', 9, 'bold'),
                 padx=10, pady=5, relief='raised').pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(actions_section, text="🔄 Reset Image", command=self.reset_image,
                 bg='#607D8B', fg='white', font=('Arial', 9, 'bold'),
                 padx=10, pady=5, relief='raised').pack(fill=tk.X)
        
        # === PERFORMANCE SECTION ===
        perf_section = tk.LabelFrame(content_frame, text="🚀 Performance", 
                                    font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                    padx=10, pady=10, relief='groove', bd=2)
        perf_section.pack(fill=tk.X, pady=(0, 15))
        
        # Performance mode toggle
        perf_mode_frame = tk.Frame(perf_section, bg='#f0f0f0')
        perf_mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.fast_zoom_var = tk.BooleanVar(value=self.enable_fast_zoom)
        fast_zoom_check = tk.Checkbutton(perf_mode_frame, text="🚀 Fast Zoom Mode", 
                                        variable=self.fast_zoom_var, command=self.toggle_fast_zoom_ui,
                                        font=('Arial', 9, 'bold'), bg='#f0f0f0', anchor='w')
        fast_zoom_check.pack(fill=tk.X, pady=2)
        
        # Memory info
        memory_frame = tk.Frame(perf_section, bg='#f0f0f0')
        memory_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(memory_frame, text="Cache Memory:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#333').pack(anchor=tk.W)
        
        self.memory_label = tk.Label(memory_frame, text="0.0 MB", 
                                    font=('Arial', 9), bg='#e0e0e0', fg='#333', 
                                    relief='sunken', anchor='w', padx=5)
        self.memory_label.pack(fill=tk.X, pady=(2, 0))
        
        # Performance buttons
        perf_buttons_frame = tk.Frame(perf_section, bg='#f0f0f0')
        perf_buttons_frame.pack(fill=tk.X)
        
        tk.Button(perf_buttons_frame, text="🗑️ Clear Cache", command=self.clear_image_cache,
                 bg='#FF9800', fg='white', font=('Arial', 9, 'bold'),
                 padx=8, pady=3, relief='raised').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        tk.Button(perf_buttons_frame, text="📊 Update Stats", command=self.update_memory_display,
                 bg='#2196F3', fg='white', font=('Arial', 9, 'bold'),
                 padx=8, pady=3, relief='raised').pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # === HELP SECTION ===
        help_section = tk.LabelFrame(content_frame, text="ℹ️ Keyboard Shortcuts", 
                                    font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                    padx=10, pady=10, relief='groove', bd=2)
        help_section.pack(fill=tk.X, pady=(0, 20))
        
        help_text_frame = tk.Frame(help_section, bg='#f0f0f0')
        help_text_frame.pack(fill=tk.X)
        
        shortcuts = [
            ("🖱️ Mouse Wheel", "Zoom in/out at cursor"),
            ("WASD / Arrow Keys", "Navigate image view"),
            ("Shift + Navigation", "Pan faster"),
            ("⬅️➡️⬆️⬇️ (Move mode)", "Move selected section"),
            ("Shift + Arrows", "Move section faster"),
            ("In Precise Mode", "Sub-pixel movement"),
            ("Click on image", "to enable navigation"),
            ("Click on UI", "to disable navigation")
        ]
        
        for shortcut, description in shortcuts:
            shortcut_row = tk.Frame(help_text_frame, bg='#f0f0f0')
            shortcut_row.pack(fill=tk.X, pady=1)
            
            tk.Label(shortcut_row, text=shortcut, font=('Arial', 8, 'bold'),
                    bg='#f0f0f0', fg='#333', width=15, anchor='w').pack(side=tk.LEFT)
            
            tk.Label(shortcut_row, text=description, font=('Arial', 8),
                    bg='#f0f0f0', fg='#666').pack(side=tk.LEFT, padx=(5, 0))
        
    def create_canvas(self, parent):
        """Create a simple main canvas for image display"""
        canvas_container = tk.Frame(parent, bg='#f0f0f0', relief='solid', bd=1)
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Simple header
        header = tk.Frame(canvas_container, bg='#d0d0d0')
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Image", font=('Arial', 12, 'bold'),
                bg='#d0d0d0', fg='#333').pack(pady=10)
        
        # Canvas area
        canvas_area = tk.Frame(canvas_container, bg='white')
        canvas_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_area, 
                               bg='white',
                               width=self.canvas_width, 
                               height=self.canvas_height)
        
        # Simple scrollbars
        v_scrollbar = tk.Scrollbar(canvas_area, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = tk.Scrollbar(canvas_area, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        
        # Bind mouse wheel for zooming
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)    # Linux scroll down
        
        # Bind keyboard events for precise movement - use both canvas and root for better focus
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyPress>", self.on_key_press)
        
        # Make canvas focusable and set initial focus
        self.canvas.config(takefocus=True)
        self.canvas.focus_set()
        
        # Bind focus events to maintain keyboard control
        self.canvas.bind("<FocusIn>", self.on_canvas_focus_in)
        self.canvas.bind("<FocusOut>", self.on_canvas_focus_out)
        
        # Only mouse enter canvas sets focus, not any click
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())  # Mouse enter canvas
        
    def on_canvas_click(self, event):
        """Set focus to canvas when clicked to enable keyboard shortcuts"""
        self.canvas.focus_set()
        print("Canvas clicked - focus set")
        # Call the original mouse down handler
        self.on_mouse_down(event)
    
    def on_canvas_focus_in(self, event):
        """Handle canvas gaining focus"""
        print("Canvas gained focus - keyboard navigation enabled")
        if hasattr(self, 'original_image') and self.original_image:
            self.update_status("✅ Keyboard navigation ENABLED • Use WASD/arrows to navigate, mouse wheel to zoom • Click on UI to disable")
    
    def on_canvas_focus_out(self, event):
        """Handle canvas losing focus"""
        print("Canvas lost focus - keyboard navigation disabled")
        if hasattr(self, 'original_image') and self.original_image:
            self.update_status("❌ Keyboard navigation DISABLED • Click on image to re-enable navigation")
        
    def create_sections_panel(self, parent):
        """Create a simple right sections panel"""
        sections_container = tk.Frame(parent, bg='#f0f0f0', width=350, relief='solid', bd=1)
        sections_container.pack(side=tk.RIGHT, fill=tk.Y)
        sections_container.pack_propagate(False)
        
        # Simple header
        header = tk.Frame(sections_container, bg='#d0d0d0')
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Sections", font=('Arial', 12, 'bold'),
                bg='#d0d0d0', fg='#333').pack(pady=10)
        
        content_frame = tk.Frame(sections_container, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Sections counter
        self.sections_count_label = tk.Label(content_frame,
                                            text="Total: 0",
                                            font=('Arial', 10),
                                            bg='#f0f0f0',
                                            fg='#333')
        self.sections_count_label.pack(pady=(0, 10))
        
        # Simple sections list
        self.sections_listbox = tk.Listbox(content_frame,
                                          font=('Arial', 9),
                                          bg='white',
                                          height=12)  # Reduced height to make room for gamepad
        self.sections_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # === PRECISION MOVEMENT GAMEPAD ===
        gamepad_frame = tk.LabelFrame(content_frame, text="🎮 Move Selected Section", 
                                     font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#2c5282',
                                     padx=8, pady=8, relief='groove', bd=2)
        gamepad_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Selected section info at top
        self.selected_info_var = tk.StringVar(value="No section selected")
        selected_info_label = tk.Label(gamepad_frame, textvariable=self.selected_info_var,
                                     font=('Arial', 9, 'bold'), bg='#f0f0f0', fg='#333')
        selected_info_label.pack(pady=(0, 8))
        
        # Step size controls
        step_frame = tk.Frame(gamepad_frame, bg='#f0f0f0')
        step_frame.pack(pady=(0, 8))
        
        tk.Label(step_frame, text="Step:", font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.movement_step_var = tk.StringVar(value="1")
        step_entry = tk.Entry(step_frame, textvariable=self.movement_step_var, 
                             width=6, font=('Arial', 9))
        step_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        tk.Label(step_frame, text="cm", font=('Arial', 9, 'bold'), bg='#f0f0f0', fg='#2c5282').pack(side=tk.LEFT)
        
        # Gamepad-style arrow buttons
        arrows_container = tk.Frame(gamepad_frame, bg='#f0f0f0')
        arrows_container.pack()
        
        # Top row - Up arrow
        up_frame = tk.Frame(arrows_container, bg='#f0f0f0')
        up_frame.pack()
        
        up_button = tk.Button(up_frame, text="▲", command=lambda: self.move_selected_section(0, -1),
                             font=('Arial', 14, 'bold'), bg='#4CAF50', fg='white', 
                             width=3, height=1, relief='raised', bd=2)
        up_button.pack()
        
        # Middle row - Left, Info, Right
        middle_frame = tk.Frame(arrows_container, bg='#f0f0f0')
        middle_frame.pack(pady=3)
        
        left_button = tk.Button(middle_frame, text="◄", command=lambda: self.move_selected_section(-1, 0),
                               font=('Arial', 14, 'bold'), bg='#4CAF50', fg='white',
                               width=3, height=1, relief='raised', bd=2)
        left_button.pack(side=tk.LEFT)
        
        # Center info
        center_info = tk.Label(middle_frame, text="Move", font=('Arial', 8),
                             bg='#f0f0f0', fg='#666')
        center_info.pack(side=tk.LEFT, padx=8)
        
        right_button = tk.Button(middle_frame, text="►", command=lambda: self.move_selected_section(1, 0),
                                font=('Arial', 14, 'bold'), bg='#4CAF50', fg='white',
                                width=3, height=1, relief='raised', bd=2)
        right_button.pack(side=tk.LEFT)
        
        # Bottom row - Down arrow
        down_frame = tk.Frame(arrows_container, bg='#f0f0f0')
        down_frame.pack()
        
        down_button = tk.Button(down_frame, text="▼", command=lambda: self.move_selected_section(0, 1),
                               font=('Arial', 14, 'bold'), bg='#4CAF50', fg='white',
                               width=3, height=1, relief='raised', bd=2)
        down_button.pack()
        
        # Keyboard shortcut hint
        hint_label = tk.Label(gamepad_frame, text="💡 Use arrow keys or buttons above",
                             font=('Arial', 8), bg='#f0f0f0', fg='#888')
        hint_label.pack(pady=(8, 0))
        
        # Simple action buttons
        tk.Button(content_frame, text="Change Color", 
                 command=self.change_section_color,
                 bg='#4CAF50', fg='white', font=('Arial', 9),
                 width=25, pady=3).pack(pady=2)
        
        tk.Button(content_frame, text="Delete Selected", 
                 command=self.delete_selected_section,
                 bg='#f44336', fg='white', font=('Arial', 9),
                 width=25, pady=3).pack(pady=2)
        
        tk.Button(content_frame, text="Delete All", 
                 command=self.delete_all_sections,
                 bg='#f44336', fg='white', font=('Arial', 9),
                 width=25, pady=3).pack(pady=2)
        
        # Bind listbox selection
        self.sections_listbox.bind('<<ListboxSelect>>', self.on_section_select)
    
    def duplicate_section(self):
        """Duplicate the selected section"""
        selection = self.sections_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(self.clipped_sections):
                original_section = self.clipped_sections[idx]
                # Create a copy with slight offset
                new_section = original_section.copy()
                old_x, old_y = new_section['position']
                new_section['position'] = (old_x + 20, old_y + 20)  # Offset by 20 pixels
                new_section['id'] = len(self.clipped_sections)
                self.clipped_sections.append(new_section)
                self.update_sections_list()
                self.display_image()
                self.update_status("Section duplicated successfully")
    
    def delete_all_sections(self):
        """Delete all sections with confirmation"""
        if self.clipped_sections:
            result = messagebox.askyesno("Delete All Sections", 
                                       "Are you sure you want to delete all sections? This cannot be undone.")
            if result:
                self.clear_selections()
                self.update_status("All sections deleted")
        
    def load_image(self):
        """Load a TIFF image with no size restrictions"""
        # macOS fix: add parent parameter and handle file type differently
        if self.is_macos:
            # macOS file dialog needs explicit parent and different filetypes format
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
        
        if file_path:
            try:
                self.update_status("Loading image (no size limits)...")
                
                # Temporarily disable PIL warnings and limits
                original_max_pixels = Image.MAX_IMAGE_PIXELS
                Image.MAX_IMAGE_PIXELS = None
                
                # Load with PIL for TIFF support
                self.original_image = Image.open(file_path)
                
                # Get image info for user feedback
                width, height = self.original_image.size
                megapixels = (width * height) / 1_000_000
                self.update_status(f"Loading large image: {width}×{height} ({megapixels:.1f}MP)...")
                
                # Extract DPI from image metadata
                self._extract_and_set_dpi(file_path)
                
                # Convert to RGB if needed (this might take time for very large images)
                if self.original_image.mode != 'RGB':
                    self.update_status(f"Converting to RGB format...")
                    self.original_image = self.original_image.convert('RGB')
                
                # Create working copy
                self.working_image = self.original_image.copy()
                
                # Clear existing selections
                self.current_selections = []
                self.clipped_sections = []
                self.update_sections_list()
                
                # Reset merge state
                self.is_merged_image = False
                
                # Reset image controls
                self.width_var.set("100")
                self.height_var.set("100")
                self.image_scale = 1.0
                
                # Update image info with large file details
                width, height = self.original_image.size
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                megapixels = (width * height) / 1_000_000
                
                self.update_image_info(f"{os.path.basename(file_path)} • {width:,}×{height:,} • {megapixels:.1f}MP • {file_size:.1f}MB")
                
                # Update canvas info
                if hasattr(self, 'canvas_info_label'):
                    self.canvas_info_label.config(text=f"Large image loaded: {width:,}×{height:,} pixels ({megapixels:.1f}MP) • Use mouse wheel to zoom")
                
                # Display image with performance optimizations
                self.update_status(f"🚀 Initializing performance optimizations...")
                
                # Initialize performance optimizations after UI is ready
                def init_optimizations():
                    self.fit_to_window()
                    self.optimize_image_loading()
                
                self.root.after(100, init_optimizations)
                
                # Reset window title with performance mode
                mode_text = "🚀 OPTIMIZED" if self.enable_fast_zoom else "🐌 LEGACY"
                self.root.title(f"📸 Advanced TIFF Editor - {mode_text} - No Size Limits")
                
                # Enhanced status message with size categorization
                size_category = "🔥 MASSIVE" if megapixels > 100 else "📏 LARGE" if megapixels > 25 else "📷 NORMAL"
                self.update_status(f"✅ {size_category} image loaded: {width:,}×{height:,} ({megapixels:.1f}MP) • Mouse wheel to zoom")
                
                # Restore original limit setting (though we set it to None anyway)
                Image.MAX_IMAGE_PIXELS = original_max_pixels
                
            except Exception as e:
                # Restore original limit setting on error
                Image.MAX_IMAGE_PIXELS = original_max_pixels
                self.update_status("Failed to load image")
                error_msg = str(e)
                # Provide more helpful error messages
                if "exceeds limit" in error_msg.lower():
                    error_msg = f"Image size limit error bypassed, but still failed: {error_msg}\n\nTry closing other applications to free up memory."
                elif "memory" in error_msg.lower():
                    error_msg = f"Memory error: {error_msg}\n\nThis image might be too large for available RAM."
                messagebox.showerror("Error", f"Failed to load image: {error_msg}")
    
    def _extract_and_set_dpi(self, file_path):
        """Extract DPI from image metadata and update the UI - NO LIMITS!"""
        try:
            extracted_dpi = None
            dpi_source = "not found"
            
            # Method 1: Try to get DPI from PIL image info
            dpi_info = self.original_image.info.get('dpi', None)
            if dpi_info:
                if isinstance(dpi_info, (list, tuple)) and len(dpi_info) >= 2:
                    # Use the first DPI value (x_dpi) - accept ANY value, even 1
                    extracted_dpi = int(dpi_info[0]) if dpi_info[0] > 0 else int(dpi_info[1])
                    dpi_source = f"PIL dpi field: {dpi_info}"
                elif isinstance(dpi_info, (int, float)) and dpi_info > 0:
                    extracted_dpi = int(dpi_info)
                    dpi_source = f"PIL dpi field: {dpi_info}"
            
            # Method 2: Try resolution field if no DPI found
            if not extracted_dpi:
                resolution_info = self.original_image.info.get('resolution', None)
                if resolution_info and isinstance(resolution_info, (list, tuple)) and len(resolution_info) >= 2:
                    if resolution_info[0] > 0:
                        extracted_dpi = int(resolution_info[0])
                        dpi_source = f"PIL resolution field: {resolution_info}"
            
            # Method 3: Try EXIF data if available
            if not extracted_dpi and hasattr(self.original_image, '_getexif'):
                try:
                    exif = self.original_image._getexif()
                    if exif:
                        # EXIF tag 282 is XResolution, 283 is YResolution
                        x_resolution = exif.get(282)  # XResolution
                        if x_resolution:
                            if isinstance(x_resolution, (list, tuple)) and len(x_resolution) >= 2:
                                # Resolution is often stored as (numerator, denominator)
                                if x_resolution[1] != 0:
                                    extracted_dpi = int(x_resolution[0] / x_resolution[1])
                                    dpi_source = f"EXIF XResolution: {x_resolution}"
                            elif isinstance(x_resolution, (int, float)) and x_resolution > 0:
                                extracted_dpi = int(x_resolution)
                                dpi_source = f"EXIF XResolution: {x_resolution}"
                except Exception as e:
                    pass  # EXIF parsing failed, continue
            
            # Method 4: Check for other common metadata fields
            if not extracted_dpi:
                # Try other common fields that might contain resolution info
                for field_name in ['jfif_density', 'density', 'x_resolution', 'y_resolution']:
                    field_value = self.original_image.info.get(field_name, None)
                    if field_value and isinstance(field_value, (int, float, list, tuple)):
                        if isinstance(field_value, (list, tuple)) and len(field_value) > 0:
                            field_value = field_value[0]
                        if isinstance(field_value, (int, float)) and field_value > 0:
                            extracted_dpi = int(field_value)
                            dpi_source = f"metadata field '{field_name}': {field_value}"
                            break
            
            # If we found a DPI value, update the UI
            if extracted_dpi and extracted_dpi > 0:
                # Accept ANY positive DPI value - no limits!
                # Even very low DPI values (like 1) or very high ones (like 10000) can be valid
                old_dpi = self.image_dpi
                self.image_dpi = extracted_dpi
                self.dpi_var.set(str(extracted_dpi))
                
                # Provide more informative status messages
                if extracted_dpi < 72:
                    self.update_status(f"Image DPI auto-detected: {extracted_dpi} (low resolution - was {old_dpi})")
                elif extracted_dpi > 1200:
                    self.update_status(f"Image DPI auto-detected: {extracted_dpi} (very high resolution - was {old_dpi})")
                else:
                    pass
                    pass
                    pass  # Placeholder for else block
                    pass  # Placeholder to avoid syntax error
                    self.update_status(f"Image DPI auto-detected: {extracted_dpi} (was {old_dpi})")
                
                # Refresh all DPI-dependent elements after a short delay
                def refresh_dpi_elements():
                    # Refresh the display for updated cm measurements
                    if self.show_grid:
                        self.display_image()
                    
                    # Update ruler measurement if ruler is active
                    if self.show_ruler and self.ruler_start and self.ruler_end:
                        _, real_pixels, cm_distance = self.calculate_distance(
                            self.ruler_start[0], self.ruler_start[1],
                            self.ruler_end[0], self.ruler_end[1]
                        )
                        measurement_text = f"Distance: {real_pixels:.1f} px ({cm_distance:.2f} cm)"
                        self.ruler_measurement_var.set(measurement_text)
                
                self.root.after(200, refresh_dpi_elements)
            else:
                # No DPI found in metadata
                filename = os.path.basename(file_path)
                
                # Show all metadata for debugging
                available_fields = list(self.original_image.info.keys())
                self.update_status(f"No DPI in {filename} metadata (available: {available_fields}), using default {self.image_dpi} DPI")
                
        except Exception as e:
            # If anything goes wrong, just use default DPI
            filename = os.path.basename(file_path) if file_path else "image"
            self.update_status(f"Could not read DPI from {filename} (error: {str(e)[:100]}), using default {self.image_dpi} DPI")
                
    def display_image(self):
        """🚀 HIGH-PERFORMANCE Display with viewport culling and smart caching"""
        if self.original_image is None:
            return
        
        if self.enable_fast_zoom:
            self._display_image_optimized()
        else:
            self._display_image_legacy()
    
    def _display_image_optimized(self):
        """🚀 Advanced optimized display with GPU acceleration and smart caching"""
        try:
            start_time = time.perf_counter()
            
            # Get viewport information with better precision
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate what's actually visible with sub-pixel precision
            scroll_x = self.canvas.canvasx(0)
            scroll_y = self.canvas.canvasy(0)
            visible_width = min(canvas_width, self.canvas.winfo_reqwidth())
            visible_height = min(canvas_height, self.canvas.winfo_reqheight())
            
            # Enhanced viewport key with image hash for cache validation
            image_hash = getattr(self.original_image, '_cache_hash', None)
            if not image_hash:
                # Create lightweight hash for cache validation
                image_hash = hashlib.md5(f"{id(self.original_image)}_{self.original_image.size}".encode()).hexdigest()[:8]
                self.original_image._cache_hash = image_hash
            
            viewport_key = f"{image_hash}_{self.image_scale:.4f}_{scroll_x:.0f}_{scroll_y:.0f}_{visible_width}x{visible_height}"
            
            # Check cache with LRU management
            if viewport_key in self.display_cache:
                # Move to end for LRU
                cache_entry = self.display_cache.pop(viewport_key)
                self.display_cache[viewport_key] = cache_entry
                
                self.photo_image = cache_entry['photo']
                display_width = cache_entry['width']
                display_height = cache_entry['height']
                
                self.cache_hit_count += 1
                render_time = (time.perf_counter() - start_time) * 1000
                self.update_status(f"⚡ Cache hit: {render_time:.1f}ms (saved ~{cache_entry.get('estimated_render_time', 0):.0f}ms)")
            else:
                self.cache_miss_count += 1
                # Calculate optimal pyramid level
                optimal_level = self._get_optimal_pyramid_level()
                
                # Get or create pyramid level
                pyramid_img = self._get_pyramid_level(optimal_level)
                
                # Calculate display dimensions with sub-pixel precision
                orig_width, orig_height = self.original_image.size
                display_width = max(1, min(int(orig_width * self.image_scale), 32000))
                display_height = max(1, min(int(orig_height * self.image_scale), 32000))
                
                # Check for viewport optimization opportunity
                # Check if image is too large for direct rendering
                total_pixels = display_width * display_height
                if total_pixels > self.max_display_pixels:
                    # Use simplified rendering for massive images
                    display_img = pyramid_img.resize((display_width, display_height), Image.Resampling.LANCZOS)
                    self.update_status(f"🔍 Large image optimization: {display_width}x{display_height}")
                else:
                    # Standard rendering for manageable sizes
                    pyramid_scale = optimal_level
                    pyramid_display_scale = self.image_scale / pyramid_scale
                    
                    if abs(pyramid_display_scale - 1.0) > 0.01:
                        new_width = int(pyramid_img.size[0] * pyramid_display_scale)
                        new_height = int(pyramid_img.size[1] * pyramid_display_scale)
                        new_width = max(1, min(new_width, 32000))
                        new_height = max(1, min(new_height, 32000))
                        display_img = pyramid_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        display_img = pyramid_img
                
                # Convert to PhotoImage
                self.photo_image = ImageTk.PhotoImage(display_img)
                
                # Cache the result (with size limit)
                self._cache_display_result(viewport_key, self.photo_image, display_width, display_height)
                
                render_time = (time.time() - start_time) * 1000
                pyramid_info = f"pyramid {optimal_level:.2f}x" if optimal_level != 1.0 else "full res"
                self.update_status(f"⚡ Rendered {display_width}x{display_height} ({pyramid_info}) in {render_time:.1f}ms")
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
            
            # Update scroll region
            self.canvas.configure(scrollregion=(0, 0, display_width, display_height))
            
            # Redraw overlays immediately to ensure they're always visible
            if self.current_selections:
                self.redraw_selections()
            if self.clipped_sections:
                self.draw_clipped_sections()
            if self.show_lines:
                self.draw_vertical_lines()
            if self.show_grid:
                self.draw_grid()
            if self.show_ruler:
                self.draw_ruler()
            
        except Exception as e:
            print(f"Error in optimized display: {e}")
            # Fallback to legacy mode
            self._display_image_legacy()
    
    def _display_image_legacy(self):
        """Original display method - kept as fallback"""
        try:
            # Calculate display size
            orig_width, orig_height = self.original_image.size
            display_width = int(orig_width * self.image_scale)
            display_height = int(orig_height * self.image_scale)
            
            # Ensure minimum size
            display_width = max(display_width, 1)
            display_height = max(display_height, 1)
            
            # Resize image for display
            display_img = self.working_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(display_img)
            
            # Clear canvas and display image
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Redraw overlays
            print(f"DEBUG: display_image calling redraw_selections")
            self.redraw_selections()
            print(f"DEBUG: display_image calling draw_clipped_sections")
            self.draw_clipped_sections()
            
            print(f"DEBUG: display_image - show_lines: {self.show_lines}")
            if self.show_lines:
                print(f"DEBUG: display_image - scheduling draw_vertical_lines")
                self.root.after(10, self.draw_vertical_lines)
            else:
                print(f"DEBUG: display_image - NOT drawing vertical lines (show_lines=False)")
            if self.show_grid:
                self.root.after(15, self.draw_grid)
            if self.show_ruler:
                self.root.after(20, self.draw_ruler)
            
        except Exception as e:
            print(f"Error in legacy display: {e}")
            messagebox.showerror("Display Error", f"Failed to display image: {str(e)}")
    
    # 🚀 OPTIMIZATION SUPPORT METHODS
    
    def _get_optimal_pyramid_level(self):
        """Determine the best pyramid level for current zoom"""
        if self.image_scale >= 1.0:
            return 1.0  # Use full resolution for zoom in
        elif self.image_scale >= 0.5:
            return 0.5
        elif self.image_scale >= 0.25:
            return 0.25
        elif self.image_scale >= 0.1:
            return 0.1
        else:
            return 0.05
    
    def _get_pyramid_level(self, level):
        """Get or create a pyramid level"""
        if level not in self.image_pyramid:
            self._create_pyramid_level(level)
        return self.image_pyramid[level]
    
    def _create_pyramid_level(self, level):
        """Create a specific pyramid level"""
        try:
            if level == 1.0:
                # Full resolution - use working image
                self.image_pyramid[level] = self.working_image.copy()
            else:
                # Downscaled version
                orig_width, orig_height = self.original_image.size
                new_width = max(1, int(orig_width * level))
                new_height = max(1, int(orig_height * level))
                
                # Use high-quality resampling for pyramid levels
                self.image_pyramid[level] = self.working_image.resize(
                    (new_width, new_height), 
                    Image.Resampling.LANCZOS
                )
                
            print(f"Created pyramid level {level}: {self.image_pyramid[level].size}")
            
        except Exception as e:
            print(f"Error creating pyramid level {level}: {e}")
            # Fallback to working image
            self.image_pyramid[level] = self.working_image.copy()
    
    def _render_viewport_only(self, source_img, scroll_x, scroll_y, visible_width, visible_height):
        """Render only the visible viewport for massive images"""
        try:
            # Calculate the region of the source image that's visible
            source_width, source_height = source_img.size
            
            # Convert scroll coordinates to source image coordinates
            scale_factor = source_width / (self.original_image.size[0] * self.image_scale)
            
            source_x = int(scroll_x * scale_factor)
            source_y = int(scroll_y * scale_factor)
            source_right = min(source_width, int((scroll_x + visible_width) * scale_factor))
            source_bottom = min(source_height, int((scroll_y + visible_height) * scale_factor))
            
            # Ensure valid crop region
            source_x = max(0, source_x)
            source_y = max(0, source_y)
            crop_width = source_right - source_x
            crop_height = source_bottom - source_y
            
            if crop_width <= 0 or crop_height <= 0:
                # Return a small fallback image
                return Image.new('RGB', (visible_width, visible_height), 'white')
            
            # Crop the visible region
            viewport_img = source_img.crop((source_x, source_y, source_right, source_bottom))
            
            # Resize to visible dimensions
            if viewport_img.size != (visible_width, visible_height):
                viewport_img = viewport_img.resize((visible_width, visible_height), Image.Resampling.LANCZOS)
            
            return viewport_img
            
        except Exception as e:
            print(f"Error in viewport rendering: {e}")
            # Return fallback
            return Image.new('RGB', (visible_width, visible_height), 'lightgray')
    
    def _cache_display_result(self, key, photo_image, width, height):
        """Cache display result with size management"""
        # Remove old entries if cache is full
        if len(self.display_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.display_cache))
            del self.display_cache[oldest_key]
        
        self.display_cache[key] = {
            'photo': photo_image,
            'width': width,
            'height': height,
            'timestamp': time.time()
        }
    
    def _schedule_overlay_rendering(self):
        """Efficiently schedule overlay rendering"""
        # Use a single delayed call to render all overlays
        if hasattr(self, '_overlay_scheduled'):
            return  # Already scheduled
        
        self._overlay_scheduled = True
        
        def render_overlays():
            try:
                self.redraw_selections()
                self.draw_clipped_sections()
                
                if self.show_lines:
                    self.draw_vertical_lines()
                if self.show_grid:
                    self.draw_grid()
                if self.show_ruler:
                    self.draw_ruler()
            finally:
                if hasattr(self, '_overlay_scheduled'):
                    delattr(self, '_overlay_scheduled')
        
        # Schedule after a short delay to batch overlay updates
        self.root.after(25, render_overlays)
    
    def clear_image_cache(self):
        """Clear all image caches to free memory"""
        self.image_pyramid.clear()
        self.display_cache.clear()
        if self.auto_garbage_collect:
            gc.collect()
        self.update_status("🗑️ Image cache cleared - memory freed")
    
    def get_memory_usage_mb(self):
        """Estimate current memory usage"""
        total_mb = 0
        
        # Calculate pyramid cache size
        for level, img in self.image_pyramid.items():
            width, height = img.size
            # Estimate: 3 bytes per pixel (RGB) + overhead
            mb = (width * height * 3) / (1024 * 1024)
            total_mb += mb
        
        # Add display cache
        total_mb += len(self.display_cache) * 5  # Rough estimate
        
        return total_mb
    
    def toggle_fast_zoom(self):
        """Toggle between optimized and legacy zoom modes"""
        self.enable_fast_zoom = not self.enable_fast_zoom
        mode = "OPTIMIZED 🚀" if self.enable_fast_zoom else "LEGACY 🐌"
        self.update_status(f"Zoom mode: {mode}")
        self.display_image()  # Refresh with new mode
    
    def toggle_fast_zoom_ui(self):
        """Toggle fast zoom from UI checkbox"""
        self.enable_fast_zoom = self.fast_zoom_var.get()
        self.toggle_fast_zoom()
        # Update checkbox to match internal state
        self.fast_zoom_var.set(self.enable_fast_zoom)
    
    def toggle_gpu_acceleration(self):
        """Toggle GPU acceleration on/off"""
        if hasattr(self, 'gpu_var'):
            self.enable_gpu_acceleration = self.gpu_var.get()
            if self.enable_gpu_acceleration and not HAS_OPENCV:
                self.enable_gpu_acceleration = False
                self.gpu_var.set(False)
                messagebox.showwarning("GPU Acceleration", "OpenCV not available. GPU acceleration disabled.")
            
            mode = "🚀 GPU ENABLED" if self.enable_gpu_acceleration else "💻 CPU ONLY"
            self.update_status(f"Processing mode: {mode}")
            
            # Clear cache to force regeneration with new method
            self.clear_image_cache()
    
    def toggle_profiling(self):
        """Toggle performance profiling on/off"""
        if hasattr(self, 'profiling_var'):
            self.enable_profiling = self.profiling_var.get()
            mode = "📊 PROFILING ON" if self.enable_profiling else "📊 PROFILING OFF"
            self.update_status(f"Performance profiling: {mode}")
            
            if self.enable_profiling:
                print("🔬 Performance profiling enabled - operations will be timed")
            else:
                # Show profiling summary if available
                if self.performance_stats['render_times']:
                    recent_times = [op['duration_ms'] for op in self.performance_stats['render_times'][-10:]]
                    avg_time = sum(recent_times) / len(recent_times)
                    print(f"📈 Recent average render time: {avg_time:.1f}ms")
    
    def update_memory_display(self):
        """Update memory usage display"""
        try:
            memory_mb = self.get_memory_usage_mb()
            pyramid_count = len(self.image_pyramid)
            cache_count = len(self.display_cache)
            
            memory_text = f"{memory_mb:.1f} MB ({pyramid_count}P + {cache_count}C)"
            self.memory_label.config(text=memory_text)
            
            # Color code based on usage
            if memory_mb > self.memory_limit_mb * 0.8:  # > 80% of limit
                self.memory_label.config(fg='red')
            elif memory_mb > self.memory_limit_mb * 0.5:  # > 50% of limit
                self.memory_label.config(fg='orange')
            else:
                self.memory_label.config(fg='green')
                
            self.update_status(f"📊 Memory: {memory_mb:.1f}MB • Pyramid levels: {pyramid_count} • Display cache: {cache_count}")
            
        except Exception as e:
            self.memory_label.config(text="Error", fg='red')
            print(f"Error updating memory display: {e}")
    
    def optimize_image_loading(self):
        """Optimize image loading for better performance"""
        if self.original_image is None:
            return
            
        try:
            # Clear old caches
            self.image_pyramid.clear()
            self.display_cache.clear()
            
            # Pre-generate commonly used pyramid levels
            if self.enable_fast_zoom:
                self.update_status("🚀 Pre-generating pyramid levels...")
                
                # Generate levels based on image size
                img_size = self.original_image.size[0] * self.original_image.size[1]
                
                if img_size > 50_000_000:  # > 50MP - generate more levels
                    levels_to_create = [0.05, 0.1, 0.25, 0.5]
                elif img_size > 10_000_000:  # > 10MP
                    levels_to_create = [0.1, 0.25, 0.5]
                else:  # Smaller images
                    levels_to_create = [0.25, 0.5]
                
                for level in levels_to_create:
                    self._create_pyramid_level(level)
                    # Allow UI to remain responsive
                    self.root.update_idletasks()
                
                self.update_status(f"✅ Created {len(levels_to_create)} pyramid levels")
            
            # Update memory display
            self.update_memory_display()
            
        except Exception as e:
            print(f"Error optimizing image loading: {e}")
            self.update_status(f"⚠️ Optimization error: {str(e)[:50]}")
        
    def redraw_selections(self):
        """Redraw current selection being drawn"""
        # Only show the current selection path being drawn (if any)
        pass
        
    def draw_clipped_sections(self):
        """Draw all clipped sections on the canvas"""
        print(f"DEBUG: draw_clipped_sections called, sections count: {len(self.clipped_sections)}")
        
        # Clear section photos to prevent memory leaks
        self.section_photos = []
        
        for i, section in enumerate(self.clipped_sections):
            print(f"DEBUG: Drawing section {i}: pos={section['position']}, size={section['size']}, color={section['color']}")
            # Calculate scaled position
            x, y = section['position']
            scaled_x = int(x * self.image_scale)
            scaled_y = int(y * self.image_scale)
            
            # Scale the section image
            width, height = section['size']
            scaled_width = int(width * self.image_scale)
            scaled_height = int(height * self.image_scale)
            
            print(f"DEBUG: Section {i} scaled dimensions: {scaled_width}x{scaled_height} at ({scaled_x}, {scaled_y})")
            
            if scaled_width > 0 and scaled_height > 0:
                print(f"DEBUG: Resizing section {i} image for display")
                # Resize the clipped section for display
                display_section = section['image'].resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                
                print(f"DEBUG: Converting section {i} to PhotoImage")
                # Convert to PhotoImage
                section_photo = ImageTk.PhotoImage(display_section)
                
                # Store reference to prevent garbage collection
                self.section_photos.append(section_photo)
                
                print(f"DEBUG: Drawing section {i} on canvas at ({scaled_x}, {scaled_y})")
                # Draw on canvas
                img_id = self.canvas.create_image(scaled_x, scaled_y, anchor=tk.NW, image=section_photo, tags=f"clipped_{i}")
                print(f"DEBUG: Section {i} canvas image ID: {img_id}")
                
                # Draw border around clipped section
                border_color = section['color']
                border_width = 2
                
                # Highlight selected section
                selection = self.sections_listbox.curselection()
                if selection and selection[0] == i:
                    border_color = "#0066FF"  # Blue for selected
                    border_width = 3
                
                self.canvas.create_rectangle(
                    scaled_x, scaled_y, 
                    scaled_x + scaled_width, scaled_y + scaled_height,
                    outline=border_color, width=border_width, tags=f"clipped_border_{i}"
                )
                
                # Draw resize handles if in move mode
                if self.current_mode == "move":
                    handle_size = 8
                    # Top-left corner
                    self.canvas.create_rectangle(
                        scaled_x - handle_size//2, scaled_y - handle_size//2,
                        scaled_x + handle_size//2, scaled_y + handle_size//2,
                        fill="blue", outline="darkblue", tags=f"handle_tl_{i}"
                    )
                    # Top-right corner
                    self.canvas.create_rectangle(
                        scaled_x + scaled_width - handle_size//2, scaled_y - handle_size//2,
                        scaled_x + scaled_width + handle_size//2, scaled_y + handle_size//2,
                        fill="blue", outline="darkblue", tags=f"handle_tr_{i}"
                    )
                    # Bottom-left corner
                    self.canvas.create_rectangle(
                        scaled_x - handle_size//2, scaled_y + scaled_height - handle_size//2,
                        scaled_x + handle_size//2, scaled_y + scaled_height + handle_size//2,
                        fill="blue", outline="darkblue", tags=f"handle_bl_{i}"
                    )
                    # Bottom-right corner
                    self.canvas.create_rectangle(
                        scaled_x + scaled_width - handle_size//2, scaled_y + scaled_height - handle_size//2,
                        scaled_x + scaled_width + handle_size//2, scaled_y + scaled_height + handle_size//2,
                        fill="blue", outline="darkblue", tags=f"handle_br_{i}"
                    )
                        
    def on_mouse_down(self, event):
        """Handle mouse button press with improved precision"""
        if self.original_image is None:
            return
            
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates with precision handling
        if self.precise_mode:
            image_x = canvas_x / self.image_scale
            image_y = canvas_y / self.image_scale
        else:
            image_x = round(canvas_x / self.image_scale)
            image_y = round(canvas_y / self.image_scale)
        
        # Store current mouse position for smooth movement
        self.last_mouse_pos = (image_x, image_y)
        
        # Handle ruler interaction first (if enabled)
        if self.show_ruler and self._handle_ruler_click(event.x, event.y, image_x, image_y):
            return
        
        # Handle line dragging (if lines are shown and not confirmed)
        if self.show_lines and not self.lines_confirmed and self._handle_line_click(event.x, event.y):
            return
        
        if self.current_mode == "select":
            print(f"DEBUG: on_mouse_down - selection mode, starting drawing at ({image_x}, {image_y})")
            self.drawing = True
            self.selection_path = [(image_x, image_y)]
            
        elif self.current_mode == "move":
            self.drag_start = (image_x, image_y)
            # Check if clicking on a resize handle first
            clicked_handle = self.find_resize_handle_at_point(event.x, event.y)
            if clicked_handle is not None:
                self.selected_section = clicked_handle[0]
                self.resize_mode = True
                self.resize_corner = clicked_handle[1]
                self.update_status(f"Resizing section {self.selected_section + 1} from {self.resize_corner} corner")
            else:
                # Find which clipped section was clicked for moving
                clicked_section = self.find_clipped_section_at_point(image_x, image_y)
                if clicked_section is not None:
                    self.selected_section = clicked_section
                    # Ensure this section is selected in the listbox
                    self.sections_listbox.selection_clear(0, tk.END)
                    self.sections_listbox.selection_set(clicked_section)
                    self.sections_listbox.activate(clicked_section)
                    self.resize_mode = False
                    self.update_status(f"Moving section {self.selected_section + 1} - {'grid snap' if self.snap_to_grid else 'precise' if self.precise_mode else 'standard'} mode")
                else:
                    self.selected_section = None
                
    def on_mouse_drag(self, event):
        """Handle mouse drag with improved precision"""
        if self.original_image is None:
            return
            
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates with precision handling
        if self.precise_mode:
            image_x = canvas_x / self.image_scale
            image_y = canvas_y / self.image_scale
        else:
            image_x = round(canvas_x / self.image_scale)
            image_y = round(canvas_y / self.image_scale)
        
        # Handle ruler dragging first (if active)
        if self.show_ruler and self._handle_ruler_drag(canvas_x, canvas_y, image_x, image_y):
            return
        
        # Handle line dragging (if active)
        if self.dragging_line is not None and self._handle_line_drag(canvas_x, canvas_y):
            return
        
        if self.current_mode == "select" and self.drawing:
            self.selection_path.append((image_x, image_y))
            # Only log every 50th point to reduce spam
            if len(self.selection_path) % 50 == 0:
                print(f"DEBUG: on_mouse_drag - path length now: {len(self.selection_path)}")
            
            # Draw temporary line
            if len(self.selection_path) > 1:
                prev_point = self.selection_path[-2]
                curr_point = self.selection_path[-1]
                self.canvas.create_line(
                    prev_point[0] * self.image_scale, prev_point[1] * self.image_scale,
                    curr_point[0] * self.image_scale, curr_point[1] * self.image_scale,
                    fill=self.selected_color, width=int(self.brush_size), tags="temp_selection"
                )
                
        elif self.current_mode == "move" and self.selected_section is not None and self.last_mouse_pos:
            # Calculate movement delta from last position for smoother movement
            dx = image_x - self.last_mouse_pos[0]
            dy = image_y - self.last_mouse_pos[1]
            
            # Use much smaller movement threshold for responsive movement
            movement_threshold = 0.01 if self.precise_mode else 0.1
            if abs(dx) >= movement_threshold or abs(dy) >= movement_threshold:
                if self.resize_mode:
                    # Resize the clipped section (no buffering for resize to maintain responsiveness)
                    self.resize_clipped_section(self.selected_section, self.resize_corner, dx, dy)
                    # Update last position for resize
                    self.last_mouse_pos = (image_x, image_y)
                else:
                    # Move the clipped section with buffering
                    self.move_clipped_section(self.selected_section, dx, dy)
                    # Always update last position for smooth tracking
                    self.last_mouse_pos = (image_x, image_y)
            
    def on_mouse_up(self, event):
        """Handle mouse button release with precision feedback"""
        # Handle ruler release first (if active)
        if self.show_ruler and self._handle_ruler_release():
            return
        
        # Handle line release (if active)
        if self._handle_line_release():
            return
        
        if self.current_mode == "select" and self.drawing:
            print(f"DEBUG: on_mouse_up - selection mode, drawing was: {self.drawing}")
            self.drawing = False
            
            print(f"DEBUG: selection_path length: {len(self.selection_path) if hasattr(self, 'selection_path') else 'NO PATH'}")
            if len(self.selection_path) > 2:
                print(f"DEBUG: Creating clipped section with path of {len(self.selection_path)} points")
                # Automatically clip and color the selection
                self.create_clipped_section(self.selection_path.copy(), self.selected_color)
            else:
                print(f"DEBUG: Path too short for section creation: {len(self.selection_path)}")
                
            # Clear temporary drawing
            self.canvas.delete("temp_selection")
            print(f"DEBUG: on_mouse_up calling display_image after section creation")
            self.display_image()
            
        elif self.current_mode == "move":
            if self.selected_section is not None:
                # Final position feedback
                section = self.clipped_sections[self.selected_section]
                x, y = section['position']
                if self.precise_mode:
                    self.update_status(f"Section {self.selected_section + 1} positioned at ({x:.2f}, {y:.2f})")
                else:
                    self.update_status(f"Section {self.selected_section + 1} positioned at ({int(x)}, {int(y)})")
            
            self.selected_section = None
            self.drag_start = None
            self.resize_mode = False
            self.resize_corner = None
            self.last_mouse_pos = None
            
    def on_mouse_move(self, event):
        """Handle mouse movement for cursor updates and coordinate display"""
        if self.original_image is None:
            return
            
        # Get canvas coordinates and convert to image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        image_x = canvas_x / self.image_scale
        image_y = canvas_y / self.image_scale
        
        # Update cursor based on what's under the mouse
        if self.current_mode == "move":
            # Check if over a resize handle
            handle = self.find_resize_handle_at_point(event.x, event.y)
            if handle:
                self.canvas.config(cursor="sizing")
            elif self.find_clipped_section_at_point(image_x, image_y) is not None:
                self.canvas.config(cursor="fleur")  # Move cursor
            else:
                self.canvas.config(cursor="arrow")
        
        # Show coordinates in coordinate label (both pixels and cm)
        if hasattr(self, 'coord_label'):
            # Convert to centimeters
            x_cm = self.pixels_to_cm(image_x)
            y_cm = self.pixels_to_cm(image_y)
            
            if self.snap_to_grid:
                snap_x, snap_y = self.snap_to_grid_position(image_x, image_y)
                snap_x_cm = self.pixels_to_cm(snap_x)
                snap_y_cm = self.pixels_to_cm(snap_y)
                self.coord_label.config(text=f"({image_x:.1f}px, {image_y:.1f}px) | ({x_cm:.2f}cm, {y_cm:.2f}cm) → Snap: ({snap_x:.0f}px, {snap_y:.0f}px) | ({snap_x_cm:.2f}cm, {snap_y_cm:.2f}cm)")
            elif self.precise_mode:
                self.coord_label.config(text=f"Pos: ({image_x:.2f}px, {image_y:.2f}px) | ({x_cm:.2f}cm, {y_cm:.2f}cm)")
            else:
                self.coord_label.config(text=f"Pos: ({int(image_x)}px, {int(image_y)}px) | ({x_cm:.2f}cm, {y_cm:.2f}cm)")
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts for precise movement and image navigation"""
        # Handle image navigation with WASD and arrow keys (when not in move mode or no section selected)
        navigation_keys = {
            'w': (0, -1), 'W': (0, -1), 'Up': (0, -1),
            's': (0, 1), 'S': (0, 1), 'Down': (0, 1),
            'a': (-1, 0), 'A': (-1, 0), 'Left': (-1, 0),
            'd': (1, 0), 'D': (1, 0), 'Right': (1, 0)
        }
        
        # Check if we should handle image navigation
        should_navigate = False
        if event.keysym in navigation_keys:
            if self.current_mode != "move":
                should_navigate = True
            elif not self.clipped_sections or not self.sections_listbox.curselection():
                should_navigate = True
        
        if should_navigate and event.keysym in navigation_keys:
            self.pan_image(navigation_keys[event.keysym], event.state & 1)  # Pass shift state
            return
        
        # Handle section movement (original functionality)
        if self.current_mode != "move" or not self.clipped_sections:
            return
        
        # Handle arrow keys for precision movement
        if event.keysym in ['Up', 'Down', 'Left', 'Right']:
            # Check if a section is selected
            selection = self.sections_listbox.curselection()
            if not selection:
                self.update_status("Select a section first to use arrow key movement")
                return
            
            # Map arrow keys to directions
            key_directions = {
                'Up': (0, -1),
                'Down': (0, 1),
                'Left': (-1, 0),
                'Right': (1, 0)
            }
            
            direction_x, direction_y = key_directions[event.keysym]
            
            # Use larger step for Shift+Arrow (10x multiplier)
            if event.state & 1:  # Shift key held
                original_step = self.movement_step_var.get()
                try:
                    multiplied_step = float(original_step) * 10
                    self.movement_step_var.set(str(multiplied_step))
                    self.move_selected_section(direction_x, direction_y)
                    self.movement_step_var.set(original_step)  # Restore original
                except ValueError:
                    pass
            else:
                # Normal arrow key movement
                self.move_selected_section(direction_x, direction_y)
    
    def _handle_ruler_click(self, canvas_x, canvas_y, image_x, image_y):
        """Handle clicks when ruler is enabled"""
        if not self.show_ruler:
            return False
        
        # Check if clicking near existing ruler endpoints (for dragging)
        if self.ruler_start and self.ruler_end:
            start_display = (self.ruler_start[0] * self.image_scale, self.ruler_start[1] * self.image_scale)
            end_display = (self.ruler_end[0] * self.image_scale, self.ruler_end[1] * self.image_scale)
            
            # Check if clicking near start point
            if self._point_distance(canvas_x, canvas_y, start_display[0], start_display[1]) < 10:
                self.ruler_dragging = True
                self.ruler_drag_point = "start"
                return True
            
            # Check if clicking near end point
            if self._point_distance(canvas_x, canvas_y, end_display[0], end_display[1]) < 10:
                self.ruler_dragging = True
                self.ruler_drag_point = "end"
                return True
            
            # Check if clicking on the line (for moving entire ruler)
            if self._point_to_line_distance(canvas_x, canvas_y, start_display, end_display) < 5:
                self.ruler_dragging = True
                self.ruler_drag_point = "line"
                self.ruler_drag_offset = (
                    canvas_x - start_display[0],
                    canvas_y - start_display[1]
                )
                return True
        
        # If not dragging existing ruler, start new ruler
        self.ruler_start = (image_x, image_y)
        self.ruler_end = (image_x, image_y)
        self.ruler_dragging = True
        self.ruler_drag_point = "end"
        self.update_status("Drawing ruler - drag to set end point")
        return True
    
    def _handle_ruler_drag(self, canvas_x, canvas_y, image_x, image_y):
        """Handle ruler dragging"""
        if not self.ruler_dragging:
            return False
        
        if self.ruler_drag_point == "start":
            self.ruler_start = (image_x, image_y)
        elif self.ruler_drag_point == "end":
            self.ruler_end = (image_x, image_y)
        elif self.ruler_drag_point == "line":
            # Move entire ruler
            if hasattr(self, 'ruler_drag_offset'):
                start_display = (self.ruler_start[0] * self.image_scale, self.ruler_start[1] * self.image_scale)
                new_start_x = (canvas_x - self.ruler_drag_offset[0]) / self.image_scale
                new_start_y = (canvas_y - self.ruler_drag_offset[1]) / self.image_scale
                
                # Calculate ruler length and direction
                dx = self.ruler_end[0] - self.ruler_start[0]
                dy = self.ruler_end[1] - self.ruler_start[1]
                
                # Move both points
                self.ruler_start = (new_start_x, new_start_y)
                self.ruler_end = (new_start_x + dx, new_start_y + dy)
        
        # Redraw with updated ruler
        self.display_image()
        return True
    
    def _handle_ruler_release(self):
        """Handle ruler mouse release"""
        if self.ruler_dragging:
            self.ruler_dragging = False
            self.ruler_drag_point = None
            if hasattr(self, 'ruler_drag_offset'):
                delattr(self, 'ruler_drag_offset')
            
            if self.ruler_start and self.ruler_end:
                _, _, cm_distance = self.calculate_distance(
                    self.ruler_start[0], self.ruler_start[1],
                    self.ruler_end[0], self.ruler_end[1]
                )
                self.update_status(f"Ruler measurement: {cm_distance:.2f} cm")
            return True
        return False
    
    def _point_distance(self, x1, y1, x2, y2):
        """Calculate distance between two points"""
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def _point_to_line_distance(self, px, py, line_start, line_end):
        """Calculate distance from point to line segment"""
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Line length squared
        line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        
        if line_len_sq == 0:
            return self._point_distance(px, py, x1, y1)
        
        # Parameter t that represents position along the line
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len_sq))
        
        # Closest point on line segment
        closest_x = x1 + t * (x2 - x1)
        closest_y = y1 + t * (y2 - y1)
        
        return self._point_distance(px, py, closest_x, closest_y)
        
    def _handle_line_click(self, canvas_x, canvas_y):
        """Handle clicking on a vertical line for dragging"""
        if not self.line_positions or not self.original_image:
            return False
        
        # Convert canvas coordinates to image coordinates
        image_x = canvas_x / self.image_scale
        
        # Check if click is near any line
        for i, line_x in enumerate(self.line_positions):
            line_display_x = line_x * self.image_scale
            distance = abs(canvas_x - line_display_x)
            
            if distance <= self.line_drag_tolerance:
                self.dragging_line = i
                self.line_drag_start = (canvas_x, canvas_y)
                self.update_status(f"Dragging vertical line {i + 1} - drag to reposition")
                # Redraw to show dragging color
                self.display_image()
                return True
        
        return False
    
    def _handle_line_drag(self, canvas_x, canvas_y):
        """Handle dragging a vertical line"""
        if self.dragging_line is None or not self.original_image:
            return False
        
        # Convert to image coordinates
        new_image_x = canvas_x / self.image_scale
        
        # Clamp to image bounds with some margin
        orig_width = self.original_image.size[0]
        new_image_x = max(10, min(orig_width - 10, new_image_x))
        
        # Update line position
        self.line_positions[self.dragging_line] = new_image_x
        
        # Redraw to show new position
        self.display_image()
        
        # Update status with position info
        cm_from_left = self.pixels_to_cm(new_image_x)
        self.update_status(f"Line {self.dragging_line + 1}: {cm_from_left:.1f}cm from left edge")
        return True
    
    def _handle_line_release(self):
        """Handle releasing a dragged line"""
        if self.dragging_line is not None:
            self.update_status(f"Line {self.dragging_line + 1} positioned")
            self.dragging_line = None
            self.line_drag_start = None
            # Redraw to remove dragging color
            self.display_image()
            return True
        return False
            
        # Get currently selected section from listbox
        selection = self.sections_listbox.curselection()
        if not selection:
            return
            
        section_idx = selection[0]
        if section_idx >= len(self.clipped_sections):
            return
            
        # Movement step size
        step = 1 if not (event.state & 0x1) else 10  # 10 pixels if Shift held, 1 otherwise
        if self.precise_mode and not (event.state & 0x1):
            step = 0.1  # Sub-pixel movement in precise mode
            
        # Arrow key movements
        dx, dy = 0, 0
        if event.keysym == "Left":
            dx = -step
        elif event.keysym == "Right":
            dx = step
        elif event.keysym == "Up":
            dy = -step
        elif event.keysym == "Down":
            dy = step
        else:
            return  # Not an arrow key
            
        # Move the section
        if dx != 0 or dy != 0:
            self.move_clipped_section(section_idx, dx, dy)
            # Update status to show movement
            section = self.clipped_sections[section_idx]
            x, y = section['position']
            self.update_status(f"Moved section {section_idx + 1} to ({x:.1f}, {y:.1f}) using keyboard")
            return "break"  # Prevent default handling
        
    def find_resize_handle_at_point(self, canvas_x, canvas_y):
        """Find if a resize handle was clicked, returns (section_index, corner) or None"""
        handle_size = 8
        
        for i, section in enumerate(self.clipped_sections):
            x, y = section['position']
            width, height = section['size']
            
            # Scale coordinates
            scaled_x = int(x * self.image_scale)
            scaled_y = int(y * self.image_scale)
            scaled_width = int(width * self.image_scale)
            scaled_height = int(height * self.image_scale)
            
            # Check each corner handle
            handles = {
                'tl': (scaled_x, scaled_y),  # top-left
                'tr': (scaled_x + scaled_width, scaled_y),  # top-right
                'bl': (scaled_x, scaled_y + scaled_height),  # bottom-left
                'br': (scaled_x + scaled_width, scaled_y + scaled_height)  # bottom-right
            }
            
            for corner, (hx, hy) in handles.items():
                if (hx - handle_size//2 <= canvas_x <= hx + handle_size//2 and
                    hy - handle_size//2 <= canvas_y <= hy + handle_size//2):
                    return (i, corner)
        
        return None
        
    def resize_clipped_section(self, section_idx, corner, dx, dy):
        """Resize a clipped section by dragging a corner"""
        if 0 <= section_idx < len(self.clipped_sections):
            section = self.clipped_sections[section_idx]
            x, y = section['position']
            width, height = section['size']
            
            # Calculate new dimensions based on which corner is being dragged
            new_x, new_y = x, y
            new_width, new_height = width, height
            
            if corner == 'tl':  # top-left
                new_x = x + dx
                new_y = y + dy
                new_width = width - dx
                new_height = height - dy
            elif corner == 'tr':  # top-right
                new_y = y + dy
                new_width = width + dx
                new_height = height - dy
            elif corner == 'bl':  # bottom-left
                new_x = x + dx
                new_width = width - dx
                new_height = height + dy
            elif corner == 'br':  # bottom-right
                new_width = width + dx
                new_height = height + dy
            
            # Enforce minimum size and maintain aspect ratio
            min_size = 20
            if new_width >= min_size and new_height >= min_size:
                # Calculate aspect ratio from original
                original_width, original_height = section['original_size']
                aspect_ratio = original_width / original_height
                
                # Adjust dimensions to maintain aspect ratio
                # Use the smaller scale factor to prevent deformation
                scale_factor = min(new_width / original_width, new_height / original_height)
                final_width = int(original_width * scale_factor)
                final_height = int(original_height * scale_factor)
                
                # Update section data
                section['position'] = (new_x, new_y)
                section['size'] = (final_width, final_height)
                
                # Resize the actual image maintaining aspect ratio
                resized_image = section['original_image'].resize((final_width, final_height), Image.Resampling.LANCZOS)
                section['image'] = resized_image
                
                # Update boundary for hit detection (scale the original boundary proportionally)
                if 'original_boundary' in section:
                    original_boundary = section['original_boundary']
                    bbox = section['original_bbox']
                    
                    # Use the same scale factor for both dimensions
                    scale_factor = min(final_width / (bbox[2] - bbox[0]), final_height / (bbox[3] - bbox[1]))
                    
                    section['boundary'] = [
                        (new_x + (pt[0] - bbox[0]) * scale_factor, new_y + (pt[1] - bbox[1]) * scale_factor)
                        for pt in original_boundary
                    ]
                
                self.display_image()
        
    def create_clipped_section(self, path, color):
        """Create a new clipped section with color overlay"""
        print(f"DEBUG: create_clipped_section called with path length: {len(path)}, color: {color}")
        if len(path) < 3:
            print(f"DEBUG: Path too short, returning")
            return
            
        # Create mask for the selection
        mask = Image.new('L', self.original_image.size, 0)
        draw = ImageDraw.Draw(mask)
        pil_path = [(int(x), int(y)) for x, y in path]
        draw.polygon(pil_path, fill=255)
        
        # Extract the selected area from original image with transparency
        # Create RGBA version of original image
        original_rgba = self.original_image.convert('RGBA')
        
        # Create transparent background
        transparent_bg = Image.new('RGBA', self.original_image.size, (0, 0, 0, 0))
        
        # Apply mask to create transparent selection
        selected_area = Image.composite(original_rgba, transparent_bg, mask)
        
        # Create colored overlay with 30% opacity
        overlay = Image.new('RGBA', self.original_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Convert hex color to RGB and add 30% alpha
        hex_color = color.lstrip('#')
        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgba_color = rgb_color + (77,)  # 30% opacity (77/255)
        
        overlay_draw.polygon(pil_path, fill=rgba_color)
        
        # Blend the color overlay with the selected area (maintaining transparency)
        colored_section = Image.alpha_composite(selected_area, overlay)
        
        # Get bounding box of the selection
        bbox = mask.getbbox()
        if bbox:
            # Crop the colored section to its bounding box
            cropped_section = colored_section.crop(bbox)
            
            # Store the clipped section data
            clipped_section = {
                'image': cropped_section,
                'position': bbox[:2],  # (x, y) of top-left corner
                'size': (bbox[2] - bbox[0], bbox[3] - bbox[1]),  # (width, height)
                'boundary': path,  # Original selection boundary for hit detection
                'color': color,
                'id': len(self.clipped_sections),
                'original_image': cropped_section.copy(),  # Store original for resize
                'original_boundary': path.copy(),  # Store original boundary
                'original_bbox': bbox,  # Store original bbox
                'original_size': (bbox[2] - bbox[0], bbox[3] - bbox[1])  # Store original size
            }
            
            print(f"DEBUG: Adding clipped section to list, current count: {len(self.clipped_sections)}")
            self.clipped_sections.append(clipped_section)
            print(f"DEBUG: Clipped sections count after append: {len(self.clipped_sections)}")
            
            # Ensure working image exists
            if self.working_image is None:
                self.working_image = self.original_image.copy()
            
            # Remove the area from the working image (create hole with white background)
            # Create a mask where the selected area becomes white (background color)
            working_copy = self.working_image.copy()
            working_draw = ImageDraw.Draw(working_copy)
            working_draw.polygon(pil_path, fill=(255, 255, 255))  # Fill with white background
            
            self.working_image = working_copy
            
            # Clear image cache to force refresh with the hole
            self.display_cache.clear()
            self.image_pyramid.clear()
            
            # Update the sections list
            print(f"DEBUG: Updating sections list")
            self.update_sections_list()
            
            print(f"DEBUG: Section creation completed successfully")
            messagebox.showinfo("Clipped", f"Section clipped and colored! Switch to 'Move' mode to reposition it.")
        
    def move_clipped_section(self, section_idx, dx, dy):
        """Move a clipped section with optional light buffering for smooth motion"""
        if not (0 <= section_idx < len(self.clipped_sections)):
            return
        
        section = self.clipped_sections[section_idx]
        x, y = section['position']
        
        # Check if smooth movement is enabled
        if hasattr(self, 'smooth_var') and self.smooth_var.get():
            # Light buffering for smoothness
            self.add_movement_to_buffer(dx, dy)
            
            # Get smoothed movement with less restriction
            if self.should_update_display() or abs(dx) > 1 or abs(dy) > 1:
                smooth_dx, smooth_dy = self.get_smoothed_movement()
                section['position'] = (x + smooth_dx, y + smooth_dy)
                # Update boundary for hit detection
                section['boundary'] = [(bx + smooth_dx, by + smooth_dy) for bx, by in section['boundary']]
            else:
                return  # Skip update for very small movements
        else:
            # Direct movement without buffering for maximum speed
            section['position'] = (x + dx, y + dy)
            # Update boundary for hit detection
            section['boundary'] = [(bx + dx, by + dy) for bx, by in section['boundary']]
        
        # Always update display for responsive feedback
        self.display_image()
    
    def move_clipped_section_direct(self, section_idx, dx, dy):
        """Direct movement without buffering - used internally by interpolation"""
        if not (0 <= section_idx < len(self.clipped_sections)):
            return
            
        section = self.clipped_sections[section_idx]
        # Update position
        old_x, old_y = section['position']
        new_x = old_x + dx
        new_y = old_y + dy
        
        # Apply grid snapping if enabled
        if self.snap_to_grid:
            new_x, new_y = self.snap_to_grid_position(new_x, new_y)
        elif not self.precise_mode:
            # Round to whole pixels if not in precise mode
            new_x = round(new_x)
            new_y = round(new_y)
        
        section['position'] = (new_x, new_y)
        
        # Update boundary for hit detection
        actual_dx = new_x - old_x
        actual_dy = new_y - old_y
        section['boundary'] = [(x + actual_dx, y + actual_dy) for x, y in section['boundary']]
        
        # Only update display if significant change
        if abs(actual_dx) > 0.01 or abs(actual_dy) > 0.01:
            self.display_image()
            
            # Show precise coordinates in status (less frequently to avoid spam)
            if hasattr(self, '_last_status_update'):
                import time
                if time.time() - self._last_status_update > 0.1:  # Update status every 100ms max
                    self._update_movement_status(section_idx, new_x, new_y)
                    self._last_status_update = time.time()
            else:
                self._update_movement_status(section_idx, new_x, new_y)
                import time
                self._last_status_update = time.time()
    
    def _update_movement_status(self, section_idx, x, y):
        """Update status bar with movement information"""
        if self.precise_mode:
            self.update_status(f"Section {section_idx + 1} moved to ({x:.2f}, {y:.2f})")
        else:
            self.update_status(f"Section {section_idx + 1} moved to ({int(x)}, {int(y)})")
    
    def move_selected_section(self, direction_x, direction_y):
        """Move the currently selected section by a specified amount in the given direction"""
        # Get currently selected section
        selection = self.sections_listbox.curselection()
        if not selection:
            self.update_status("No section selected for precision movement")
            self.selected_info_var.set("No section selected")
            return
        
        selected_idx = selection[0]
        if selected_idx >= len(self.clipped_sections):
            self.update_status("Invalid section selection")
            return
        
        try:
            # Get step size in centimeters
            step_value_cm = float(self.movement_step_var.get())
            
            # Convert cm to pixels
            step_pixels = self.cm_to_pixels(step_value_cm)
            
            # Calculate movement delta
            dx = direction_x * step_pixels
            dy = direction_y * step_pixels
            
            # Move the section
            self.move_clipped_section_direct(selected_idx, dx, dy)
            
            # Update selected section info
            section = self.clipped_sections[selected_idx]
            x, y = section['position']
            
            direction_names = {
                (0, -1): "up", (0, 1): "down", 
                (-1, 0): "left", (1, 0): "right"
            }
            direction_name = direction_names.get((direction_x, direction_y), "diagonally")
            
            self.update_status(f"Section {selected_idx + 1} moved {direction_name} by {step_value_cm:.2f}cm")
            
            # Update position display in cm
            x_cm = self.pixels_to_cm(x)
            y_cm = self.pixels_to_cm(y)
            self.selected_info_var.set(f"Section {selected_idx + 1} at ({x_cm:.2f}, {y_cm:.2f}) cm")
                
        except ValueError:
            self.update_status("Invalid step size - please enter a number")
            self.movement_step_var.set("1")  # Reset to default
    
    def find_clipped_section_at_point(self, x, y):
        """Find which clipped section contains the given point (prioritize recently selected)"""
        # Check currently selected section first to maintain selection stability
        selection = self.sections_listbox.curselection()
        if selection:
            selected_idx = selection[0]
            if (selected_idx < len(self.clipped_sections) and 
                self.point_in_polygon(x, y, self.clipped_sections[selected_idx]['boundary'])):
                return selected_idx
        
        # If current selection doesn't contain point, find any section that does
        # Check in reverse order so top sections (drawn last) are selected first
        for i in reversed(range(len(self.clipped_sections))):
            if self.point_in_polygon(x, y, self.clipped_sections[i]['boundary']):
                # Auto-select this section in the listbox
                self.sections_listbox.selection_clear(0, tk.END)
                self.sections_listbox.selection_set(i)
                self.sections_listbox.activate(i)
                return i
        return None
        
    def point_in_polygon(self, x, y, polygon):
        """Check if point is inside polygon using ray casting algorithm"""
        if len(polygon) < 3:
            return False
            
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside
        
    def apply_color_to_section(self, section_idx):
        """This function is no longer needed - clipping and coloring happen together"""
        pass
            
    def clip_section(self, section_idx):
        """This function is no longer needed - clipping and coloring happen together"""
        pass
            
    def create_selection_mask(self, path):
        """Create a mask from selection path"""
        mask = Image.new('L', self.original_image.size, 0)
        draw = ImageDraw.Draw(mask)
        
        if len(path) > 2:
            # Convert path to PIL format
            pil_path = [(int(x), int(y)) for x, y in path]
            draw.polygon(pil_path, fill=255)
            
        return mask
        
    def move_section(self, section_idx, dx, dy):
        """This function is no longer needed - use move_clipped_section instead"""
        pass
            
    def zoom_in(self):
        """🚀 Optimized zoom in"""
        old_scale = self.image_scale
        self.image_scale *= 1.2
        self.image_scale = min(10.0, self.image_scale)  # Limit max zoom
        
        if old_scale != self.image_scale:
            # Clear cache if zoom level changed significantly
            if abs(self.image_scale - old_scale) > 0.5:
                self.display_cache.clear()
            self.display_image()
            self.update_status(f"🔍 Zoomed in to {self.image_scale:.1f}x")
        else:
            self.update_status("🔍 Maximum zoom reached")
        
    def zoom_out(self):
        """🚀 Optimized zoom out"""
        old_scale = self.image_scale
        self.image_scale /= 1.2
        self.image_scale = max(0.05, self.image_scale)  # Limit min zoom
        
        if old_scale != self.image_scale:
            # Clear cache if zoom level changed significantly
            if abs(old_scale - self.image_scale) > 0.5:
                self.display_cache.clear()
            self.display_image()
            self.update_status(f"🔍 Zoomed out to {self.image_scale:.1f}x")
        else:
            self.update_status("🔍 Minimum zoom reached")
    
    def on_mouse_wheel(self, event):
        """🚀 High-performance mouse wheel zooming with viewport tracking"""
        if self.original_image is None:
            return
        
        # Store mouse position for zoom-to-cursor (future enhancement)
        mouse_x = self.canvas.canvasx(event.x)
        mouse_y = self.canvas.canvasy(event.y)
        
        old_scale = self.image_scale
        zoom_factor = 1.1  # Smoother zoom increments
        
        # Determine zoom direction - Windows uses delta, Linux uses num
        if hasattr(event, 'delta'):  # Windows
            if event.delta > 0:
                self.image_scale *= zoom_factor  # Zoom in
                direction = "in"
            else:
                self.image_scale /= zoom_factor  # Zoom out
                direction = "out"
        elif hasattr(event, 'num'):  # Linux
            if event.num == 4:
                self.image_scale *= zoom_factor  # Zoom in
                direction = "in"
            elif event.num == 5:
                self.image_scale /= zoom_factor  # Zoom out
                direction = "out"
        
        # Limit zoom range - more permissive for large images
        self.image_scale = max(0.01, min(50.0, self.image_scale))
        
        # Only update if zoom actually changed
        if abs(old_scale - self.image_scale) > 0.001:
            # Throttle cache clearing to improve performance
            scale_change = abs(old_scale - self.image_scale) / old_scale
            if scale_change > 0.3:  # Only clear cache for significant changes
                self.display_cache.clear()
            
            self.display_image()
            
            # Show memory usage for large images
            if self.enable_fast_zoom:
                memory_mb = self.get_memory_usage_mb()
                self.update_status(f"🚀 Zoom {direction} to {self.image_scale:.2f}x • Cache: {memory_mb:.1f}MB")
            else:
                self.update_status(f"🐌 Zoom {direction} to {self.image_scale:.2f}x (legacy mode)")
        else:
            self.update_status(f"🔍 Zoom limit reached ({self.image_scale:.2f}x)")
    
    def pan_image(self, direction, shift_pressed=False):
        """Pan the image using keyboard navigation"""
        if self.original_image is None:
            self.update_status("No image loaded - cannot pan")
            return
        
        direction_x, direction_y = direction
        speed = "fast" if shift_pressed else "normal"
        
        try:
            # Get current scroll positions (0.0 to 1.0)
            x_scroll_top, x_scroll_bottom = self.canvas.xview()
            y_scroll_top, y_scroll_bottom = self.canvas.yview()
            
            # Calculate step as fraction (larger if shift pressed)
            step_fraction = 0.15 if not shift_pressed else 0.4
            
            # Calculate new scroll positions
            new_x_top = x_scroll_top + (direction_x * step_fraction)
            new_y_top = y_scroll_top + (direction_y * step_fraction)
            
            # Clamp to valid range
            new_x_top = max(0.0, min(1.0, new_x_top))
            new_y_top = max(0.0, min(1.0, new_y_top))
            
            # Apply new scroll positions
            self.canvas.xview_moveto(new_x_top)
            self.canvas.yview_moveto(new_y_top)
            
            # Provide feedback
            keys = "WASD/Arrow keys"
            self.update_status(f"Image panned ({speed} speed) • Use {keys} to navigate • Hold Shift for faster panning")
            
        except tk.TclError:
            # Fallback - image might not be large enough to scroll
            self.update_status(f"Image navigation attempted ({speed}) • Image may not be large enough to pan")
        
    def fit_to_window(self):
        """Fit image to window with performance optimization for large images"""
        if self.original_image is None:
            return
            
        try:
            img_width, img_height = self.original_image.size
            
            # Calculate megapixels for performance optimization
            megapixels = (img_width * img_height) / 1_000_000
            
            # Update canvas to get current size
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate fit-to-window scale
            fit_scale = 1.0
            if canvas_width > 50 and canvas_height > 50:
                scale_x = (canvas_width - 20) / img_width  # Leave some margin
                scale_y = (canvas_height - 20) / img_height
                fit_scale = min(scale_x, scale_y, 1.0)
            else:
                # Fallback scale if canvas size is not available
                fit_scale = 0.5
            
            # Apply smart scaling that balances performance and visibility
            performance_scale = 1.0
            target_display_scale = 0.2  # Target 20% visibility as minimum
            
            if megapixels > 100:
                # Very large images: aggressive performance scaling but ensure visibility
                performance_scale = 0.3  # 30% for very large images
                self.update_status(f"Performance mode: Using {int(performance_scale*100)}% preview for very large {megapixels:.1f}MP image")
            elif megapixels > 50:
                # Large images: moderate performance scaling
                performance_scale = 0.5  # 50% for large images  
                self.update_status(f"Performance mode: Using {int(performance_scale*100)}% preview for large {megapixels:.1f}MP image")
            elif megapixels > 25:
                # Medium-large images: light performance scaling
                performance_scale = 0.7  # 70% for medium-large images
                self.update_status(f"Performance mode: Using {int(performance_scale*100)}% preview for {megapixels:.1f}MP image")
            
            # Calculate combined scale
            combined_scale = fit_scale * performance_scale
            
            # Ensure good visibility - prioritize usability over extreme performance
            if combined_scale < target_display_scale:
                # If the combined scale would make image too small, adjust the balance
                # Keep some performance benefit but ensure usability
                needed_fit_scale = target_display_scale / performance_scale
                
                if needed_fit_scale > 1.0:
                    # If we need more than 100% fit scale, reduce performance scaling instead
                    performance_scale = target_display_scale / fit_scale
                    performance_scale = max(performance_scale, 0.2)  # Never go below 20%
                    combined_scale = fit_scale * performance_scale
                else:
                    combined_scale = target_display_scale
            
            self.image_scale = combined_scale
            
            # Update canvas scroll region for larger images
            display_width = int(img_width * self.image_scale)
            display_height = int(img_height * self.image_scale)
            self.canvas.configure(scrollregion=(0, 0, display_width, display_height))
                
            self.display_image()
            
        except Exception as e:
            print(f"Error in fit_to_window: {e}")
            # Fallback: just display at current scale
            self.display_image()
            
    def change_mode(self):
        """Change the current operation mode with simple visual feedback"""
        self.current_mode = self.mode_var.get()
        
        # Update visual indicators based on mode
        if self.current_mode == "none":
            self.canvas.config(cursor="arrow")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Mouse Mode: Navigate, zoom, and interact with interface")
            # Update the mode indicator
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="Mouse Mode - Navigate and interact",
                                         bg='#607D8B')
        elif self.current_mode == "select":
            self.canvas.config(cursor="cross")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Selection Mode: Draw around parts of the image")
            # Update the mode indicator
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="Selection Mode - Draw around areas",
                                         bg='#4CAF50')
        elif self.current_mode == "move":
            self.canvas.config(cursor="arrow")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Move Mode: Drag sections to reposition them")
            # Update the mode indicator
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="Move Mode - Drag to reposition",
                                         bg='#2196F3')
        
    def toggle_lines(self):
        """Toggle vertical lines display"""
        try:
            if hasattr(self, 'lines_var') and self.lines_var:
                self.show_lines = self.lines_var.get()
            else:
                self.show_lines = False
            
            # If turning off lines, also unlock them
            if not self.show_lines and self.lines_confirmed:
                self.unlock_lines()
                
            if self.original_image:
                self.display_image()
                
            self.update_status(f"Vertical lines {'enabled' if self.show_lines else 'disabled'}")
        except Exception as e:
            self.update_status("Error toggling vertical lines")
    

    
    def draw_vertical_lines(self):
        """Draw vertical lines overlay on canvas that scale with image using cm-based spacing"""
        if not self.original_image:
            return
            
        # Clear previous line objects
        self.line_objects = []
        
        # Get image dimensions and scale
        orig_width, orig_height = self.original_image.size
        display_width = int(orig_width * self.image_scale)
        display_height = int(orig_height * self.image_scale)
        
        # If no line positions set, calculate initial positions
        if not self.line_positions or len(self.line_positions) != self.num_lines:
            # Calculate line spacing based on cm measurement
            line_spacing_pixels = self.cm_to_pixels(self.line_spacing_cm)
            
            # Reset line positions in image coordinates
            self.line_positions = []
            
            # Calculate starting position to center the lines
            total_width_needed = line_spacing_pixels * (self.num_lines - 1)
            start_x = (orig_width - total_width_needed) / 2
            
            # Calculate initial positions
            for i in range(self.num_lines):
                x_pos_image = start_x + (i * line_spacing_pixels)
                if x_pos_image >= 0 and x_pos_image <= orig_width:
                    self.line_positions.append(x_pos_image)
        
        # Draw vertical lines using stored positions
        for i, x_pos_image in enumerate(self.line_positions):
            # Scale to display coordinates
            x_pos_display = x_pos_image * self.image_scale
            
            # Draw line from top to bottom of the displayed image
            if self.lines_confirmed:
                line_color = '#00FF00'  # Green if confirmed
                line_width = 3
            elif self.dragging_line == i:
                line_color = '#FFD700'  # Gold if being dragged
                line_width = 4
            else:
                line_color = '#FF0000'  # Red if not confirmed
                line_width = 2
            
            # Create line and store its ID
            line_id = self.canvas.create_line(x_pos_display, 0, x_pos_display, display_height,
                                           fill=line_color, width=line_width, tags="guide_lines")
            self.line_objects.append(line_id)
    
    def draw_grid(self):
        """Draw grid overlay on canvas for precise positioning"""
        if not self.original_image or not self.show_grid:
            return
            
        # Get image dimensions and scale
        orig_width, orig_height = self.original_image.size
        display_width = int(orig_width * self.image_scale)
        display_height = int(orig_height * self.image_scale)
        
        # Calculate grid spacing in centimeters (always use cm now)
        grid_spacing_real = self.cm_to_pixels(self.grid_size_cm)
        
        # Calculate grid spacing in display coordinates
        grid_spacing_display = grid_spacing_real * self.image_scale
        
        # Draw vertical grid lines
        x = 0
        line_count = 0
        while x <= display_width:
            # Make every 5th line slightly thicker for major grid lines
            line_width = 2 if line_count % 5 == 0 else 1
            line_color = "#999999" if line_count % 5 == 0 else "#CCCCCC"
            
            self.canvas.create_line(x, 0, x, display_height,
                                  fill=line_color, width=line_width, tags="grid_line")
            x += grid_spacing_display
            line_count += 1
        
        # Draw horizontal grid lines
        y = 0
        line_count = 0
        while y <= display_height:
            # Make every 5th line slightly thicker for major grid lines
            line_width = 2 if line_count % 5 == 0 else 1
            line_color = "#999999" if line_count % 5 == 0 else "#CCCCCC"
            
            self.canvas.create_line(0, y, display_width, y,
                                  fill=line_color, width=line_width, tags="grid_line")
            y += grid_spacing_display
            line_count += 1
        
        # Draw grid labels for major lines (every 5th line) when in cm mode
        if self.image_scale > 0.5:  # Only show labels when zoomed in enough
            self._draw_grid_labels(display_width, display_height, grid_spacing_display)
    
    def _draw_grid_labels(self, display_width, display_height, grid_spacing_display):
        """Draw measurement labels on major grid lines (always in cm)"""
        major_spacing = grid_spacing_display * 5  # Every 5th line
        
        # Get the actual grid spacing in image pixels (always cm based now)
        grid_spacing_real = self.cm_to_pixels(self.grid_size_cm)
        major_spacing_real = grid_spacing_real * 5  # Every 5th line in real pixels
        
        # Draw vertical labels (showing X coordinates)
        x_display = 0
        x_real = 0
        grid_count = 0
        while x_display <= display_width:
            if grid_count > 0 and grid_count % 5 == 0:  # Every 5th line
                # Show cm values: each major line represents (grid_count // 5) * 5 * grid_size_cm
                # Or more simply: grid_count * grid_size_cm
                cm_value = grid_count * self.grid_size_cm
                label_text = f"{cm_value:.1f}cm"
                
                self.canvas.create_text(x_display, 15, text=label_text, fill="#666666",
                                      font=('Arial', 8), tags="grid_line")
            
            x_display += grid_spacing_display
            x_real += grid_spacing_real
            grid_count += 1
        
        # Draw horizontal labels (showing Y coordinates)
        y_display = 0
        y_real = 0
        grid_count = 0
        while y_display <= display_height:
            if grid_count > 0 and grid_count % 5 == 0:  # Every 5th line
                # Show cm values: each major line represents grid_count * grid_size_cm
                cm_value = grid_count * self.grid_size_cm
                label_text = f"{cm_value:.1f}cm"
                
                self.canvas.create_text(35, y_display, text=label_text, fill="#666666",
                                      font=('Arial', 8), tags="grid_line")
            
            y_display += grid_spacing_display
            y_real += grid_spacing_real
            grid_count += 1
    
    def draw_ruler(self):
        """Draw the measurement ruler if enabled and positioned"""
        if not self.show_ruler or not self.ruler_start or not self.ruler_end:
            return
        
        # Convert coordinates to display coordinates
        start_x = int(self.ruler_start[0] * self.image_scale)
        start_y = int(self.ruler_start[1] * self.image_scale)
        end_x = int(self.ruler_end[0] * self.image_scale)
        end_y = int(self.ruler_end[1] * self.image_scale)
        
        # Draw ruler line
        self.canvas.create_line(start_x, start_y, end_x, end_y,
                              fill="#FF4444", width=3, tags="ruler")
        
        # Draw ruler endpoints
        self.canvas.create_oval(start_x-5, start_y-5, start_x+5, start_y+5,
                              fill="#FF4444", outline="#CC0000", width=2, tags="ruler")
        self.canvas.create_oval(end_x-5, end_y-5, end_x+5, end_y+5,
                              fill="#FF4444", outline="#CC0000", width=2, tags="ruler")
        
        # Calculate and display measurement
        _, real_pixels, cm_distance = self.calculate_distance(
            self.ruler_start[0], self.ruler_start[1],
            self.ruler_end[0], self.ruler_end[1]
        )
        
        # Update measurement display
        measurement_text = f"Distance: {real_pixels:.1f} px ({cm_distance:.2f} cm)"
        self.ruler_measurement_var.set(measurement_text)
        
        # Draw measurement text on canvas
        mid_x = (start_x + end_x) // 2
        mid_y = (start_y + end_y) // 2 - 20
        
        # Create background for text
        self.canvas.create_rectangle(mid_x-50, mid_y-8, mid_x+50, mid_y+8,
                                   fill="#FFFFFF", outline="#FF4444", width=1, tags="ruler")
        self.canvas.create_text(mid_x, mid_y, text=f"{cm_distance:.2f} cm",
                              fill="#FF4444", font=('Arial', 10, 'bold'), tags="ruler")
    
    def resize_image_to_fit(self):
        """Resize image based on width/height percentage"""
        if not self.original_image:
            return
            
        try:
            width_percent = float(self.width_var.get()) / 100.0
            height_percent = float(self.height_var.get()) / 100.0
            
            # Calculate new scale based on percentages
            orig_width, orig_height = self.original_image.size
            
            # Get canvas size for reference
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 50 and canvas_height > 50:
                # Calculate scale to fit the percentage of canvas
                target_width = canvas_width * width_percent
                target_height = canvas_height * height_percent
                
                scale_x = target_width / orig_width
                scale_y = target_height / orig_height
                
                # Use the smaller scale to maintain aspect ratio
                self.image_scale = min(scale_x, scale_y)
                
                self.display_image()
                
        except ValueError:
            messagebox.showerror("Error", "Please enter valid percentage values")
    
    def fit_image_to_lines(self):
        """Automatically resize image to fit nicely between vertical lines"""
        if not self.original_image or not self.show_lines:
            messagebox.showwarning("Warning", "Please enable vertical lines first")
            return
            
        # Get canvas dimensions
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        
        if canvas_width <= 50:
            return
            
        # Calculate available width between lines
        if self.num_lines > 1:
            line_spacing = canvas_width / (self.num_lines + 1)
            # Make image fit within one section between lines (with some margin)
            target_width = line_spacing * 0.8  # 80% of space between lines
        else:
            target_width = canvas_width * 0.4  # 40% of canvas width
            
        # Calculate scale to achieve target width
        orig_width, orig_height = self.original_image.size
        new_scale = target_width / orig_width
        
        self.image_scale = new_scale
        
        # Update the percentage controls to reflect the new size
        canvas_height = self.canvas.winfo_height()
        if canvas_height > 50:
            width_percent = int((target_width / canvas_width) * 100)
            height_percent = int(((orig_height * new_scale) / canvas_height) * 100)
            
            self.width_var.set(str(width_percent))
            self.height_var.set(str(height_percent))
        
        self.display_image()
        self.update_status("Image resized to fit between lines")
    
    def reset_image_size(self):
        """Reset image to original size (100% scale)"""
        if self.original_image:
            self.image_scale = 1.0
            self.width_var.set("100")
            self.height_var.set("100")
            self.display_image()
            self.update_status("Image reset to original size")
    
    def confirm_lines(self):
        """Confirm and lock the current line positions"""
        if not self.show_lines:
            messagebox.showwarning("Warning", "Please enable vertical lines first")
            return
            
        self.lines_confirmed = True
        
        # Disable line modification controls
        self.lines_scale.config(state='disabled')
        # Find and disable the spacing spinbox
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                self._disable_spacing_controls(child)
        
        self.confirm_lines_button.config(state='disabled')
        self.unlock_lines_button.config(state='normal')
        
        # Update display to show confirmed lines (green)
        if self.original_image:
            self.display_image()
            
        self.update_status(f"Lines confirmed! {self.num_lines} lines locked at {self.line_spacing_cm:.1f}cm spacing")
    
    def unlock_lines(self):
        """Unlock the lines for modification"""
        self.lines_confirmed = False
        
        # Re-enable line modification controls
        self.lines_scale.config(state='normal')
        # Find and enable the spacing spinbox
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                self._enable_spacing_controls(child)
        
        self.confirm_lines_button.config(state='normal')
        self.unlock_lines_button.config(state='disabled')
        
        # Update display to show editable lines (red)
        if self.original_image:
            self.display_image()
            
        self.update_status("Lines unlocked - you can now modify line count and positions")
    
    def reset_line_positions(self):
        """Reset all line positions to default equally spaced layout"""
        if not self.original_image:
            self.update_status("Load an image first")
            return
        
        if self.lines_confirmed:
            self.update_status("Unlock lines first to reset positions")
            return
        
        # Clear current positions to force recalculation
        self.line_positions = []
        
        if self.original_image:
            self.display_image()
        
        self.update_status("Line positions reset to equal spacing")
    
    def reset_equal_spacing(self):
        """Reset lines to equal spacing based on current spacing setting"""
        if not self.original_image:
            self.update_status("Load an image first")
            return
        
        if self.lines_confirmed:
            self.update_status("Unlock lines first to reset spacing")
            return
        
        # Force recalculation with current spacing
        self.line_positions = []
        
        if self.original_image:
            self.display_image()
        
        self.update_status(f"Lines respaced equally at {self.line_spacing_cm:.1f}cm intervals")
    
    def _disable_spacing_controls(self, widget):
        """Helper to recursively disable spacing controls"""
        try:
            if isinstance(widget, tk.Spinbox) and hasattr(widget, 'get'):
                if widget.get() == self.spacing_var.get():
                    widget.config(state='disabled')
            for child in widget.winfo_children():
                self._disable_spacing_controls(child)
        except:
            pass
    
    def _enable_spacing_controls(self, widget):
        """Helper to recursively enable spacing controls"""
        try:
            if isinstance(widget, tk.Spinbox) and hasattr(widget, 'get'):
                widget.config(state='normal')
            for child in widget.winfo_children():
                self._enable_spacing_controls(child)
        except:
            pass
    
    def update_brush_size(self, value):
        """Update brush size"""
        self.brush_size = int(float(value))
        if hasattr(self, 'brush_value_label'):
            self.brush_value_label.config(text=f"{self.brush_size}px")
    
    def set_spacing_preset(self, value):
        """Set line spacing to a preset value"""
        self.spacing_var.set(value)
        self.update_line_spacing()
    
    def update_lines_count(self, value):
        """Update number of vertical lines with visual feedback"""
        if self.lines_confirmed:
            return  # Don't allow changes when lines are confirmed
            
        try:
            self.num_lines = int(float(value))
            if hasattr(self, 'lines_count_label') and self.lines_count_label:
                self.lines_count_label.config(text=str(self.num_lines))
            
            if self.show_lines and self.original_image:
                self.display_image()
            
            self.update_status(f"Lines count updated to {self.num_lines}")
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error updating lines count: {value}, error: {e}")
            self.num_lines = 5  # Reset to default
            if hasattr(self, 'lines_count_label') and self.lines_count_label:
                self.lines_count_label.config(text="5")
            self.update_status("Error updating line count - reset to 5")
    
    def update_line_spacing(self):
        """Update the spacing between vertical lines with visual feedback"""
        if self.lines_confirmed:
            return  # Don't allow changes when lines are confirmed
            
        try:
            if self.spacing_var:
                self.line_spacing_cm = float(self.spacing_var.get())
                if hasattr(self, 'spacing_value_label') and self.spacing_value_label:
                    self.spacing_value_label.config(text=f"{self.line_spacing_cm:.1f}cm")
                
                if self.show_lines and self.original_image:
                    self.display_image()
                
                self.update_status(f"Line spacing updated to {self.line_spacing_cm:.1f}cm")
        except (ValueError, AttributeError, TypeError) as e:
            # Reset to default if invalid value
            print(f"Error updating line spacing: {e}")
            if self.spacing_var:
                self.spacing_var.set("5.0")
            self.line_spacing_cm = 5.0
            if hasattr(self, 'spacing_value_label') and self.spacing_value_label:
                self.spacing_value_label.config(text="5.0cm")
            self.update_status("Error updating line spacing - reset to 5.0cm")
    
    def toggle_snap(self):
        """Toggle grid snapping"""
        self.snap_to_grid = self.snap_var.get()
        self.update_status(f"Grid snapping {'enabled' if self.snap_to_grid else 'disabled'}")
    
    def update_grid_size_cm(self):
        """Update grid size in centimeters"""
        try:
            self.grid_size_cm = float(self.grid_cm_var.get())
            if self.show_grid and self.original_image:
                self.display_image()
        except ValueError:
            self.grid_cm_var.set("1.0")
            self.grid_size_cm = 1.0
    
    def toggle_show_grid(self):
        """Toggle grid display"""
        self.show_grid = self.grid_show_var.get()
        if self.original_image:
            self.display_image()
    
    def refresh_dpi_dependent_elements(self):
        """Refresh all elements that depend on DPI after DPI change"""
        if not self.original_image:
            return
            
        # Redraw grid if visible
        if self.show_grid:
            self.display_image()
        
        # Update ruler measurement if ruler is active
        if self.show_ruler and self.ruler_start and self.ruler_end:
            # Recalculate ruler measurement with new DPI
            _, real_pixels, cm_distance = self.calculate_distance(
                self.ruler_start[0], self.ruler_start[1],
                self.ruler_end[0], self.ruler_end[1]
            )
            measurement_text = f"Distance: {real_pixels:.1f} px ({cm_distance:.2f} cm)"
            self.ruler_measurement_var.set(measurement_text)
            
            # Redraw ruler with updated measurement
            if hasattr(self, 'canvas'):
                self.canvas.delete("ruler")
                self.draw_ruler()
        
        # Update any section measurements if they exist
        self.update_sections_list()
    
    def update_dpi(self):
        """Update image DPI for accurate measurements - UNLIMITED VALUES!"""
        try:
            old_dpi = self.image_dpi
            new_dpi = int(float(self.dpi_var.get()))  # Handle decimal inputs too
            
            # Accept ANY positive DPI value - no limits!
            if new_dpi > 0:
                self.image_dpi = new_dpi
                
                # If DPI actually changed, update all DPI-dependent elements
                if old_dpi != self.image_dpi:
                    self.refresh_dpi_dependent_elements()
                    
                    # Provide informative feedback about the DPI value
                    if new_dpi < 50:
                        self.update_status(f"Image DPI set to {self.image_dpi} (very low resolution - was {old_dpi})")
                    elif new_dpi > 2400:
                        self.update_status(f"Image DPI set to {self.image_dpi} (very high resolution - was {old_dpi})")
                    else:
                        self.update_status(f"Image DPI set to {self.image_dpi} (was {old_dpi})")
            else:
                self.update_status("DPI must be positive - keeping current value")
                self.dpi_var.set(str(self.image_dpi))
                
        except (ValueError, TypeError):
            self.dpi_var.set("300")
            self.image_dpi = 300
            self.update_status("Invalid DPI value, reset to 300")
    
    def toggle_show_ruler(self):
        """Toggle ruler display"""
        self.show_ruler = self.ruler_show_var.get()
        if not self.show_ruler:
            # Clear ruler when disabled
            self.ruler_start = None
            self.ruler_end = None
            self.ruler_measurement_var.set("Click and drag to measure")
        if self.original_image:
            self.display_image()
        
        status = "enabled" if self.show_ruler else "disabled"
        self.update_status(f"Measurement ruler {status}")
    
    def pixels_to_cm(self, pixels):
        """Convert pixels to centimeters based on current DPI"""
        inches = pixels / self.image_dpi
        return inches * 2.54  # Convert inches to cm
    
    def cm_to_pixels(self, cm):
        """Convert centimeters to pixels based on current DPI"""
        inches = cm / 2.54  # Convert cm to inches
        return inches * self.image_dpi
    
    def get_grid_spacing_pixels(self):
        """Get grid spacing in pixels (always cm based)"""
        return self.cm_to_pixels(self.grid_size_cm)
    
    def calculate_distance(self, x1, y1, x2, y2):
        """Calculate distance between two points and return in both pixels and cm"""
        # Calculate pixel distance in image coordinates
        real_pixel_distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        
        # Convert to display pixel distance (for visual reference)
        display_pixel_distance = real_pixel_distance * self.image_scale
        
        # Convert real pixels to centimeters
        cm_distance = self.pixels_to_cm(real_pixel_distance)
        
        return display_pixel_distance, real_pixel_distance, cm_distance
    
    def toggle_precise_mode(self):
        """Toggle precise mode for sub-pixel positioning"""
        self.precise_mode = self.precise_var.get()
        self.update_status(f"Precise mode {'enabled' if self.precise_mode else 'disabled'} - allows sub-pixel positioning")
    
    def toggle_smooth_movement(self):
        """Toggle smooth movement buffering"""
        enabled = self.smooth_var.get()
        if enabled:
            self.update_status("Smooth movement enabled - fluid motion activated")
        else:
            # Clear buffer when disabled
            self.movement_buffer = []
            self.update_status("Smooth movement disabled - direct movement mode")
    
    def snap_to_grid_position(self, x, y):
        """Snap coordinates to grid if snapping is enabled"""
        if not self.snap_to_grid:
            return x, y
        
        # Get grid spacing based on current unit
        grid_spacing = self.get_grid_spacing_pixels()
        
        # Snap to nearest grid point
        snapped_x = round(x / grid_spacing) * grid_spacing
        snapped_y = round(y / grid_spacing) * grid_spacing
        return snapped_x, snapped_y
    
    def add_movement_to_buffer(self, dx, dy):
        """Add movement to buffer for smoothing"""
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Add movement to buffer
        self.movement_buffer.append((dx, dy, current_time))
        
        # Keep buffer size limited
        if len(self.movement_buffer) > self.buffer_size:
            self.movement_buffer.pop(0)
    
    def get_smoothed_movement(self):
        """Get smoothed movement from buffer"""
        if not self.movement_buffer:
            return 0, 0
        
        # Calculate weighted average of recent movements
        total_weight = 0
        smooth_dx = 0
        smooth_dy = 0
        
        for i, (dx, dy, timestamp) in enumerate(self.movement_buffer):
            # Give more weight to recent movements
            weight = (i + 1) / len(self.movement_buffer)
            smooth_dx += dx * weight
            smooth_dy += dy * weight
            total_weight += weight
        
        if total_weight > 0:
            smooth_dx /= total_weight
            smooth_dy /= total_weight
        
        return smooth_dx, smooth_dy
    
    def should_update_display(self):
        """Check if enough time has passed to update display (frame rate limiting)"""
        import time
        current_time = time.time() * 1000  # Convert to milliseconds
        
        if current_time - self.last_update_time >= self.min_update_interval:
            self.last_update_time = current_time
            return True
        return False
    
    def interpolate_movement(self, section_idx, target_dx, target_dy):
        """Smoothly interpolate movement to target position"""
        if not self.movement_interpolation or section_idx >= len(self.clipped_sections):
            # Direct movement if interpolation is disabled
            self.move_clipped_section_direct(section_idx, target_dx, target_dy)
            return
        
        # Divide movement into smaller steps for smooth animation
        step_dx = target_dx / self.interpolation_steps
        step_dy = target_dy / self.interpolation_steps
        
        def animate_step(step):
            if step < self.interpolation_steps and section_idx < len(self.clipped_sections):
                self.move_clipped_section_direct(section_idx, step_dx, step_dy)
                # Schedule next step
                self.root.after(5, lambda: animate_step(step + 1))
        
        # Start animation
        animate_step(0)
        
    def update_opacity(self, value):
        """Update color opacity with enhanced feedback"""
        self.color_opacity = float(value)
        percentage = int(self.color_opacity * 100)
        if hasattr(self, 'opacity_label'):
            self.opacity_label.configure(text=f"{percentage}%")
        
    def choose_color(self):
        """Open color chooser dialog"""
        color = colorchooser.askcolor(color=self.selected_color)
        if color[1]:  # If a color was selected
            self.selected_color = color[1]
            self.color_button.configure(bg=self.selected_color)
            
    def clear_selections(self):
        """Clear all clipped sections"""
        self.clipped_sections = []
        self.update_sections_list()
        if self.original_image:
            self.working_image = self.original_image.copy()
            self.display_image()
            
    def undo_last_selection(self):
        """Remove the last clipped section"""
        if self.clipped_sections:
            self.clipped_sections.pop()
            self.update_sections_list()
            # Rebuild the working image
            self.rebuild_working_image()
            self.display_image()
            
    def rebuild_working_image(self):
        """Rebuild the working image with current clipped sections"""
        if not self.original_image:
            return
            
        self.working_image = self.original_image.copy()
        
        # Create holes for all clipped sections
        for section in self.clipped_sections:
            # Use the original boundary to create holes (fill with white)
            working_draw = ImageDraw.Draw(self.working_image)
            pil_path = [(int(x), int(y)) for x, y in section['boundary']]
            working_draw.polygon(pil_path, fill=(255, 255, 255))  # Fill with white background
        
        # Clear caches to force refresh
        self.display_cache.clear()
        self.image_pyramid.clear()
            
    def reset_image(self):
        """Reset the working image to the original"""
        if self.original_image:
            result = messagebox.askyesno("Reset Image", 
                                       "This will reset the image to its original state and remove all clipped sections. Continue?")
            if result:
                self.working_image = self.original_image.copy()
                self.clipped_sections = []
                self.update_sections_list()
                self.display_image()
                messagebox.showinfo("Reset", "Image has been reset to original state")
            
    def update_sections_list(self):
        """Update the sections listbox with enhanced formatting"""
        self.sections_listbox.delete(0, tk.END)
        
        for i, section in enumerate(self.clipped_sections):
            # Enhanced section display with more info
            width, height = section['size']
            color_name = section['color']
            section_text = f"📄 Section {i+1:02d} • {color_name} • {width}×{height}px"
            self.sections_listbox.insert(tk.END, section_text)
        
        # Update counters and stats
        count = len(self.clipped_sections)
        if hasattr(self, 'sections_count_label'):
            self.sections_count_label.config(text=f"📊 Total Sections: {count}")
        
        if hasattr(self, 'stats_label'):
            if count == 0:
                self.stats_label.config(text="No sections created yet")
            else:
                total_pixels = sum(s['size'][0] * s['size'][1] for s in self.clipped_sections)
                self.stats_label.config(text=f"{count} sections • {total_pixels:,} total pixels")
            
    def on_section_select(self, event):
        """Handle section selection in listbox with better feedback"""
        selection = self.sections_listbox.curselection()
        if selection:
            self.selected_section = selection[0]
            section = self.clipped_sections[self.selected_section]
            x, y = section['position']
            width, height = section['size']
            
            # Convert to centimeters for display
            x_cm = self.pixels_to_cm(x)
            y_cm = self.pixels_to_cm(y)
            width_cm = self.pixels_to_cm(width)
            height_cm = self.pixels_to_cm(height)
            
            # Update status with section info in cm
            if self.current_mode == "move":
                self.update_status(f"Selected section {self.selected_section + 1} at ({x_cm:.2f}, {y_cm:.2f}) cm • Size: {width_cm:.2f}×{height_cm:.2f} cm • Ready to move")
            else:
                self.update_status(f"Selected section {self.selected_section + 1} • Switch to Move mode to reposition")
            
            # Update precision movement info in cm
            if hasattr(self, 'selected_info_var'):
                self.selected_info_var.set(f"Section {self.selected_section + 1} at ({x_cm:.2f}, {y_cm:.2f}) cm")
            
            # Refresh display to show selection highlight
            self.display_image()
        else:
            self.selected_section = None
            # Update precision movement info
            if hasattr(self, 'selected_info_var'):
                self.selected_info_var.set("No section selected")
            
    def delete_selected_section(self):
        """Delete the selected clipped section"""
        selection = self.sections_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(self.clipped_sections):
                self.clipped_sections.pop(idx)
                self.update_sections_list()
                self.rebuild_working_image()
                self.display_image()
                
    def change_section_color(self):
        """Change color of selected clipped section"""
        selection = self.sections_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(self.clipped_sections):
                color = colorchooser.askcolor()
                if color[1]:
                    section = self.clipped_sections[idx]
                    old_color = section['color']
                    section['color'] = color[1]
                    
                    # Recreate the section with new color
                    # Get the original area again
                    mask = Image.new('L', self.original_image.size, 0)
                    draw = ImageDraw.Draw(mask)
                    pil_path = [(int(x), int(y)) for x, y in section['boundary']]
                    draw.polygon(pil_path, fill=255)
                    
                    selected_area = Image.composite(self.original_image, Image.new('RGB', self.original_image.size, (255, 255, 255)), mask)
                    
                    # Create new colored overlay
                    overlay = Image.new('RGBA', self.original_image.size, (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    
                    hex_color = color[1].lstrip('#')
                    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    rgba_color = rgb_color + (77,)  # 30% opacity
                    
                    overlay_draw.polygon(pil_path, fill=rgba_color)
                    
                    # Blend new color
                    selected_rgba = selected_area.convert('RGBA')
                    colored_section = Image.alpha_composite(selected_rgba, overlay)
                    
                    # Update the section image
                    bbox = mask.getbbox()
                    if bbox:
                        section['image'] = colored_section.crop(bbox)
                    
                    self.update_sections_list()
                    self.display_image()
                
    def save_project(self):
        """Save current project to JSON file"""
        if not self.clipped_sections:
            messagebox.showwarning("Warning", "No clipped sections to save")
            return
            
        if self.is_macos:
            file_path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save Project",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*")]
            )
        else:
            file_path = filedialog.asksaveasfilename(
                title="Save Project",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        
        if file_path:
            try:
                # Convert clipped sections to serializable format
                serializable_sections = []
                for section in self.clipped_sections:
                    serializable_sections.append({
                        'position': section['position'],
                        'size': section['size'],
                        'boundary': section['boundary'],
                        'color': section['color'],
                        'id': section['id']
                    })
                
                project_data = {
                    'clipped_sections': serializable_sections,
                    'image_scale': self.image_scale
                }
                
                with open(file_path, 'w') as f:
                    json.dump(project_data, f, indent=2)
                    
                messagebox.showinfo("Success", "Project saved successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project: {str(e)}")
                
    def load_project(self):
        """Load project from JSON file"""
        if self.is_macos:
            file_path = filedialog.askopenfilename(
                parent=self.root,
                title="Load Project",
                filetypes=[("JSON files", "*.json"), ("All files", "*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="Load Project",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    project_data = json.load(f)
                    
                # Note: Loading projects will require the same original image
                # The clipped section images cannot be perfectly reconstructed
                messagebox.showinfo("Note", "Project loading requires the same original image. Clipped sections will be recreated from boundary data.")
                
                self.image_scale = project_data.get('image_scale', 1.0)
                
                if self.original_image:
                    self.display_image()
                    
                messagebox.showinfo("Success", "Project metadata loaded successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load project: {str(e)}")
                
    def export_image(self):
        """Export the current working image with optional grid/lines overlay"""
        if self.working_image is None:
            messagebox.showwarning("Warning", "No image to export")
            return
        
        # Check if overlays are active
        has_overlays = (self.show_grid or 
                       (self.show_lines and hasattr(self, 'line_positions')) or
                       (hasattr(self, 'clipped_sections') and self.clipped_sections))
        
        # If overlays are present, ask user if they want to include them
        include_overlays = False
        if has_overlays:
            overlay_types = []
            if self.show_grid:
                overlay_types.append("grid")
            if self.show_lines and hasattr(self, 'line_positions'):
                overlay_types.append("vertical lines")
            if hasattr(self, 'clipped_sections') and self.clipped_sections:
                overlay_types.append("colored selections")
            
            overlay_text = " and ".join(overlay_types)
            result = messagebox.askyesnocancel(
                "Export Options", 
                f"You have {overlay_text} visible on your image.\n\n"
                f"Do you want to include the overlay(s) in the exported image?\n\n"
                f"• Yes: Export image WITH overlays\n"
                f"• No: Export image WITHOUT overlays\n"
                f"• Cancel: Cancel export"
            )
            if result is None:  # Cancel
                return
            include_overlays = result
            
        if self.is_macos:
            file_path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Export Image",
                defaultextension=".tiff",
                filetypes=[("TIFF files", "*.tiff *.tif"), ("PNG files", "*.png"), 
                          ("JPEG files", "*.jpg *.jpeg"), ("All files", "*")]
            )
        else:
            file_path = filedialog.asksaveasfilename(
                title="Export Image",
                defaultextension=".tiff",
                filetypes=[("TIFF files", "*.tiff"), ("PNG files", "*.png"), 
                          ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
        
        if file_path:
            try:
                # Create the image to export
                if include_overlays and has_overlays:
                    self.update_status("Creating image with overlays...")
                    export_image = self._create_image_with_overlays()
                    self.update_status("Overlays applied successfully!")
                else:
                    export_image = self.working_image.copy()
                
                # Verify export dimensions
                export_width, export_height = export_image.size
                original_width, original_height = self.original_image.size
                export_mp = (export_width * export_height) / 1_000_000
                
                export_image.save(file_path)
                
                # Create success message with overlay info
                overlay_info = ""
                if include_overlays and has_overlays:
                    overlay_types = []
                    if self.show_grid:
                        overlay_types.append("grid")
                    if self.show_lines and hasattr(self, 'line_positions'):
                        overlay_types.append("vertical lines")
                    overlay_info = f"Overlays included: {', '.join(overlay_types)}\n"
                
                # Confirm full quality export
                if export_width == original_width and export_height == original_height:
                    messagebox.showinfo("Success", 
                        f"Full resolution image exported successfully!\n\n"
                        f"Resolution: {export_width:,}×{export_height:,} ({export_mp:.1f}MP)\n"
                        f"{overlay_info}"
                        f"Location: {file_path}")
                else:
                    messagebox.showinfo("Success", 
                        f"Image exported successfully!\n\n"
                        f"Export resolution: {export_width:,}×{export_height:,} ({export_mp:.1f}MP)\n"
                        f"Original resolution: {original_width:,}×{original_height:,}\n"
                        f"{overlay_info}"
                        f"Location: {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image: {str(e)}")
    
    def _create_image_with_overlays(self):
        """Create a copy of the working image with grid and/or lines drawn on it"""
        # For overlays with clipped sections, we want to start with the original image
        # and then apply both the sections and other overlays
        if hasattr(self, 'clipped_sections') and self.clipped_sections:
            # Start with original image, then apply sections and overlays
            overlay_image = self.original_image.copy()
        else:
            # No sections, just use working image
            overlay_image = self.working_image.copy()
        
        draw = ImageDraw.Draw(overlay_image)
        
        # Get image dimensions
        img_width, img_height = overlay_image.size
        
        # Draw vertical lines if they're shown
        if self.show_lines and hasattr(self, 'line_positions') and self.line_positions:
            line_color = (0, 255, 0) if self.lines_confirmed else (255, 0, 0)  # Green if confirmed, red if not
            line_width = max(1, int(min(img_width, img_height) / 1000))  # Scale line width with image size
            if self.lines_confirmed:
                line_width = max(2, line_width)  # Confirmed lines are thicker
            
            for x_pos in self.line_positions:
                # Convert to integer and ensure line position is within image bounds
                x_pos_int = int(round(x_pos))
                if 0 <= x_pos_int <= img_width:
                    # Draw line from top to bottom
                    draw.line([(x_pos_int, 0), (x_pos_int, img_height-1)], 
                             fill=line_color, width=line_width)
        
        # Draw grid if it's shown
        if self.show_grid and self.original_image and hasattr(self, 'image_dpi'):
            try:
                # Calculate grid spacing in pixels (always use cm now)
                grid_spacing_real = self.cm_to_pixels(self.grid_size_cm)
                
                # Ensure grid spacing is reasonable
                if grid_spacing_real > 0 and grid_spacing_real < min(img_width, img_height):
                    # Scale line width based on image size
                    base_line_width = max(1, int(min(img_width, img_height) / 2000))
                    
                    # Draw vertical grid lines
                    x = 0
                    line_count = 0
                    while x <= img_width and line_count < 1000:  # Safety limit
                        # Make every 5th line slightly thicker for major grid lines
                        line_width = base_line_width * 2 if line_count % 5 == 0 else base_line_width
                        line_color = (100, 100, 100) if line_count % 5 == 0 else (180, 180, 180)  # Gray colors
                        
                        x_int = int(round(x))
                        if x_int <= img_width:  # Only draw if within bounds
                            draw.line([(x_int, 0), (x_int, img_height-1)], 
                                     fill=line_color, width=line_width)
                        x += grid_spacing_real
                        line_count += 1
                    
                    # Draw horizontal grid lines
                    y = 0
                    line_count = 0
                    while y <= img_height and line_count < 1000:  # Safety limit
                        # Make every 5th line slightly thicker for major grid lines
                        line_width = base_line_width * 2 if line_count % 5 == 0 else base_line_width
                        line_color = (100, 100, 100) if line_count % 5 == 0 else (180, 180, 180)  # Gray colors
                        
                        y_int = int(round(y))
                        if y_int <= img_height:  # Only draw if within bounds
                            draw.line([(0, y_int), (img_width-1, y_int)], 
                                     fill=line_color, width=line_width)
                        y += grid_spacing_real
                        line_count += 1
            except Exception as e:
                print(f"Warning: Could not draw grid overlay: {e}")
                # Continue without grid if there's an error
        
        # Draw clipped sections (colored selections) if they exist
        if hasattr(self, 'clipped_sections') and self.clipped_sections:
            try:
                for section in self.clipped_sections:
                    # Get section position and size
                    pos_x, pos_y = section['position']
                    section_image = section['image']
                    
                    # Ensure position is within image bounds
                    if (pos_x >= 0 and pos_y >= 0 and 
                        pos_x < img_width and pos_y < img_height):
                        
                        # Calculate the area to paste (clip to image bounds if necessary)
                        sect_width, sect_height = section_image.size
                        end_x = min(pos_x + sect_width, img_width)
                        end_y = min(pos_y + sect_height, img_height)
                        
                        # Crop section image if it extends beyond bounds
                        if end_x < pos_x + sect_width or end_y < pos_y + sect_height:
                            crop_width = end_x - pos_x
                            crop_height = end_y - pos_y
                            section_image = section_image.crop((0, 0, crop_width, crop_height))
                        
                        # Paste the section onto the overlay image
                        if section_image.mode == 'RGBA':
                            overlay_image.paste(section_image, (int(pos_x), int(pos_y)), section_image)
                        else:
                            overlay_image.paste(section_image, (int(pos_x), int(pos_y)))
            except Exception as e:
                print(f"Warning: Could not draw clipped sections overlay: {e}")
                # Continue without sections if there's an error
        
        return overlay_image
    
    def load_multiple_files(self):
        """Load multiple TIFF files for merging"""
        # macOS fix: add parent parameter
        if self.is_macos:
            file_paths = filedialog.askopenfilenames(
                parent=self.root,
                title="Select Multiple TIFF Images to Merge",
                filetypes=[("TIFF files", "*.tiff *.tif *.TIF *.TIFF"), ("All files", "*")]
            )
        else:
            file_paths = filedialog.askopenfilenames(
                title="Select Multiple TIFF Images to Merge",
                filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
            )
        
        if file_paths:
            self.loaded_files = list(file_paths)
            self.loaded_images = []
            
            try:
                self.update_status("Loading images for merge...")
                
                # Load all images with better error handling and no size limits
                loaded_count = 0
                failed_files = []
                
                # Temporarily disable PIL limits for all images
                original_max_pixels = Image.MAX_IMAGE_PIXELS
                Image.MAX_IMAGE_PIXELS = None
                
                for i, file_path in enumerate(self.loaded_files):
                    try:
                        self.update_status(f"Loading image {i+1}/{len(self.loaded_files)}: {os.path.basename(file_path)}")
                        
                        img = Image.open(file_path)
                        width, height = img.size
                        megapixels = (width * height) / 1_000_000
                        
                        if megapixels > 100:  # Show info for very large images
                            self.update_status(f"Loading large image {i+1}: {width:,}×{height:,} ({megapixels:.1f}MP)")
                        
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        self.loaded_images.append(img)
                        loaded_count += 1
                    except Exception as file_error:
                        error_msg = str(file_error)
                        if "exceeds limit" in error_msg.lower():
                            error_msg = "Size limit bypassed but still failed - possibly memory issue"
                        failed_files.append(f"{os.path.basename(file_path)}: {error_msg}")
                        continue
                
                # Restore original setting
                Image.MAX_IMAGE_PIXELS = original_max_pixels
                
                if failed_files:
                    error_msg = "Some files failed to load:\n" + "\n".join(failed_files[:5])
                    if len(failed_files) > 5:
                        error_msg += f"\n... and {len(failed_files) - 5} more"
                    messagebox.showwarning("Loading Issues", error_msg)
                
                if loaded_count == 0:
                    raise Exception("No images could be loaded")
                
                # Remove failed files from the list
                if failed_files:
                    successful_files = []
                    for i, file_path in enumerate(self.loaded_files):
                        if i < len(self.loaded_images):
                            successful_files.append(file_path)
                    self.loaded_files = successful_files
                
                self.update_status(f"Loaded {loaded_count} images. Opening merge preview...")
                
                # Initialize position and scale arrays
                self.image_positions = []
                self.image_scales = []
                
                # Open merge preview window
                self.open_merge_preview()
                
            except Exception as e:
                self.update_status("Failed to load images")
                messagebox.showerror("Error", f"Failed to load images: {str(e)}")
                self.loaded_files = []
                self.loaded_images = []
                self.image_positions = []
                self.image_scales = []
    
    def open_merge_preview(self):
        """Open preview window for arranging images before merge"""
        if self.merge_preview_window:
            self.merge_preview_window.destroy()
        
        self.merge_preview_window = tk.Toplevel(self.root)
        self.merge_preview_window.title("🔄 Merge Images Preview")
        self.merge_preview_window.geometry("900x700")
        self.merge_preview_window.configure(bg='#f0f0f0')
        
        # Make window modal
        self.merge_preview_window.transient(self.root)
        self.merge_preview_window.grab_set()
        
        # Header
        header_frame = tk.Frame(self.merge_preview_window, bg='#2563eb', height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📁 Merge Multiple Images", 
                              font=('Arial', 14, 'bold'), bg='#2563eb', fg='white')
        title_label.pack(expand=True)
        
        # Main content
        content_frame = tk.Frame(self.merge_preview_window, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left panel - File list and settings
        left_panel = tk.Frame(content_frame, bg='#f0f0f0', width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)
        
        # Files section
        files_section = tk.LabelFrame(left_panel, text="📄 Selected Files", 
                                     font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                     padx=10, pady=10)
        files_section.pack(fill=tk.X, pady=(0, 15))
        
        # File list
        self.merge_files_listbox = tk.Listbox(files_section, height=6, font=('Arial', 9))
        for i, file_path in enumerate(self.loaded_files):
            filename = os.path.basename(file_path)
            img_size = self.loaded_images[i].size
            self.merge_files_listbox.insert(tk.END, f"{i+1}. {filename} ({img_size[0]}×{img_size[1]})")
        self.merge_files_listbox.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_controls_frame = tk.Frame(files_section, bg='#f0f0f0')
        file_controls_frame.pack(fill=tk.X)
        
        tk.Button(file_controls_frame, text="➕ Add More", command=self.add_more_files,
                 bg='#4CAF50', fg='white', font=('Arial', 8), padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(file_controls_frame, text="🗑️ Remove", command=self.remove_selected_file,
                 bg='#f44336', fg='white', font=('Arial', 8), padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(file_controls_frame, text="🔄 Reorder", command=self.reorder_files,
                 bg='#FF9800', fg='white', font=('Arial', 8), padx=8, pady=2).pack(side=tk.LEFT)
        
        # Merge settings section
        settings_section = tk.LabelFrame(left_panel, text="⚙️ Merge Settings", 
                                        font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                        padx=10, pady=10)
        settings_section.pack(fill=tk.X, pady=(0, 15))
        
        # Arrangement options
        tk.Label(settings_section, text="Arrangement:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W, pady=(0, 5))
        
        self.merge_arrangement_var = tk.StringVar(value="horizontal")
        
        arrange_frame = tk.Frame(settings_section, bg='#f0f0f0')
        arrange_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Radiobutton(arrange_frame, text="➡️ Horizontal", variable=self.merge_arrangement_var, 
                      value="horizontal", command=self.on_arrangement_change,
                      bg='#f0f0f0', font=('Arial', 9)).pack(anchor=tk.W)
        
        tk.Radiobutton(arrange_frame, text="⬇️ Vertical", variable=self.merge_arrangement_var, 
                      value="vertical", command=self.on_arrangement_change,
                      bg='#f0f0f0', font=('Arial', 9)).pack(anchor=tk.W)
        
        tk.Radiobutton(arrange_frame, text="🎛️ Grid (Auto)", variable=self.merge_arrangement_var, 
                      value="grid", command=self.on_arrangement_change,
                      bg='#f0f0f0', font=('Arial', 9)).pack(anchor=tk.W)
        
        tk.Radiobutton(arrange_frame, text="🎨 Free-form (Drag & Drop)", variable=self.merge_arrangement_var, 
                      value="freeform", command=self.switch_to_freeform_mode,
                      bg='#f0f0f0', font=('Arial', 9, 'bold'), fg='#2563eb').pack(anchor=tk.W)
        
        # Spacing control
        spacing_frame = tk.Frame(settings_section, bg='#f0f0f0')
        spacing_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(spacing_frame, text="Spacing:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.merge_spacing_var = tk.StringVar(value="10")
        spacing_spinbox = tk.Spinbox(spacing_frame, from_=0, to=100, increment=5,
                                    textvariable=self.merge_spacing_var, width=8,
                                    command=self.update_merge_preview, font=('Arial', 9))
        spacing_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        spacing_spinbox.bind('<Return>', lambda e: self.update_merge_preview())
        
        tk.Label(spacing_frame, text="px", font=('Arial', 9),
                bg='#f0f0f0').pack(side=tk.LEFT)
        
        # Canvas size controls (for free-form mode) - initially hidden
        self.canvas_size_frame = tk.Frame(settings_section, bg='#f0f0f0')
        
        tk.Label(self.canvas_size_frame, text="Canvas Size (Free-form):", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W, pady=(10, 5))
        
        canvas_size_controls = tk.Frame(self.canvas_size_frame, bg='#f0f0f0')
        canvas_size_controls.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(canvas_size_controls, text="Width:", font=('Arial', 9),
                bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.canvas_width_var = tk.StringVar(value="2000")
        width_spinbox = tk.Spinbox(canvas_size_controls, from_=500, to=10000, increment=100,
                                  textvariable=self.canvas_width_var, width=8,
                                  font=('Arial', 9))
        width_spinbox.pack(side=tk.LEFT, padx=(5, 10))
        
        tk.Label(canvas_size_controls, text="Height:", font=('Arial', 9),
                bg='#f0f0f0').pack(side=tk.LEFT)
        
        self.canvas_height_var = tk.StringVar(value="1500")
        height_spinbox = tk.Spinbox(canvas_size_controls, from_=500, to=10000, increment=100,
                                   textvariable=self.canvas_height_var, width=8,
                                   font=('Arial', 9))
        height_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        
        tk.Label(canvas_size_controls, text="px", font=('Arial', 9),
                bg='#f0f0f0').pack(side=tk.LEFT)
        
        # Right panel - Preview
        preview_panel = tk.Frame(content_frame, bg='white', relief='solid', bd=1)
        preview_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Preview header
        preview_header = tk.Frame(preview_panel, bg='#e0e0e0', height=40)
        preview_header.pack(fill=tk.X)
        preview_header.pack_propagate(False)
        
        tk.Label(preview_header, text="👁️ Merge Preview", font=('Arial', 10, 'bold'),
                bg='#e0e0e0', fg='#333').pack(expand=True)
        
        # Preview canvas
        self.merge_preview_canvas = tk.Canvas(preview_panel, bg='white')
        
        # Scrollbars for preview
        v_scroll = tk.Scrollbar(preview_panel, orient=tk.VERTICAL, command=self.merge_preview_canvas.yview)
        h_scroll = tk.Scrollbar(preview_panel, orient=tk.HORIZONTAL, command=self.merge_preview_canvas.xview)
        
        self.merge_preview_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.merge_preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Summary section
        summary_section = tk.LabelFrame(left_panel, text="📊 Merge Summary", 
                                       font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                       padx=10, pady=10)
        summary_section.pack(fill=tk.X, pady=(0, 15))
        
        self.merge_summary_label = tk.Label(summary_section, text="", 
                                           font=('Arial', 9), bg='#f0f0f0', fg='#666',
                                           justify=tk.LEFT, anchor=tk.W)
        self.merge_summary_label.pack(fill=tk.X)
        
        # Bottom buttons
        buttons_frame = tk.Frame(self.merge_preview_window, bg='#f0f0f0')
        buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        tk.Button(buttons_frame, text="❌ Cancel", command=self.cancel_merge,
                 bg='#6c757d', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.LEFT)
        
        tk.Button(buttons_frame, text="🔄 Update Preview", command=self.update_merge_preview,
                 bg='#17a2b8', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(buttons_frame, text="✅ Confirm Merge", command=self.confirm_merge,
                 bg='#28a745', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.RIGHT)
        
        # Initial preview
        self.update_merge_preview()
    
    def add_more_files(self):
        """Add more files to the merge list"""
        if self.is_macos:
            file_paths = filedialog.askopenfilenames(
                parent=self.root if hasattr(self, 'root') else self.merge_preview_window,
                title="Select Additional TIFF Images",
                filetypes=[("TIFF files", "*.tiff *.tif *.TIF *.TIFF"), ("All files", "*")]
            )
        else:
            file_paths = filedialog.askopenfilenames(
                title="Select Additional TIFF Images",
                filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
            )
        
        if file_paths:
            try:
                for file_path in file_paths:
                    if file_path not in self.loaded_files:
                        img = Image.open(file_path)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        self.loaded_files.append(file_path)
                        self.loaded_images.append(img)
                
                # Update file list
                self.merge_files_listbox.delete(0, tk.END)
                for i, file_path in enumerate(self.loaded_files):
                    filename = os.path.basename(file_path)
                    img_size = self.loaded_images[i].size
                    self.merge_files_listbox.insert(tk.END, f"{i+1}. {filename} ({img_size[0]}×{img_size[1]})")
                
                self.update_merge_preview()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load additional images: {str(e)}")
    
    def remove_selected_file(self):
        """Remove selected file from merge list"""
        selection = self.merge_files_listbox.curselection()
        if selection and len(self.loaded_files) > 1:
            idx = selection[0]
            
            # Remove from lists
            self.loaded_files.pop(idx)
            self.loaded_images.pop(idx)
            
            # Update file list
            self.merge_files_listbox.delete(0, tk.END)
            for i, file_path in enumerate(self.loaded_files):
                filename = os.path.basename(file_path)
                img_size = self.loaded_images[i].size
                self.merge_files_listbox.insert(tk.END, f"{i+1}. {filename} ({img_size[0]}×{img_size[1]})")
            
            self.update_merge_preview()
        elif len(self.loaded_files) <= 1:
            messagebox.showwarning("Warning", "Cannot remove - at least one image is required")
    
    def reorder_files(self):
        """Simple reorder by moving selected item up or down"""
        selection = self.merge_files_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a file to reorder")
            return
        
        idx = selection[0]
        
        # Ask user whether to move up or down
        choice = messagebox.askyesnocancel("Reorder", 
                                          f"Move '{os.path.basename(self.loaded_files[idx])}' up (Yes) or down (No)?")
        
        if choice is True and idx > 0:  # Move up
            # Swap with previous item
            self.loaded_files[idx], self.loaded_files[idx-1] = self.loaded_files[idx-1], self.loaded_files[idx]
            self.loaded_images[idx], self.loaded_images[idx-1] = self.loaded_images[idx-1], self.loaded_images[idx]
            new_selection = idx - 1
        elif choice is False and idx < len(self.loaded_files) - 1:  # Move down
            # Swap with next item
            self.loaded_files[idx], self.loaded_files[idx+1] = self.loaded_files[idx+1], self.loaded_files[idx]
            self.loaded_images[idx], self.loaded_images[idx+1] = self.loaded_images[idx+1], self.loaded_images[idx]
            new_selection = idx + 1
        else:
            return  # No change or cancelled
        
        # Update file list
        self.merge_files_listbox.delete(0, tk.END)
        for i, file_path in enumerate(self.loaded_files):
            filename = os.path.basename(file_path)
            img_size = self.loaded_images[i].size
            self.merge_files_listbox.insert(tk.END, f"{i+1}. {filename} ({img_size[0]}×{img_size[1]})")
        
        # Restore selection
        self.merge_files_listbox.selection_set(new_selection)
        
        self.update_merge_preview()
    
    def update_merge_preview(self):
        """Update the merge preview based on current settings"""
        if not self.loaded_images:
            return
        
        try:
            # Get current settings
            arrangement = self.merge_arrangement_var.get()
            
            # For freeform, we handle it differently
            if arrangement == "freeform":
                return  # Freeform uses its own preview system
            
            spacing = int(self.merge_spacing_var.get())
            
            # Create merged image preview
            merged_img = self.create_merged_image(arrangement, spacing, preview=True)
            
            if merged_img:
                # Scale down for preview (max 500px in either dimension)
                max_preview_size = 500
                img_width, img_height = merged_img.size
                
                if img_width > max_preview_size or img_height > max_preview_size:
                    scale_factor = min(max_preview_size / img_width, max_preview_size / img_height)
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    preview_img = merged_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    preview_img = merged_img
                
                # Convert to PhotoImage
                self.merge_preview_photo = ImageTk.PhotoImage(preview_img)
                
                # Clear canvas and display
                self.merge_preview_canvas.delete("all")
                self.merge_preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.merge_preview_photo)
                
                # Update scroll region
                self.merge_preview_canvas.configure(scrollregion=self.merge_preview_canvas.bbox("all"))
                
                # Show final dimensions info
                if hasattr(self, 'merge_preview_window'):
                    self.merge_preview_window.title(f"🔄 Merge Preview - Final Size: {img_width}×{img_height}px")
                
                # Update summary
                if hasattr(self, 'merge_summary_label'):
                    total_pixels = img_width * img_height
                    megapixels = total_pixels / 1_000_000
                    file_count = len(self.loaded_images)
                    
                    summary_text = (f"Files: {file_count}\n"
                                   f"Final Size: {img_width:,} × {img_height:,} px\n"
                                   f"Total Pixels: {megapixels:.1f} MP\n"
                                   f"Arrangement: {arrangement.title()}\n"
                                   f"Spacing: {spacing} px")
                    
                    self.merge_summary_label.config(text=summary_text)
        
        except Exception as e:
            print(f"Preview error: {e}")
            if hasattr(self, 'merge_summary_label'):
                self.merge_summary_label.config(text="Error generating preview")
    
    def create_merged_image(self, arrangement, spacing, preview=False):
        """Create merged image based on arrangement and spacing"""
        if not self.loaded_images:
            return None
        
        images = self.loaded_images
        
        if arrangement == "horizontal":
            # Calculate total width and max height (no size limits)
            total_width = sum(img.width for img in images) + spacing * (len(images) - 1)
            max_height = max(img.height for img in images)
            
            # Create new image
            merged = Image.new('RGB', (total_width, max_height), 'white')
            
            # Paste images side by side
            x_offset = 0
            for img in images:
                # Center vertically
                y_offset = (max_height - img.height) // 2
                merged.paste(img, (x_offset, y_offset))
                x_offset += img.width + spacing
        
        elif arrangement == "vertical":
            # Calculate max width and total height (no size limits)
            max_width = max(img.width for img in images)
            total_height = sum(img.height for img in images) + spacing * (len(images) - 1)
            
            # Create new image
            merged = Image.new('RGB', (max_width, total_height), 'white')
            
            # Paste images vertically
            y_offset = 0
            for img in images:
                # Center horizontally
                x_offset = (max_width - img.width) // 2
                merged.paste(img, (x_offset, y_offset))
                y_offset += img.height + spacing
        
        elif arrangement == "grid":
            # Calculate grid dimensions (try to make it as square as possible)
            num_images = len(images)
            cols = int(num_images ** 0.5)
            rows = (num_images + cols - 1) // cols  # Ceiling division
            
            # Calculate cell size (max width/height among all images)
            max_width = max(img.width for img in images)
            max_height = max(img.height for img in images)
            
            # Calculate total dimensions (no size limits)
            total_width = max_width * cols + spacing * (cols - 1)
            total_height = max_height * rows + spacing * (rows - 1)
            
            # Create new image
            merged = Image.new('RGB', (total_width, total_height), 'white')
            
            # Paste images in grid
            for i, img in enumerate(images):
                row = i // cols
                col = i % cols
                
                x_offset = col * (max_width + spacing) + (max_width - img.width) // 2
                y_offset = row * (max_height + spacing) + (max_height - img.height) // 2
                
                merged.paste(img, (x_offset, y_offset))
        
        elif arrangement == "freeform":
            # Calculate dynamic canvas size based on image positions and sizes
            min_x, min_y = 0, 0
            max_x, max_y = 0, 0
            
            # First pass: calculate required canvas dimensions
            positioned_images = []
            for i, img in enumerate(images):
                if i < len(self.image_positions):
                    x, y = self.image_positions[i]
                    
                    # Scale positions from preview coordinate system to full resolution
                    # The preview images are 15% scale, so positions need to be scaled up
                    # The relationship is: full_position = preview_position / preview_scale_factor
                    position_scale_factor = 1.0 / self.preview_scale_factor  # 1/0.15 ≈ 6.67
                    x = x * position_scale_factor
                    y = y * position_scale_factor
                    
                    # Apply scaling if specified
                    current_img = img
                    if i < len(self.image_scales) and self.image_scales[i] != 1.0:
                        scale = self.image_scales[i]
                        new_width = int(img.width * scale)
                        new_height = int(img.height * scale)
                        current_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Ensure positions are non-negative
                    x, y = max(0, int(x)), max(0, int(y))
                    
                    # Calculate bounds needed for this image
                    right_edge = x + current_img.width
                    bottom_edge = y + current_img.height
                    
                    max_x = max(max_x, right_edge)
                    max_y = max(max_y, bottom_edge)
                    
                    positioned_images.append((current_img, x, y))
                    print(f"Image {i}: preview pos ({self.image_positions[i][0]:.1f}, {self.image_positions[i][1]:.1f}) -> scaled pos ({x}, {y})")
                    print(f"  Size: {current_img.width}x{current_img.height}, edges: ({right_edge}, {bottom_edge})")
                else:
                    # Default positioning for images without specified positions
                    positioned_images.append((img, i * 50, i * 50))
                    max_x = max(max_x, (i * 50) + img.width)
                    max_y = max(max_y, (i * 50) + img.height)
            
            # Add some padding to the canvas
            padding = 100
            canvas_width = max_x + padding
            canvas_height = max_y + padding
            
            print(f"Dynamic canvas size: {canvas_width}x{canvas_height} (required: {max_x}x{max_y})")
            
            # Create dynamic canvas
            merged = Image.new('RGB', (canvas_width, canvas_height), self.canvas_background_color)
            
            # Second pass: place all images
            for img, x, y in positioned_images:
                merged.paste(img, (int(x), int(y)))
        
        return merged
    
    def confirm_merge(self):
        """Confirm and perform the merge operation"""
        try:
            # Get settings
            arrangement = self.merge_arrangement_var.get()
            spacing = int(self.merge_spacing_var.get()) if arrangement != "freeform" else 0
            
            # Create the final merged image
            self.update_status("Creating merged image...")
            merged_image = self.create_merged_image(arrangement, spacing, preview=False)
            
            if merged_image:
                # Set as the current image
                self.original_image = merged_image
                self.working_image = merged_image.copy()
                self.is_merged_image = True
                
                # Clear existing selections
                self.current_selections = []
                self.clipped_sections = []
                self.update_sections_list()
                
                # Reset image controls
                self.width_var.set("100")
                self.height_var.set("100")
                self.image_scale = 1.0
                
                # Update image info
                width, height = merged_image.size
                file_count = len(self.loaded_files)
                self.update_image_info(f"Merged Image • {width}×{height} • {file_count} files")
                
                # Close preview window
                self.merge_preview_window.destroy()
                self.merge_preview_window = None
                
                # Ask if user wants to save the merged image
                save_choice = messagebox.askyesno("Save Merged Image?", 
                                                f"Would you like to save the merged image ({file_count} files) before editing?\n\n"
                                                f"Final size: {width:,} × {height:,} pixels\n"
                                                f"You can also export it later from the Export button.")
                
                if save_choice:
                    self.export_merged_image(merged_image, file_count)
                
                # Display the merged image
                self.root.after(100, self.fit_to_window)
                
                # Update window title to show merged status
                self.root.title(f"📸 Advanced TIFF Image Editor - Merged Image ({file_count} files)")
                
                self.update_status(f"Successfully merged {file_count} images • Use mouse wheel to zoom • Ready for editing")
                
                # Clean up
                self.loaded_files = []
                self.loaded_images = []
                
            else:
                messagebox.showerror("Error", "Failed to create merged image")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge images: {str(e)}")
            self.update_status("Failed to merge images")
    
    def on_arrangement_change(self):
        """Handle arrangement mode change"""
        # Hide canvas size controls for non-freeform modes
        if hasattr(self, 'canvas_size_frame'):
            self.canvas_size_frame.pack_forget()
        
        # Update preview for regular arrangements
        self.update_merge_preview()
    
    def switch_to_freeform_mode(self):
        """Switch to free-form arrangement mode with drag and drop"""
        # Initialize positions if not already set
        if len(self.image_positions) != len(self.loaded_images):
            self.image_positions = []
            self.image_scales = []
            
            # Default positions: spread images across the canvas
            canvas_width = int(self.canvas_width_var.get()) if hasattr(self, 'canvas_width_var') else 2000
            canvas_height = int(self.canvas_height_var.get()) if hasattr(self, 'canvas_height_var') else 1500
            
            for i, img in enumerate(self.loaded_images):
                # Spread images in a grid pattern initially
                cols = int(len(self.loaded_images) ** 0.5) + 1
                row = i // cols
                col = i % cols
                
                x = col * (canvas_width // cols)
                y = row * (canvas_height // cols)
                
                # Ensure image fits within canvas
                if x + img.width > canvas_width:
                    x = max(0, canvas_width - img.width)
                if y + img.height > canvas_height:
                    y = max(0, canvas_height - img.height)
                
                self.image_positions.append((x, y))
                self.image_scales.append(1.0)
        
        # Show canvas size controls
        if hasattr(self, 'canvas_size_frame'):
            self.canvas_size_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Switch to freeform preview mode
        self.open_freeform_editor()
    
    def create_preview_images(self):
        """Create downscaled preview images for fast drag-and-drop performance"""
        self.preview_images = []
        self.preview_photos = []
        
        for i, img in enumerate(self.loaded_images):
            try:
                # Calculate preview size
                original_width, original_height = img.size
                preview_width = int(original_width * self.preview_scale_factor)
                preview_height = int(original_height * self.preview_scale_factor)
                
                # Ensure minimum size for visibility
                preview_width = max(preview_width, 50)
                preview_height = max(preview_height, 50)
                
                # Create high-quality thumbnail
                preview_img = img.copy()
                preview_img.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
                
                self.preview_images.append(preview_img)
                
                # Update status
                self.update_status(f"Creating preview {i+1}/{len(self.loaded_images)}...")
                self.root.update_idletasks()
                
            except Exception as e:
                print(f"Error creating preview for image {i}: {e}")
                # Create a placeholder if preview fails
                placeholder = Image.new('RGB', (100, 100), color='lightgray')
                self.preview_images.append(placeholder)
        
        self.update_status("Preview images created - ready for fast drag & drop!")

    def open_freeform_editor(self):
        """Open the free-form drag and drop editor"""
        # Create preview images for performance
        self.update_status("Creating optimized preview images for fast drag & drop...")
        self.create_preview_images()
        
        # Close current preview window if open
        if self.merge_preview_window:
            self.merge_preview_window.destroy()
        
        self.merge_preview_window = tk.Toplevel(self.root)
        self.merge_preview_window.title("🎨 Free-form Image Arranger - High Performance Mode")
        self.merge_preview_window.geometry("1400x900")  # Larger window
        self.merge_preview_window.configure(bg='#f0f0f0')
        
        # Make window modal
        self.merge_preview_window.transient(self.root)
        self.merge_preview_window.grab_set()
        
        # Header
        header_frame = tk.Frame(self.merge_preview_window, bg='#2563eb', height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🎨 Drag & Drop Image Arranger", 
                              font=('Arial', 14, 'bold'), bg='#2563eb', fg='white')
        title_label.pack(expand=True)
        
        # Main content
        content_frame = tk.Frame(self.merge_preview_window, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = tk.Frame(content_frame, bg='#f0f0f0', width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Canvas settings
        canvas_settings = tk.LabelFrame(left_panel, text="🖼️ Canvas Settings", 
                                       font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                       padx=10, pady=10)
        canvas_settings.pack(fill=tk.X, pady=(0, 10))
        
        # Canvas size
        size_frame = tk.Frame(canvas_settings, bg='#f0f0f0')
        size_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(size_frame, text="Size:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W)
        
        size_controls = tk.Frame(size_frame, bg='#f0f0f0')
        size_controls.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(size_controls, text="W:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.freeform_width_var = tk.StringVar(value="5000")  # Larger default canvas
        width_entry = tk.Entry(size_controls, textvariable=self.freeform_width_var, width=6)
        width_entry.pack(side=tk.LEFT, padx=(2, 5))
        
        tk.Label(size_controls, text="H:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.freeform_height_var = tk.StringVar(value="4000")  # Larger default canvas
        height_entry = tk.Entry(size_controls, textvariable=self.freeform_height_var, width=6)
        height_entry.pack(side=tk.LEFT, padx=(2, 5))
        
        tk.Button(size_controls, text="Apply", command=self.update_freeform_canvas,
                 bg='#4CAF50', fg='white', font=('Arial', 8), padx=5).pack(side=tk.LEFT, padx=(5, 0))
        
        # Background color
        bg_frame = tk.Frame(canvas_settings, bg='#f0f0f0')
        bg_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(bg_frame, text="Background:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W)
        
        self.bg_color_button = tk.Button(bg_frame, text="⬜ White", 
                                        command=self.choose_background_color,
                                        bg='white', font=('Arial', 8), padx=10)
        self.bg_color_button.pack(fill=tk.X, pady=(5, 0))
        
        # Zoom controls
        zoom_frame = tk.Frame(canvas_settings, bg='#f0f0f0')
        zoom_frame.pack(fill=tk.X, pady=(10, 5))
        
        tk.Label(zoom_frame, text="Zoom:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W)
        
        zoom_controls = tk.Frame(zoom_frame, bg='#f0f0f0')
        zoom_controls.pack(fill=tk.X, pady=(5, 0))
        
        tk.Button(zoom_controls, text="➖", command=self.zoom_out_freeform,
                 bg='#6c757d', fg='white', font=('Arial', 8), width=3).pack(side=tk.LEFT)
        
        self.zoom_info_label = tk.Label(zoom_controls, text="Zoom: 100%", 
                                       font=('Arial', 9), bg='#e0e0e0', fg='#333', 
                                       width=10, relief='sunken')
        self.zoom_info_label.pack(side=tk.LEFT, padx=(5, 5))
        
        tk.Button(zoom_controls, text="➕", command=self.zoom_in_freeform,
                 bg='#6c757d', fg='white', font=('Arial', 8), width=3).pack(side=tk.LEFT)
        
        tk.Button(zoom_controls, text="🔄", command=self.reset_zoom_freeform,
                 bg='#17a2b8', fg='white', font=('Arial', 8), width=3).pack(side=tk.LEFT, padx=(5, 0))
        
        # Zoom instruction
        tk.Label(zoom_frame, text="💡 Mouse wheel or +/- keys to zoom, 0 to reset", 
                font=('Arial', 8), bg='#f0f0f0', fg='#666').pack(pady=(5, 0))
        
        # Performance status section
        perf_section = tk.LabelFrame(left_panel, text="⚡ Performance Mode", 
                                    font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#28a745',
                                    padx=8, pady=8, relief='groove', bd=2)
        perf_section.pack(fill=tk.X, pady=(0, 10))
        
        # Performance info
        self.perf_info_label = tk.Label(perf_section, 
                                       text="Fast preview mode active",
                                       font=('Arial', 9, 'bold'), bg='#f0f0f0', fg='#28a745')
        self.perf_info_label.pack()
        
        performance_details = tk.Frame(perf_section, bg='#f0f0f0')
        performance_details.pack(fill=tk.X, pady=(5, 0))
        
        # Show scale factor and other optimizations
        scale_info = f"• Preview scale: {int(self.preview_scale_factor * 100)}% of original size"
        tk.Label(performance_details, text=scale_info,
                font=('Arial', 8), bg='#f0f0f0', fg='#666').pack(anchor=tk.W)
        
        tk.Label(performance_details, text="• Large TIFF files optimized for smooth dragging",
                font=('Arial', 8), bg='#f0f0f0', fg='#666').pack(anchor=tk.W)
        
        tk.Label(performance_details, text="• Full resolution preserved for final export",
                font=('Arial', 8), bg='#f0f0f0', fg='#666').pack(anchor=tk.W)
        
        # Image list and controls
        images_section = tk.LabelFrame(left_panel, text="📄 Images", 
                                      font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#333',
                                      padx=10, pady=10)
        images_section.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Image listbox
        self.freeform_images_listbox = tk.Listbox(images_section, height=8, font=('Arial', 9))
        self.freeform_images_listbox.pack(fill=tk.X, pady=(0, 10))
        self.freeform_images_listbox.bind('<<ListboxSelect>>', self.on_freeform_image_select)
        
        # Populate image list
        for i, file_path in enumerate(self.loaded_files):
            filename = os.path.basename(file_path)
            self.freeform_images_listbox.insert(tk.END, f"{i+1}. {filename}")
        
        # Image controls
        img_controls = tk.Frame(images_section, bg='#f0f0f0')
        img_controls.pack(fill=tk.X)
        
        tk.Label(img_controls, text="Selected Image:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0').pack(anchor=tk.W)
        
        # Position controls
        pos_frame = tk.Frame(img_controls, bg='#f0f0f0')
        pos_frame.pack(fill=tk.X, pady=(5, 5))
        
        tk.Label(pos_frame, text="X:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.img_x_var = tk.StringVar(value="0")
        x_entry = tk.Entry(pos_frame, textvariable=self.img_x_var, width=6)
        x_entry.pack(side=tk.LEFT, padx=(2, 5))
        x_entry.bind('<Return>', self.update_selected_image_position)
        
        tk.Label(pos_frame, text="Y:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.img_y_var = tk.StringVar(value="0")
        y_entry = tk.Entry(pos_frame, textvariable=self.img_y_var, width=6)
        y_entry.pack(side=tk.LEFT, padx=(2, 5))
        y_entry.bind('<Return>', self.update_selected_image_position)
        
        # Scale controls
        scale_frame = tk.Frame(img_controls, bg='#f0f0f0')
        scale_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(scale_frame, text="Scale:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.img_scale_var = tk.StringVar(value="1.0")
        scale_entry = tk.Entry(scale_frame, textvariable=self.img_scale_var, width=6)
        scale_entry.pack(side=tk.LEFT, padx=(2, 5))
        scale_entry.bind('<Return>', self.update_selected_image_scale)
        
        tk.Button(scale_frame, text="Reset", command=self.reset_selected_image_scale,
                 bg='#6c757d', fg='white', font=('Arial', 8), padx=5).pack(side=tk.LEFT, padx=(5, 0))
        
        # Right panel - Canvas
        canvas_panel = tk.Frame(content_frame, bg='white', relief='solid', bd=1)
        canvas_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        self.freeform_canvas = tk.Canvas(canvas_panel, bg='white')
        
        v_scroll = tk.Scrollbar(canvas_panel, orient=tk.VERTICAL, command=self.freeform_canvas.yview)
        h_scroll = tk.Scrollbar(canvas_panel, orient=tk.HORIZONTAL, command=self.freeform_canvas.xview)
        
        self.freeform_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.freeform_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind drag and drop events
        self.freeform_canvas.bind("<Button-1>", self.on_freeform_canvas_click)
        self.freeform_canvas.bind("<B1-Motion>", self.on_freeform_canvas_drag)
        self.freeform_canvas.bind("<ButtonRelease-1>", self.on_freeform_canvas_release)
        self.freeform_canvas.bind("<Motion>", self.on_freeform_canvas_motion)
        
        # Bind mouse wheel zoom events
        self.freeform_canvas.bind("<MouseWheel>", self.on_freeform_canvas_zoom)  # Windows
        self.freeform_canvas.bind("<Button-4>", self.on_freeform_canvas_zoom)    # Linux scroll up
        self.freeform_canvas.bind("<Button-5>", self.on_freeform_canvas_zoom)    # Linux scroll down
        
        # Make canvas focusable for mouse wheel events
        self.freeform_canvas.config(takefocus=True)
        self.freeform_canvas.bind("<Enter>", lambda e: self.freeform_canvas.focus_set())
        
        # Bind keyboard shortcuts for zoom
        self.freeform_canvas.bind("<KeyPress-plus>", lambda e: self.zoom_in_freeform())
        self.freeform_canvas.bind("<KeyPress-equal>", lambda e: self.zoom_in_freeform())  # Plus without shift
        self.freeform_canvas.bind("<KeyPress-minus>", lambda e: self.zoom_out_freeform())
        self.freeform_canvas.bind("<KeyPress-0>", lambda e: self.reset_zoom_freeform())
        
        # Also bind to parent window for better accessibility
        self.merge_preview_window.bind("<KeyPress-plus>", lambda e: self.zoom_in_freeform())
        self.merge_preview_window.bind("<KeyPress-equal>", lambda e: self.zoom_in_freeform())
        self.merge_preview_window.bind("<KeyPress-minus>", lambda e: self.zoom_out_freeform())
        self.merge_preview_window.bind("<KeyPress-0>", lambda e: self.reset_zoom_freeform())
        
        # Bottom buttons
        buttons_frame = tk.Frame(self.merge_preview_window, bg='#f0f0f0')
        buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(buttons_frame, text="❌ Cancel", command=self.cancel_merge,
                 bg='#6c757d', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.LEFT)
        
        tk.Button(buttons_frame, text="🔄 Reset Positions", command=self.reset_all_positions,
                 bg='#17a2b8', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(buttons_frame, text="✅ Confirm Arrangement", command=self.confirm_merge,
                 bg='#28a745', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=8).pack(side=tk.RIGHT)
        
        # Initialize positions and scales if not already set
        while len(self.image_positions) < len(self.loaded_images):
            i = len(self.image_positions)
            default_x = (i * 150) % 1200  # Spread images horizontally with more space
            default_y = (i * 150) // 1200 * 200  # Stack vertically when wrapping
            self.image_positions.append((default_x, default_y))
        
        while len(self.image_scales) < len(self.loaded_images):
            self.image_scales.append(1.0)
        
        # Initial canvas setup - start zoomed out to see the large canvas
        self.freeform_zoom = 0.3  # Start zoomed out
        self.selected_image_index = None  # No selection initially
        self.update_freeform_canvas()
        self.update_zoom_info()
        
        # Show initial status
        self.update_status(f"Performance mode: Using {int(self.preview_scale_factor*100)}% preview images for fast dragging")
    
    def cancel_merge(self):
        """Cancel the merge operation"""
        self.merge_preview_window.destroy()
        self.merge_preview_window = None
        self.loaded_files = []
        self.loaded_images = []
        self.image_positions = []
        self.image_scales = []
        self.update_status("Merge cancelled")
    
    def update_freeform_canvas(self):
        """Update the free-form canvas with current images and positions"""
        try:
            base_canvas_width = int(self.freeform_width_var.get())
            base_canvas_height = int(self.freeform_height_var.get())
        except ValueError:
            base_canvas_width, base_canvas_height = 2000, 1500
        
        # Apply zoom to canvas dimensions
        canvas_width = int(base_canvas_width * self.freeform_zoom)
        canvas_height = int(base_canvas_height * self.freeform_zoom)
        
        # Clear canvas
        self.freeform_canvas.delete("all")
        
        # Set canvas size (display window stays the same, but scroll region changes)
        display_width = min(800, canvas_width)
        display_height = min(600, canvas_height)
        self.freeform_canvas.configure(width=display_width, height=display_height)
        self.freeform_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Draw background with clear boundaries
        self.freeform_canvas.create_rectangle(0, 0, canvas_width, canvas_height, 
                                            fill=self.canvas_background_color, outline='#333333', width=3)
        
        # Add a subtle grid for better positioning reference (every 500 pixels when zoomed out)
        if self.freeform_zoom <= 0.5:  # Only show grid when zoomed out
            grid_spacing = int(500 * self.freeform_zoom)
            if grid_spacing > 20:  # Don't draw if too small
                # Vertical lines
                for x in range(grid_spacing, canvas_width, grid_spacing):
                    self.freeform_canvas.create_line(x, 0, x, canvas_height, 
                                                   fill='#e0e0e0', width=1, tags="grid")
                # Horizontal lines  
                for y in range(grid_spacing, canvas_height, grid_spacing):
                    self.freeform_canvas.create_line(0, y, canvas_width, y, 
                                                   fill='#e0e0e0', width=1, tags="grid")
        
        # Draw images using preview images for performance
        self.freeform_canvas_images = []  # Store references to prevent garbage collection
        self.preview_photos = []  # Store PhotoImage references
        
        # Only initialize positions if we need MORE positions, and only for NEW images
        initial_positions_count = len(self.image_positions)
        
        # ONLY add positions for images that don't have them yet
        if len(self.image_positions) < len(self.preview_images):
            for i in range(len(self.image_positions), len(self.preview_images)):
                default_x = (i * 150) % 1200  # Spread images horizontally with more space
                default_y = (i * 150) // 1200 * 200  # Stack vertically when wrapping
                self.image_positions.append((default_x, default_y))
        
        while len(self.image_scales) < len(self.preview_images):
            self.image_scales.append(1.0)
        

        
        for i, preview_img in enumerate(self.preview_images):
                
            base_x, base_y = self.image_positions[i]
            image_scale = self.image_scales[i]
            
            # Apply zoom to position
            x = int(base_x * self.freeform_zoom)
            y = int(base_y * self.freeform_zoom)
            
            # Apply both image scaling and zoom scaling to preview image
            total_scale = image_scale * self.freeform_zoom
            
            if total_scale != 1.0:
                new_width = max(1, int(preview_img.width * total_scale))
                new_height = max(1, int(preview_img.height * total_scale))
                scaled_img = preview_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                scaled_img = preview_img
            
            # Create PhotoImage
            photo = ImageTk.PhotoImage(scaled_img)
            self.freeform_canvas_images.append(photo)  # Keep reference
            self.preview_photos.append(photo)  # Also store for cleanup
            
            # Draw on canvas with tag for identification
            img_id = self.freeform_canvas.create_image(x, y, anchor=tk.NW, image=photo, tags=f"img_{i}")
            
            # Draw selection border if this image is selected
            if i == self.selected_image_index:
                # Get image bounds for selection border
                img_x1, img_y1 = x, y
                img_x2 = img_x1 + scaled_img.width
                img_y2 = img_y1 + scaled_img.height
                
                # Draw selection border
                border_offset = self.selection_border_width // 2
                self.freeform_canvas.create_rectangle(
                    img_x1 - border_offset, img_y1 - border_offset,
                    img_x2 + border_offset, img_y2 + border_offset,
                    outline='#FF6B35', width=self.selection_border_width,
                    tags="selection"
                )
                
                # Add selection corners for visual feedback
                corner_size = 8
                corners = [
                    (img_x1, img_y1), (img_x2, img_y1),  # Top corners
                    (img_x1, img_y2), (img_x2, img_y2)   # Bottom corners
                ]
                for corner_x, corner_y in corners:
                    self.freeform_canvas.create_rectangle(
                        corner_x - corner_size//2, corner_y - corner_size//2,
                        corner_x + corner_size//2, corner_y + corner_size//2,
                        fill='#FF6B35', outline='white', width=2,
                        tags="selection"
                    )
    
    def on_freeform_canvas_click(self, event):
        """Handle mouse click on free-form canvas"""
        # Get canvas coordinates
        canvas_x = self.freeform_canvas.canvasx(event.x)
        canvas_y = self.freeform_canvas.canvasy(event.y)
        
        # Find which image was clicked
        clicked_item = self.freeform_canvas.find_closest(canvas_x, canvas_y)[0]
        tags = self.freeform_canvas.gettags(clicked_item)
        
        for tag in tags:
            if tag.startswith("img_"):
                image_index = int(tag.split("_")[1])
                

                
                # Set as selected image with visual feedback
                self.selected_image_index = image_index
                # Don't start dragging immediately - wait for actual mouse movement
                self.potential_drag_image = image_index
                self.drag_start_pos = (canvas_x, canvas_y)
                self.dragging_image = None  # Not actually dragging yet
                

                
                # Select the image in the listbox
                self.freeform_images_listbox.selection_clear(0, tk.END)
                self.freeform_images_listbox.selection_set(image_index)
                
                # Update selection without full redraw for better performance
                self.update_selection_indicators()
                
                # Update position controls
                self.update_position_controls()
                

                
                # Update status
                self.update_status(f"Selected image {image_index + 1} - drag to move or use controls")
                break
        else:
            self.dragging_image = None
            self.potential_drag_image = None
    
    def update_selection_indicators(self):
        """Update only the selection indicators without redrawing entire canvas"""
        # Remove all existing selection indicators
        self.freeform_canvas.delete("selection")
        
        # Add selection indicators for the currently selected image
        if self.selected_image_index is not None and self.selected_image_index < len(self.preview_images):
            i = self.selected_image_index
            preview_img = self.preview_images[i]
            
            # Get position and scaling
            base_x, base_y = self.image_positions[i]
            image_scale = self.image_scales[i]
            
            # Apply zoom to position
            x = int(base_x * self.freeform_zoom)
            y = int(base_y * self.freeform_zoom)
            
            # Calculate scaled image size
            total_scale = image_scale * self.freeform_zoom
            if total_scale != 1.0:
                scaled_width = max(1, int(preview_img.width * total_scale))
                scaled_height = max(1, int(preview_img.height * total_scale))
            else:
                scaled_width = preview_img.width
                scaled_height = preview_img.height
            
            # Draw selection border
            img_x1, img_y1 = x, y
            img_x2 = img_x1 + scaled_width
            img_y2 = img_y1 + scaled_height
            
            border_offset = self.selection_border_width // 2
            self.freeform_canvas.create_rectangle(
                img_x1 - border_offset, img_y1 - border_offset,
                img_x2 + border_offset, img_y2 + border_offset,
                outline='#FF6B35', width=self.selection_border_width,
                tags="selection"
            )
            
            # Add selection corners
            corner_size = 8
            corners = [
                (img_x1, img_y1), (img_x2, img_y1),  # Top corners
                (img_x1, img_y2), (img_x2, img_y2)   # Bottom corners
            ]
            for corner_x, corner_y in corners:
                self.freeform_canvas.create_rectangle(
                    corner_x - corner_size//2, corner_y - corner_size//2,
                    corner_x + corner_size//2, corner_y + corner_size//2,
                    fill='#FF6B35', outline='white', width=2,
                    tags="selection"
                )
        
        # Update zoom info to show selection
        self.update_zoom_info()
    
    def on_freeform_canvas_drag(self, event):
        """Handle mouse drag on free-form canvas"""
        canvas_x = self.freeform_canvas.canvasx(event.x)
        canvas_y = self.freeform_canvas.canvasy(event.y)
        
        # Check if we have a potential drag that should start
        if hasattr(self, 'potential_drag_image') and self.potential_drag_image is not None and self.drag_start_pos:
            # Calculate movement in canvas coordinates
            dx = canvas_x - self.drag_start_pos[0]
            dy = canvas_y - self.drag_start_pos[1]
            
            # Only start dragging if movement is significant (more than 5 pixels)
            if abs(dx) > 5 or abs(dy) > 5:
                self.dragging_image = self.potential_drag_image
                self.potential_drag_image = None

        
        # Handle actual drag
        if self.dragging_image is not None and self.drag_start_pos:
            # Calculate movement in canvas coordinates
            dx = canvas_x - self.drag_start_pos[0]
            dy = canvas_y - self.drag_start_pos[1]
            
            # Convert movement to base coordinates (account for zoom)
            base_dx = dx / self.freeform_zoom
            base_dy = dy / self.freeform_zoom
            
            # Update image position in base coordinates
            old_x, old_y = self.image_positions[self.dragging_image]
            new_x = max(0, old_x + base_dx)
            new_y = max(0, old_y + base_dy)
            

            
            # Get base canvas size
            try:
                base_canvas_width = int(self.freeform_width_var.get())
                base_canvas_height = int(self.freeform_height_var.get())
            except ValueError:
                base_canvas_width, base_canvas_height = 2000, 1500
            
            # Get image size in base coordinates (accounting for image scale only)
            img = self.loaded_images[self.dragging_image]
            image_scale = self.image_scales[self.dragging_image] if self.dragging_image < len(self.image_scales) else 1.0
            img_width = int(img.width * image_scale)
            img_height = int(img.height * image_scale)
            
            # Constrain to base canvas bounds (but allow oversized images to move freely)
            max_x = base_canvas_width - img_width
            max_y = base_canvas_height - img_height
            
            if max_x >= 0 and max_y >= 0:
                # Normal case: image fits within canvas bounds
                new_x = min(new_x, max_x)
                new_y = min(new_y, max_y)
            # Otherwise: image is larger than canvas, allow free positioning
            self.image_positions[self.dragging_image] = (new_x, new_y)
            
            # Update canvas
            self.update_freeform_canvas()
            

            
            self.update_position_controls()
            
            # Update drag start position
            self.drag_start_pos = (canvas_x, canvas_y)
    
    def on_freeform_canvas_release(self, event):
        """Handle mouse release on free-form canvas"""
        self.dragging_image = None
        self.drag_start_pos = None
        if hasattr(self, 'potential_drag_image'):
            self.potential_drag_image = None
    
    def on_freeform_canvas_motion(self, event):
        """Handle mouse motion for cursor coordinates display"""
        try:
            canvas_x = self.freeform_canvas.canvasx(event.x)
            canvas_y = self.freeform_canvas.canvasy(event.y)
            
            # Convert to actual canvas coordinates (accounting for zoom)
            actual_x = canvas_x / self.freeform_zoom
            actual_y = canvas_y / self.freeform_zoom
            
            # Update status with position info
            if hasattr(self, 'perf_info_label'):
                canvas_size = f"{int(self.freeform_width_var.get())}×{int(self.freeform_height_var.get())}"
                coords_info = f"Position: ({int(actual_x)}, {int(actual_y)}) • Canvas: {canvas_size}px"
                self.perf_info_label.config(text=coords_info)
        except:
            pass  # Ignore errors during window closing
    
    def on_freeform_canvas_zoom(self, event):
        """Handle mouse wheel zoom on free-form canvas"""
        # Get mouse position relative to canvas
        canvas_x = self.freeform_canvas.canvasx(event.x)
        canvas_y = self.freeform_canvas.canvasy(event.y)
        
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            zoom_factor = 1.1
        else:  # Zoom out
            zoom_factor = 0.9
        
        # Calculate new zoom level
        new_zoom = self.freeform_zoom * zoom_factor
        
        # Clamp zoom level
        new_zoom = max(self.freeform_zoom_min, min(new_zoom, self.freeform_zoom_max))
        
        # Only update if zoom level actually changed
        if new_zoom != self.freeform_zoom:
            # Calculate zoom center point
            old_zoom = self.freeform_zoom
            self.freeform_zoom = new_zoom
            
            # Get current scroll position
            x_scroll = self.freeform_canvas.canvasx(0)
            y_scroll = self.freeform_canvas.canvasy(0)
            
            # Update canvas display
            self.update_freeform_canvas()
            
            # Adjust scroll position to zoom around mouse cursor
            zoom_ratio = new_zoom / old_zoom
            
            # Calculate new scroll position to keep mouse position centered
            new_x = (canvas_x * zoom_ratio) - event.x
            new_y = (canvas_y * zoom_ratio) - event.y
            
            # Get canvas size to calculate scroll fractions
            try:
                canvas_width = int(self.freeform_width_var.get()) * self.freeform_zoom
                canvas_height = int(self.freeform_height_var.get()) * self.freeform_zoom
            except (ValueError, AttributeError):
                canvas_width, canvas_height = 2000 * self.freeform_zoom, 1500 * self.freeform_zoom
            
            # Scroll to new position
            if canvas_width > 0 and canvas_height > 0:
                x_fraction = max(0, min(1, new_x / canvas_width))
                y_fraction = max(0, min(1, new_y / canvas_height))
                
                self.freeform_canvas.xview_moveto(x_fraction)
                self.freeform_canvas.yview_moveto(y_fraction)
            
            # Update zoom info in UI
            self.update_zoom_info()
    
    def on_freeform_image_select(self, event):
        """Handle image selection in listbox"""
        selection = self.freeform_images_listbox.curselection()
        if selection:
            self.update_position_controls()
    
    def update_position_controls(self):
        """Update position and scale controls for selected image"""
        selection = self.freeform_images_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.image_positions):
                x, y = self.image_positions[idx]

                self.img_x_var.set(str(int(x)))
                self.img_y_var.set(str(int(y)))
            
            if idx < len(self.image_scales):
                scale = self.image_scales[idx]
                self.img_scale_var.set(f"{scale:.2f}")
    
    def update_selected_image_position(self, event=None):
        """Update position of selected image from text controls"""
        selection = self.freeform_images_listbox.curselection()
        if selection:
            idx = selection[0]
            try:
                x = int(self.img_x_var.get())
                y = int(self.img_y_var.get())
                
                # Get canvas size
                try:
                    canvas_width = int(self.freeform_width_var.get())
                    canvas_height = int(self.freeform_height_var.get())
                except ValueError:
                    canvas_width, canvas_height = 2000, 1500
                
                # Get image size
                img = self.loaded_images[idx]
                scale = self.image_scales[idx] if idx < len(self.image_scales) else 1.0
                img_width = int(img.width * scale)
                img_height = int(img.height * scale)
                
                # Constrain to canvas bounds
                x = max(0, min(x, canvas_width - img_width))
                y = max(0, min(y, canvas_height - img_height))
                
                self.image_positions[idx] = (x, y)
                self.update_freeform_canvas()
                
            except ValueError:
                pass  # Invalid input, ignore
    
    def update_selected_image_scale(self, event=None):
        """Update scale of selected image from text controls"""
        selection = self.freeform_images_listbox.curselection()
        if selection:
            idx = selection[0]
            try:
                scale = float(self.img_scale_var.get())
                scale = max(0.1, min(scale, 5.0))  # Limit scale between 0.1 and 5.0
                
                if idx < len(self.image_scales):
                    self.image_scales[idx] = scale
                else:
                    # Extend list if needed
                    while len(self.image_scales) <= idx:
                        self.image_scales.append(1.0)
                    self.image_scales[idx] = scale
                
                self.update_freeform_canvas()
                self.update_position_controls()
                
            except ValueError:
                pass  # Invalid input, ignore
    
    def reset_selected_image_scale(self):
        """Reset scale of selected image to 1.0"""
        selection = self.freeform_images_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.image_scales):
                self.image_scales[idx] = 1.0
                self.img_scale_var.set("1.0")
                self.update_freeform_canvas()
    
    def reset_all_positions(self):
        """Reset all image positions to default grid layout"""
        if messagebox.askyesno("Reset Positions", "Reset all images to default positions?"):
            canvas_width = int(self.freeform_width_var.get())
            canvas_height = int(self.freeform_height_var.get())
            
            self.image_positions = []
            self.image_scales = []
            
            for i, img in enumerate(self.loaded_images):
                # Grid layout
                cols = int(len(self.loaded_images) ** 0.5) + 1
                row = i // cols
                col = i % cols
                
                x = col * (canvas_width // cols)
                y = row * (canvas_height // cols)
                
                # Ensure image fits
                if x + img.width > canvas_width:
                    x = max(0, canvas_width - img.width)
                if y + img.height > canvas_height:
                    y = max(0, canvas_height - img.height)
                
                self.image_positions.append((x, y))
                self.image_scales.append(1.0)
            
            self.update_freeform_canvas()
            self.update_position_controls()
    
    def analyze_performance(self):
        """Comprehensive performance analysis and optimization recommendations"""
        try:
            print("\n" + "="*60)
            print("🔬 PERFORMANCE ANALYSIS REPORT")
            print("="*60)
            
            # System Information
            memory_info = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            current_memory = psutil.Process().memory_info().rss / (1024**2)
            
            print(f"💻 SYSTEM INFO:")
            print(f"   CPU Cores: {cpu_count}")
            print(f"   Total RAM: {memory_info.total / (1024**3):.1f}GB")
            print(f"   Available RAM: {memory_info.available / (1024**3):.1f}GB")
            print(f"   Current Usage: {current_memory:.0f}MB")
            
            # GPU Status
            gpu_status = "✅ ENABLED" if self.enable_gpu_acceleration else "❌ DISABLED"
            gpu_devices = self.gpu_context.get('devices', 0) if self.gpu_context else 0
            print(f"   GPU Acceleration: {gpu_status} ({gpu_devices} devices)")
            
            # Performance Settings
            print(f"\n⚙️ PERFORMANCE SETTINGS:")
            print(f"   Fast Zoom: {'✅ ON' if self.enable_fast_zoom else '❌ OFF'}")
            print(f"   Viewport Culling: {'✅ ON' if self.viewport_culling else '❌ OFF'}")
            print(f"   Async Rendering: {'✅ ON' if self.async_rendering else '❌ OFF'}")
            print(f"   Memory Limit: {self.memory_limit_mb}MB")
            
            # Cache Performance
            total_requests = self.cache_hit_count + self.cache_miss_count
            hit_rate = (self.cache_hit_count / max(total_requests, 1)) * 100
            print(f"\n💾 CACHE PERFORMANCE:")
            print(f"   Cache Hit Rate: {hit_rate:.1f}% ({self.cache_hit_count}/{total_requests})")
            print(f"   Pyramid Levels Cached: {len(self.image_pyramid)}")
            print(f"   Display Cache Items: {len(self.display_cache)}")
            print(f"   Cache Memory: {self.cache_total_memory / (1024**2):.1f}MB")
            
            # Render Performance
            if self.performance_stats['render_times']:
                recent_renders = self.performance_stats['render_times'][-20:]
                avg_time = sum(r['duration_ms'] for r in recent_renders) / len(recent_renders)
                min_time = min(r['duration_ms'] for r in recent_renders)
                max_time = max(r['duration_ms'] for r in recent_renders)
                
                print(f"\n⚡ RENDER PERFORMANCE (last 20):")
                print(f"   Average: {avg_time:.1f}ms")
                print(f"   Range: {min_time:.1f}ms - {max_time:.1f}ms")
                
                # Categorize performance
                if avg_time < 50:
                    performance_grade = "🟢 EXCELLENT"
                elif avg_time < 150:
                    performance_grade = "🟡 GOOD"
                elif avg_time < 500:
                    performance_grade = "🟠 FAIR"
                else:
                    performance_grade = "🔴 POOR"
                print(f"   Performance Grade: {performance_grade}")
            
            # Optimization Recommendations
            print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
            recommendations = []
            
            if not self.enable_fast_zoom:
                recommendations.append("Enable Fast Zoom for better performance")
            
            if not self.enable_gpu_acceleration and HAS_OPENCV:
                recommendations.append("Enable GPU acceleration if CUDA is available")
            
            if hit_rate < 70:
                recommendations.append("Low cache hit rate - consider larger cache size")
            
            if current_memory > self.memory_limit_mb * 0.9:
                recommendations.append("High memory usage - consider lowering memory limit or clearing cache")
            
            if self.performance_stats['render_times'] and avg_time > 200:
                recommendations.append("Slow render times - try reducing image size or pyramid levels")
            
            if len(self.image_pyramid) > 10:
                recommendations.append("Large pyramid cache - consider periodic cleanup")
            
            if not recommendations:
                recommendations.append("Performance is optimal! 🎉")
            
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
            
            print("="*60)
            
            # Store analysis results
            self.last_performance_analysis = {
                'timestamp': time.time(),
                'memory_usage': current_memory,
                'cache_hit_rate': hit_rate,
                'avg_render_time': avg_time if self.performance_stats['render_times'] else 0,
                'recommendations': recommendations
            }
            
        except Exception as e:
            print(f"Performance analysis error: {e}")
    
    def update_zoom_info(self):
        """Enhanced zoom information with performance indicators"""
        if hasattr(self, 'zoom_info_label'):
            zoom_percent = int(self.freeform_zoom * 100) if hasattr(self, 'freeform_zoom') else int(self.image_scale * 100)
            
            # Performance indicators
            gpu_indicator = "🚀" if self.enable_gpu_acceleration else "💻"
            fast_indicator = "⚡" if self.enable_fast_zoom else "🐌"
            
            # Cache efficiency
            total_requests = self.cache_hit_count + self.cache_miss_count
            hit_rate = (self.cache_hit_count / max(total_requests, 1)) * 100
            
            performance_info = f" • {gpu_indicator}{fast_indicator} Cache: {hit_rate:.0f}%"
            
            if hasattr(self, 'preview_images'):
                performance_info += f" • Previews: {len(self.preview_images)}"
            
            selection_info = f" • Selected: Image {self.selected_image_index + 1}" if hasattr(self, 'selected_image_index') and self.selected_image_index is not None else ""
            
            self.zoom_info_label.config(text=f"Zoom: {zoom_percent}%{performance_info}{selection_info}")
    
    def zoom_in_freeform(self):
        """Zoom in on freeform canvas"""
        new_zoom = min(self.freeform_zoom * 1.2, self.freeform_zoom_max)
        if new_zoom != self.freeform_zoom:
            self.freeform_zoom = new_zoom
            self.update_freeform_canvas()
            self.update_zoom_info()
    
    def zoom_out_freeform(self):
        """Zoom out on freeform canvas"""
        new_zoom = max(self.freeform_zoom / 1.2, self.freeform_zoom_min)
        if new_zoom != self.freeform_zoom:
            self.freeform_zoom = new_zoom
            self.update_freeform_canvas()
            self.update_zoom_info()
    
    def reset_zoom_freeform(self):
        """Reset zoom to 100%"""
        if self.freeform_zoom != 1.0:
            self.freeform_zoom = 1.0
            self.update_freeform_canvas()
            self.update_zoom_info()
    
    def choose_background_color(self):
        """Choose background color for free-form canvas"""
        color = colorchooser.askcolor(title="Choose Background Color", 
                                     initialcolor=self.canvas_background_color)
        if color[1]:  # If user didn't cancel
            self.canvas_background_color = color[1]
            # Update button appearance
            self.bg_color_button.configure(bg=color[1], 
                                         text=f"⬜ {color[1].upper()}" if color[1] != '#ffffff' else "⬜ White")
            self.update_freeform_canvas()
    
    def export_merged_image(self, merged_image, file_count=None):
        """Export the merged image with suggested filename"""
        if file_count is None:
            file_count = len(self.loaded_files) if self.loaded_files else 1
        suggested_name = f"merged_image_{file_count}_files.tiff"
        
        if self.is_macos:
            file_path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save Merged Image",
                initialfile=suggested_name,
                defaultextension=".tiff",
                filetypes=[("TIFF files", "*.tiff *.tif"), ("PNG files", "*.png"), 
                          ("JPEG files", "*.jpg *.jpeg"), ("All files", "*")]
            )
        else:
            file_path = filedialog.asksaveasfilename(
                title="Save Merged Image",
                initialfile=suggested_name,
                defaultextension=".tiff",
                filetypes=[("TIFF files", "*.tiff"), ("PNG files", "*.png"), 
                          ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
        
        if file_path:
            try:
                merged_image.save(file_path)
                messagebox.showinfo("Success", f"Merged image saved successfully!\n\nLocation: {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save merged image: {str(e)}")


def main():
    root = tk.Tk()
    app = ImageEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
