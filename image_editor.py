"""
High-Resolution TIFF Image Editor with Free Drawing Selection and Color Assignment
Features:
- Load high-resolution TIFF images
- Free drawing selection tool
- Color assignment to selected sections
- Move and rearrange sections
- Clip/cut selected sections
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, font
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import json
import os

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("📸 Advanced TIFF Image Editor - Professional Edition")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')
        
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
        self.line_spacing_percent = 20.0  # Percentage of image width between lines (now supports decimals)
        self.lines_confirmed = False  # Track if lines are locked
        self.line_positions = []  # Store actual line x positions
        
        # Mode variables
        self.current_mode = "select"  # select, move
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
        
        self.setup_ui()
        
    def setup_styles(self):
        """Setup custom ttk styles for modern UI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern button styles
        style.configure('Modern.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 10),
                       font=('Segoe UI', 10, 'bold'))
        
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
                                    text="Ready - Load a TIFF image to begin",
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
                 
        tk.Button(button_frame, text="Save Project", command=self.save_project,
                 bg='#2196F3', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Load Project", command=self.load_project,
                 bg='#2196F3', fg='white', font=('Arial', 9), 
                 padx=10, pady=5).pack(side=tk.LEFT, padx=2)
                 
        tk.Button(button_frame, text="Export", command=self.export_image,
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
        tools_container = tk.Frame(parent, bg='#f0f0f0', width=280, relief='solid', bd=1)
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
        
        self.mode_var = tk.StringVar(value="select")
        
        # Mode indicator with better styling
        self.mode_indicator = tk.Label(mode_section, 
                                      text="Selection Mode - Draw around areas", 
                                      font=('Arial', 9),
                                      bg='#4CAF50', fg='white',
                                      padx=10, pady=5, relief='raised')
        self.mode_indicator.pack(fill=tk.X, pady=(0, 10))
        
        # Radio buttons in a frame
        radio_frame = tk.Frame(mode_section, bg='#f0f0f0')
        radio_frame.pack(fill=tk.X)
        
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
        
        self.grid_show_var = tk.BooleanVar()
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
        dpi_spinbox = tk.Spinbox(dpi_frame, from_=72, to=600, increment=10,
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
        
        self.spacing_value_label = tk.Label(spacing_label_frame, text="20%", 
                                           font=('Arial', 9), bg='#e0e0e0', fg='#333', 
                                           width=5, relief='sunken')
        self.spacing_value_label.pack(side=tk.RIGHT)
        
        spacing_control_frame = tk.Frame(spacing_frame, bg='#f0f0f0')
        spacing_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # More precise spacing control with decimal support
        self.spacing_var = tk.StringVar(value="20.0")
        spacing_spinbox = tk.Spinbox(spacing_control_frame, from_=1.0, to=50.0, increment=0.5,
                                    textvariable=self.spacing_var, width=8, format="%.1f",
                                    command=self.update_line_spacing, font=('Arial', 9))
        spacing_spinbox.pack(side=tk.LEFT)
        spacing_spinbox.bind('<Return>', lambda e: self.update_line_spacing())
        
        tk.Label(spacing_control_frame, text="% of image width", font=('Arial', 9),
                bg='#f0f0f0', fg='#666').pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick spacing presets
        preset_frame = tk.Frame(lines_config_frame, bg='#f0f0f0')
        preset_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(preset_frame, text="Presets:", font=('Arial', 8, 'bold'),
                bg='#f0f0f0', fg='#666').pack(anchor=tk.W)
        
        preset_buttons_frame = tk.Frame(preset_frame, bg='#f0f0f0')
        preset_buttons_frame.pack(fill=tk.X, pady=(2, 0))
        
        presets = [("Tight", "5.0"), ("Normal", "15.0"), ("Wide", "25.0"), ("Very Wide", "40.0")]
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
        sections_container = tk.Frame(parent, bg='#f0f0f0', width=300, relief='solid', bd=1)
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
        """Load a TIFF image"""
        file_path = filedialog.askopenfilename(
            title="Select TIFF Image",
            filetypes=[("TIFF files", "*.tiff *.tif"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.update_status("Loading image...")
                
                # Load with PIL for TIFF support
                self.original_image = Image.open(file_path)
                
                # Extract DPI from image metadata
                self._extract_and_set_dpi(file_path)
                
                # Convert to RGB if needed
                if self.original_image.mode != 'RGB':
                    self.original_image = self.original_image.convert('RGB')
                
                # Create working copy
                self.working_image = self.original_image.copy()
                
                # Clear existing selections
                self.current_selections = []
                self.clipped_sections = []
                self.update_sections_list()
                
                # Reset image controls
                self.width_var.set("100")
                self.height_var.set("100")
                self.image_scale = 1.0
                
                # Update image info
                width, height = self.original_image.size
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                self.update_image_info(f"{os.path.basename(file_path)} • {width}×{height} • {file_size:.1f}MB")
                
                # Update canvas info
                if hasattr(self, 'canvas_info_label'):
                    self.canvas_info_label.config(text=f"Image loaded: {width}×{height} pixels • Use mouse wheel to zoom, WASD/arrows to navigate")
                
                # Display image
                self.root.after(100, self.fit_to_window)  # Delay to ensure canvas is ready
                
                self.update_status(f"Successfully loaded {os.path.basename(file_path)} • Use mouse wheel to zoom, WASD/arrow keys to navigate")
                
            except Exception as e:
                self.update_status("Failed to load image")
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def _extract_and_set_dpi(self, file_path):
        """Extract DPI from image metadata and update the UI"""
        try:
            # Try to get DPI from PIL image info
            dpi_info = self.original_image.info.get('dpi', None)
            extracted_dpi = None
            
            if dpi_info:
                # DPI is usually returned as (x_dpi, y_dpi)
                if isinstance(dpi_info, (list, tuple)) and len(dpi_info) >= 2:
                    # Use the first DPI value (x_dpi)
                    extracted_dpi = int(dpi_info[0])
                elif isinstance(dpi_info, (int, float)):
                    extracted_dpi = int(dpi_info)
            
            # If no DPI in image info, try to get from EXIF data
            if not extracted_dpi and hasattr(self.original_image, '_getexif'):
                try:
                    exif = self.original_image._getexif()
                    if exif:
                        # EXIF tag 282 is XResolution, 283 is YResolution
                        x_resolution = exif.get(282)  # XResolution
                        if x_resolution:
                            if isinstance(x_resolution, (list, tuple)) and len(x_resolution) >= 2:
                                # Resolution is often stored as (numerator, denominator)
                                extracted_dpi = int(x_resolution[0] / x_resolution[1])
                            else:
                                extracted_dpi = int(x_resolution)
                except:
                    pass  # EXIF parsing failed, continue
            
            # If we found a DPI value, update the UI
            if extracted_dpi and extracted_dpi > 0:
                # Validate DPI is reasonable (between 72 and 1200)
                if 72 <= extracted_dpi <= 1200:
                    self.image_dpi = extracted_dpi
                    self.dpi_var.set(str(extracted_dpi))
                    self.update_status(f"Image DPI auto-detected: {extracted_dpi}")
                    
                    # Refresh the display for updated cm measurements
                    if self.show_grid:
                        self.root.after(200, self.display_image)
                else:
                    self.update_status(f"Found DPI {extracted_dpi} but seems unreasonable, keeping default {self.image_dpi}")
            else:
                # No DPI found in metadata
                filename = os.path.basename(file_path)
                self.update_status(f"No DPI metadata found in {filename}, using default {self.image_dpi} DPI")
                
        except Exception as e:
            # If anything goes wrong, just use default DPI
            filename = os.path.basename(file_path) if file_path else "image"
            self.update_status(f"Could not read DPI from {filename}, using default {self.image_dpi} DPI")
                
    def display_image(self):
        """Display the current image on canvas"""
        if self.original_image is None:
            return
            
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
            
            # Redraw selections
            self.redraw_selections()
            
            # Draw clipped sections on top
            self.draw_clipped_sections()
            
            # Draw vertical lines overlay if enabled (after a small delay to ensure canvas is updated)
            if self.show_lines:
                self.root.after(10, self.draw_vertical_lines)
            
            # Draw grid overlay if enabled
            if self.show_grid:
                self.root.after(15, self.draw_grid)
            
            # Draw ruler if enabled
            if self.show_ruler:
                self.root.after(20, self.draw_ruler)
            
        except Exception as e:
            print(f"Error in display_image: {e}")
            messagebox.showerror("Display Error", f"Failed to display image: {str(e)}")
        
    def redraw_selections(self):
        """Redraw current selection being drawn"""
        # Only show the current selection path being drawn (if any)
        pass
        
    def draw_clipped_sections(self):
        """Draw all clipped sections on the canvas"""
        # Clear section photos to prevent memory leaks
        self.section_photos = []
        
        for i, section in enumerate(self.clipped_sections):
            # Calculate scaled position
            x, y = section['position']
            scaled_x = int(x * self.image_scale)
            scaled_y = int(y * self.image_scale)
            
            # Scale the section image
            width, height = section['size']
            scaled_width = int(width * self.image_scale)
            scaled_height = int(height * self.image_scale)
            
            if scaled_width > 0 and scaled_height > 0:
                # Resize the clipped section for display
                display_section = section['image'].resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                section_photo = ImageTk.PhotoImage(display_section)
                
                # Store reference to prevent garbage collection
                self.section_photos.append(section_photo)
                
                # Draw on canvas
                self.canvas.create_image(scaled_x, scaled_y, anchor=tk.NW, image=section_photo, tags=f"clipped_{i}")
                
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
        
        if self.current_mode == "select":
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
        
        if self.current_mode == "select" and self.drawing:
            self.selection_path.append((image_x, image_y))
            
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
        
        if self.current_mode == "select" and self.drawing:
            self.drawing = False
            
            if len(self.selection_path) > 2:
                # Automatically clip and color the selection
                self.create_clipped_section(self.selection_path.copy(), self.selected_color)
                
            # Clear temporary drawing
            self.canvas.delete("temp_selection")
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
        
        # Show coordinates in coordinate label
        if hasattr(self, 'coord_label'):
            if self.snap_to_grid:
                snap_x, snap_y = self.snap_to_grid_position(image_x, image_y)
                self.coord_label.config(text=f"({image_x:.1f}, {image_y:.1f}) → ({snap_x:.0f}, {snap_y:.0f})")
            elif self.precise_mode:
                self.coord_label.config(text=f"({image_x:.2f}, {image_y:.2f})")
            else:
                self.coord_label.config(text=f"({int(image_x)}, {int(image_y)})")
    
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
        if len(path) < 3:
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
            
            self.clipped_sections.append(clipped_section)
            
            # Remove the area from the working image (create hole)
            hole_mask = Image.new('L', self.original_image.size, 255)
            hole_draw = ImageDraw.Draw(hole_mask)
            hole_draw.polygon(pil_path, fill=0)  # Black = transparent
            
            # Apply hole to working image
            working_rgba = self.working_image.convert('RGBA')
            working_rgba.putalpha(hole_mask)
            background = Image.new('RGB', self.original_image.size, (255, 255, 255))
            self.working_image = Image.alpha_composite(background.convert('RGBA'), working_rgba).convert('RGB')
            
            # Update the sections list
            self.update_sections_list()
            
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
        """Zoom in the image"""
        self.image_scale *= 1.2
        self.display_image()
        
    def zoom_out(self):
        """Zoom out the image"""
        self.image_scale /= 1.2
        self.display_image()
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if self.original_image is None:
            return
        
        # Simple zoom implementation
        old_scale = self.image_scale
        
        # Determine zoom direction - Windows uses delta, Linux uses num
        if hasattr(event, 'delta'):  # Windows
            if event.delta > 0:
                self.image_scale *= 1.1  # Zoom in
                self.update_status("Zoomed in with mouse wheel")
            else:
                self.image_scale /= 1.1  # Zoom out
                self.update_status("Zoomed out with mouse wheel")
        elif hasattr(event, 'num'):  # Linux
            if event.num == 4:
                self.image_scale *= 1.1  # Zoom in
                self.update_status("Zoomed in with mouse wheel")
            elif event.num == 5:
                self.image_scale /= 1.1  # Zoom out
                self.update_status("Zoomed out with mouse wheel")
        
        # Limit zoom range
        self.image_scale = max(0.1, min(10.0, self.image_scale))
        
        # Update display
        if old_scale != self.image_scale:
            self.display_image()
        else:
            self.update_status("Zoom at limit")
    
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
        """Fit image to window"""
        if self.original_image is None:
            return
            
        try:
            img_width, img_height = self.original_image.size
            
            # Update canvas to get current size
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Make sure canvas has reasonable dimensions
            if canvas_width > 50 and canvas_height > 50:
                scale_x = (canvas_width - 20) / img_width  # Leave some margin
                scale_y = (canvas_height - 20) / img_height
                self.image_scale = min(scale_x, scale_y, 1.0)
            else:
                # Fallback scale if canvas size is not available
                self.image_scale = 0.5
                
            self.display_image()
            
        except Exception as e:
            print(f"Error in fit_to_window: {e}")
            # Fallback: just display at current scale
            self.display_image()
            
    def change_mode(self):
        """Change the current operation mode with simple visual feedback"""
        self.current_mode = self.mode_var.get()
        
        # Update visual indicators based on mode
        if self.current_mode == "select":
            self.canvas.config(cursor="cross")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Selection Mode: Draw around parts of the image")
            # Update the mode indicator
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="Selection Mode - Draw around areas",
                                         bg='#4CAF50')
        else:
            self.canvas.config(cursor="arrow")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Move Mode: Drag sections to reposition them")
            # Update the mode indicator
            if hasattr(self, 'mode_indicator'):
                self.mode_indicator.config(text="Move Mode - Drag to reposition",
                                         bg='#2196F3')
        
    def toggle_lines(self):
        """Toggle vertical lines display"""
        self.show_lines = self.lines_var.get()
        
        # If turning off lines, also unlock them
        if not self.show_lines and self.lines_confirmed:
            self.unlock_lines()
            
        if self.original_image:
            self.display_image()
    
    def update_lines_count(self, value):
        """Update number of vertical lines (only if not confirmed)"""
        if self.lines_confirmed:
            return  # Don't allow changes when lines are confirmed
            
        self.num_lines = int(float(value))
        if self.show_lines and self.original_image:
            self.display_image()
    
    def update_line_spacing(self):
        """Update the spacing between vertical lines (only if not confirmed)"""
        if self.lines_confirmed:
            return  # Don't allow changes when lines are confirmed
            
        try:
            self.line_spacing_percent = float(self.spacing_var.get())
            if self.show_lines and self.original_image:
                self.display_image()
        except ValueError:
            # Reset to default if invalid value
            self.spacing_var.set("20")
            self.line_spacing_percent = 20
    
    def draw_vertical_lines(self):
        """Draw vertical lines overlay on canvas that scale with image"""
        if not self.original_image:
            return
            
        # Get image dimensions and scale
        orig_width, orig_height = self.original_image.size
        display_width = int(orig_width * self.image_scale)
        display_height = int(orig_height * self.image_scale)
        
        # Calculate line spacing based on user-defined percentage of image width
        line_spacing_image = orig_width * (self.line_spacing_percent / 100.0)
        
        # Store line positions in image coordinates for anchoring
        self.line_positions = []
        
        # Calculate starting position to center the lines
        total_width_needed = line_spacing_image * (self.num_lines - 1)
        start_x = (orig_width - total_width_needed) / 2
        
        # Draw vertical lines with custom spacing
        for i in range(self.num_lines):
            # Calculate position in image coordinates
            x_pos_image = start_x + (i * line_spacing_image)
            
            # Make sure lines stay within image bounds
            if x_pos_image >= 0 and x_pos_image <= orig_width:
                # Scale to display coordinates
                x_pos_display = x_pos_image * self.image_scale
                
                # Store the image coordinate position
                self.line_positions.append(x_pos_image)
                
                # Draw line from top to bottom of the displayed image
                line_color = '#00FF00' if self.lines_confirmed else '#FF0000'  # Green if confirmed, red if not
                line_width = 3 if self.lines_confirmed else 2
                
                self.canvas.create_line(x_pos_display, 0, x_pos_display, display_height,
                                       fill=line_color, width=line_width, tags="guide_lines")
    
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
            
        self.update_status(f"Lines confirmed! {self.num_lines} lines locked at {self.line_spacing_percent:.1f}% spacing")
    
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
            
        self.num_lines = int(float(value))
        if hasattr(self, 'lines_count_label'):
            self.lines_count_label.config(text=str(self.num_lines))
        
        if self.show_lines and self.original_image:
            self.display_image()
    
    def update_line_spacing(self):
        """Update the spacing between vertical lines with visual feedback"""
        if self.lines_confirmed:
            return  # Don't allow changes when lines are confirmed
            
        try:
            self.line_spacing_percent = float(self.spacing_var.get())
            if hasattr(self, 'spacing_value_label'):
                self.spacing_value_label.config(text=f"{self.line_spacing_percent:.1f}%")
            
            if self.show_lines and self.original_image:
                self.display_image()
        except ValueError:
            # Reset to default if invalid value
            self.spacing_var.set("20.0")
            self.line_spacing_percent = 20.0
            if hasattr(self, 'spacing_value_label'):
                self.spacing_value_label.config(text="20.0%")
    
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
    
    def update_dpi(self):
        """Update image DPI for accurate measurements"""
        try:
            self.image_dpi = int(self.dpi_var.get())
            if self.show_grid and self.original_image:
                self.display_image()
            self.update_status(f"Image DPI set to {self.image_dpi}")
        except ValueError:
            self.dpi_var.set("300")
            self.image_dpi = 300
    
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
            # Create hole mask
            hole_mask = Image.new('L', self.original_image.size, 255)
            hole_draw = ImageDraw.Draw(hole_mask)
            
            # Use original boundary to create hole
            original_boundary = [(x - (section['position'][0] - section['boundary'][0][0]), 
                                y - (section['position'][1] - section['boundary'][0][1])) 
                               for x, y in section['boundary']]
            
            pil_path = [(int(x), int(y)) for x, y in section['boundary']]
            hole_draw.polygon(pil_path, fill=0)  # Black = transparent
            
            # Apply hole to working image
            working_rgba = self.working_image.convert('RGBA')
            working_rgba.putalpha(hole_mask)
            background = Image.new('RGB', self.original_image.size, (255, 255, 255))
            self.working_image = Image.alpha_composite(background.convert('RGBA'), working_rgba).convert('RGB')
            
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
        """Export the current working image"""
        if self.working_image is None:
            messagebox.showwarning("Warning", "No image to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Export Image",
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff"), ("PNG files", "*.png"), 
                      ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.working_image.save(file_path)
                messagebox.showinfo("Success", "Image exported successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image: {str(e)}")


def main():
    root = tk.Tk()
    app = ImageEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
