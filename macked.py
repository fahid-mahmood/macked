import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import requests
from bs4 import BeautifulSoup
import time
import threading
from datetime import datetime, timedelta
import random
import re
import os
import json
from pathlib import Path

# Try to import PIL for icon handling
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Note: PIL is not installed, icon support may be limited")

# Column key mapping for older config files that used Chinese column names
LEGACY_COLUMN_KEYS = {
    '软件名称': 'Name',
    '软件版本': 'Version',
    '简介': 'Description',
    '更新时间': 'Updated',
    '评论数': 'Comments',
    '浏览量': 'Views',
    '点赞量': 'Likes',
    '破解方式': 'Activation',
    '正文链接': 'Link',
}

# Default column widths (English keys)
DEFAULT_COLUMN_WIDTHS = {
    'Name': 110,
    'Version': 69,
    'Description': 192,
    'Updated': 142,
    'Comments': 49,
    'Views': 81,
    'Likes': 50,
    'Activation': 53,
    'Link': 205,
}

class ClickableTreeview(ttk.Treeview):
    """Treeview with clickable links"""
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<Control-Button-1>", self.on_ctrl_click)  # Ctrl+click toggles favorite
        self.favorites = set()  # favorited software names
        self.log_func = None  # log callback function

    def on_click(self, event):
        region = self.identify("region", event.x, event.y)
        if region == "cell":
            row_id = self.identify_row(event.y)
            col_id = self.identify_column(event.x)
            # Get the column index
            col_index = int(col_id.replace('#', '')) - 1  # convert to 0-based index
            if col_index == 8:  # link column (index 8)
                values = self.item(row_id)['values']
                if values and len(values) > 8:
                    link = values[8]  # link
                    if link and link.startswith(('http://', 'https://')):
                        webbrowser.open(link)

    def on_ctrl_click(self, event):
        """Ctrl+click toggles favorite"""
        region = self.identify("region", event.x, event.y)
        if region == "cell":
            row_id = self.identify_row(event.y)
            values = self.item(row_id)['values']
            if values and len(values) > 0:
                software_name = values[0]  # Name column
                if software_name in self.favorites:
                    # Remove from favorites
                    self.favorites.remove(software_name)
                    # Recompute tags
                    tags = []
                    if 'recent' in self.item(row_id, 'tags'):
                        tags.append('recent')
                    self.item(row_id, tags=tuple(tags))
                    if self.log_func:
                        self.log_func(f"Removed from favorites: {software_name}")
                else:
                    # Add to favorites
                    self.favorites.add(software_name)
                    # Keep existing 'recent' tag and add 'favorite'
                    existing_tags = list(self.item(row_id, 'tags'))
                    if 'favorite' not in existing_tags:
                        existing_tags.append('favorite')
                    self.item(row_id, tags=tuple(existing_tags))
                    if self.log_func:
                        self.log_func(f"Added to favorites: {software_name}")

class MackedScraperGUI:
    def __init__(self, root):
        self.root = root
        version = get_app_version()
        self.root.title(f"Macked v{version}")
        self.root.geometry("1000x700")

        # Set the app icon
        self.set_icon()

        # Center the window
        self.center_window()

        # Configuration
        self.BASE_URL = "https://macked.app/"

        # User agent list, simulating different browsers
        self.USER_AGENTS = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

        # Referer list, simulating traffic from different sites
        self.REFERERS = [
            "https://www.qq.com",
            "https://www.sohu.com",
            "https://www.cctv.com",
            "https://www.1688.com",
            "https://www.12306.cn",
            "https://www.youku.com",
            "https://www.douban.com"
        ]

        self.stop_flag = threading.Event()  # flag used to stop scraping
        self.software_data_cache = []  # cached scraped data
        self.all_software_data_cache = []  # global cache of all data
        self.config_file = self.get_config_path()  # config file path
        self.load_config()  # load configuration
        self.setup_ui()

    def get_config_path(self):
        """Return the config file path, using ~/Library/Application Support/macked/"""
        # Create the application support directory
        app_support_dir = Path.home() / 'Library' / 'Application Support' / 'macked'
        app_support_dir.mkdir(parents=True, exist_ok=True)
        return app_support_dir / 'app_config.json'

    def set_icon(self):
        # Try several ways to set the icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_paths = [
            os.path.join(script_dir, "macked.icns"),
            os.path.join(script_dir, "macked.png"),
            os.path.join(script_dir, "macked.ico"),
            "macked.icns",
            "macked.png",
            "macked.ico"
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # Try to process the image with PIL
                    if PIL_AVAILABLE:
                        img = Image.open(icon_path)
                        # For PNG/JPG, resize to a suitable icon size
                        if icon_path.endswith(('.png', '.jpg', '.jpeg', '.ico')):
                            img = img.resize((32, 32))
                        photo = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, photo)
                        # Keep a reference to the image so it is not garbage collected
                        self.icon_photo = photo
                        print(f"Icon set: {icon_path}")
                        return
                except Exception as e:
                    print(f"Failed to set icon ({icon_path}): {e}")
                    continue

        print("Icon file not found or icon setup failed")

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def load_config(self):
        """Load the configuration file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Migrate legacy Chinese column keys to English, then fill in defaults
                    saved_widths = {LEGACY_COLUMN_KEYS.get(k, k): v
                                    for k, v in config.get('column_widths', {}).items()}
                    self.column_widths = {**DEFAULT_COLUMN_WIDTHS, **saved_widths}
                    self.window_size = config.get('window_size', [1000, 700])
                    self.favorites = set(config.get('favorites', []))  # load favorites
                self.root.geometry(f"{self.window_size[0]}x{self.window_size[1]}")
            else:
                # Default column widths
                self.column_widths = dict(DEFAULT_COLUMN_WIDTHS)
                self.window_size = [1000, 700]
                self.favorites = set()  # initialize as empty set
        except Exception as e:
            print(f"Failed to load config: {e}")
            self.column_widths = dict(DEFAULT_COLUMN_WIDTHS)
            self.window_size = [1000, 700]
            self.favorites = set()

    def save_config(self):
        """Save the configuration file"""
        try:
            # Get the current window size
            self.window_size = [self.root.winfo_width(), self.root.winfo_height()]

            # Get the current column widths
            for col in self.tree['columns']:
                self.column_widths[col] = self.tree.column(col, 'width')

            config = {
                'column_widths': self.column_widths,
                'window_size': self.window_size,
                'favorites': list(self.favorites)  # save favorites
            }

            # Write the config file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def setup_ui(self):
        # Create the main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top settings area
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Pages to fetch setting
        label_pages = ttk.Label(settings_frame, text="Pages to fetch:")
        label_pages.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.pages_var = tk.StringVar(value="3")
        pages_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, width=10, textvariable=self.pages_var)
        pages_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        # Delay setting
        label_delay = ttk.Label(settings_frame, text="Delay between pages (s):")
        label_delay.grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.delay_var = tk.StringVar(value="1")
        delay_spinbox = ttk.Spinbox(settings_frame, from_=1, to=300, width=10, textvariable=self.delay_var)
        delay_spinbox.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        # Checkbox: only show updates from the last 24 hours
        self.show_recent_only_var = tk.BooleanVar()
        self.recent_only_check = ttk.Checkbutton(settings_frame, text="Show last 24h only",
                                                 variable=self.show_recent_only_var,
                                                 command=self.toggle_display_filter)
        self.recent_only_check.grid(row=0, column=4, padx=(0, 10))

        # Start and Stop buttons
        self.start_btn = ttk.Button(settings_frame, text="Start", command=self.start_scraping)
        self.start_btn.grid(row=0, column=5, padx=(10, 5))

        self.stop_btn = ttk.Button(settings_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=6, padx=(0, 0))

        # Data table area
        table_frame = ttk.LabelFrame(main_frame, text="Results", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create the clickable Treeview
        columns = ("Name", "Version", "Description", "Updated", "Comments", "Views", "Likes", "Activation", "Link")
        self.tree = ClickableTreeview(table_frame, columns=columns, show="headings", height=15)
        self.tree.favorites = self.favorites  # pass the favorites set to the Treeview
        self.tree.log_func = self.log_message  # set the log callback

        # Set column headings and widths
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            # Use the saved width if available, otherwise the default
            width = self.column_widths.get(col, 120)
            self.tree.column(col, width=width, anchor=tk.W)

        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        # Lay out the Treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        # Bind column resize events
        self.tree.bind('<B1-Motion>', self.on_column_resize)

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Status output area - half the original height
        status_frame = ttk.LabelFrame(main_frame, text="Log", padding=5)
        status_frame.pack(fill=tk.X, expand=False)

        self.log_text = scrolledtext.ScrolledText(status_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 0))

        # Initialize styles
        style = ttk.Style()
        style.configure("Green.Treeview", foreground="green")
        style.configure("Blue.Treeview", foreground="blue")
        style.configure("Treeview", font=("TkDefaultFont", 14), rowheight=25)
        style.configure("Treeview.Heading", font=("TkDefaultFont", 14))
        style.configure("TLabel", font=("TkDefaultFont", 14))
        style.configure("TButton", font=("TkDefaultFont", 14))
        style.configure("TCheckbutton", font=("TkDefaultFont", 14))
        style.configure("TSpinbox", font=("TkDefaultFont", 14))
        style.configure("TLabelFrame.Label", font=("TkDefaultFont", 14))

    def on_column_resize(self, event):
        """Track column resize events"""
        # Debounce saving with a timer to avoid saving too often
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(500, self.save_config)

    def sort_column(self, col):
        """Sort by column"""
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]

        # Special handling for the time column
        if col == "Updated":
            # Try to parse times and sort
            def parse_time(val):
                # Try various time formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M'
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(val, fmt)
                    except ValueError:
                        continue

                # If standard formats fail, try relative time descriptions (e.g. "18小时前" = 18 hours ago)
                if "小时" in val or "分钟" in val or "天" in val:
                    now = datetime.now()
                    if "小时前" in val:
                        hours = int(re.search(r'(\d+)小时前', val)[1]) if re.search(r'(\d+)小时前', val) else 0
                        return now - timedelta(hours=hours)
                    elif "分钟前" in val:
                        minutes = int(re.search(r'(\d+)分钟前', val)[1]) if re.search(r'(\d+)分钟前', val) else 0
                        return now - timedelta(minutes=minutes)
                    elif "天前" in val:
                        days = int(re.search(r'(\d+)天前', val)[1]) if re.search(r'(\d+)天前', val) else 0
                        return now - timedelta(days=days)

                # Fall back to the current time
                return datetime.now()

            # Sort by parsed time (newest first)
            data.sort(key=lambda x: parse_time(x[0]), reverse=True)
        else:
            # Other columns sort alphabetically
            data.sort(reverse=True)

        for index, (_, child) in enumerate(data):
            self.tree.move(child, '', index)

        # Re-apply color tags after sorting
        self.update_time_colors()

    def auto_sort_by_time(self):
        """Auto-sort by update time (newest first)"""
        data = [(self.tree.set(child, "Updated"), child) for child in self.tree.get_children('')]

        # Parse times and sort
        def parse_time(val):
            # Try various time formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y %H:%M'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue

            # If standard formats fail, try relative time descriptions (e.g. "18小时前" = 18 hours ago)
            if "小时" in val or "分钟" in val or "天" in val:
                now = datetime.now()
                if "小时前" in val:
                    hours = int(re.search(r'(\d+)小时前', val)[1]) if re.search(r'(\d+)小时前', val) else 0
                    return now - timedelta(hours=hours)
                elif "分钟前" in val:
                    minutes = int(re.search(r'(\d+)分钟前', val)[1]) if re.search(r'(\d+)分钟前', val) else 0
                    return now - timedelta(minutes=minutes)
                elif "天前" in val:
                    days = int(re.search(r'(\d+)天前', val)[1]) if re.search(r'(\d+)天前', val) else 0
                    return now - timedelta(days=days)

            # Fall back to the current time
            return datetime.now()

        # Sort by parsed time (newest first)
        data.sort(key=lambda x: parse_time(x[0]), reverse=True)

        for index, (_, child) in enumerate(data):
            self.tree.move(child, '', index)

        # Re-apply color tags after sorting
        self.update_time_colors()

    def update_time_colors(self):
        """Update row colors: green for updates within 24 hours"""
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values and len(values) > 3:  # make sure the Updated column exists
                update_time_str = values[3]  # Updated column
                software_name = values[0]  # Name column

                # Parse the time
                parsed_time = self.parse_datetime(update_time_str)
                current_time = datetime.now()
                time_diff = current_time - parsed_time

                # Build the tag list
                tags = []

                # Favorites take priority
                if software_name in self.favorites:
                    tags.append('favorite')  # favorite wins
                elif time_diff <= timedelta(hours=24):
                    tags.append('recent')  # only show as recent when not a favorite

                # Apply tags
                self.tree.item(item, tags=tuple(tags))

        # Configure styles
        self.tree.tag_configure('recent', foreground='green')
        self.tree.tag_configure('favorite', foreground='blue')

    def parse_datetime(self, date_str):
        """Parse a date/time string into a datetime object"""
        # Handle various time formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # If standard formats fail, try relative time descriptions (e.g. "18小时前" = 18 hours ago)
        if "小时" in date_str or "分钟" in date_str or "天" in date_str:
            now = datetime.now()
            if "小时前" in date_str:
                hours = int(re.search(r'(\d+)小时前', date_str)[1]) if re.search(r'(\d+)小时前', date_str) else 0
                return now - timedelta(hours=hours)
            elif "分钟前" in date_str:
                minutes = int(re.search(r'(\d+)分钟前', date_str)[1]) if re.search(r'(\d+)分钟前', date_str) else 0
                return now - timedelta(minutes=minutes)
            elif "天前" in date_str:
                days = int(re.search(r'(\d+)天前', date_str)[1]) if re.search(r'(\d+)天前', date_str) else 0
                return now - timedelta(days=days)

        # Fall back to the current time
        return datetime.now()

    def log_message(self, message):
        """Append a message to the log box"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def generate_random_headers(self):
        """Generate random request headers, different for every request"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(["zh-CN,zh;q=0.9,en;q=0.8", "en-US,en;q=0.9,zh-CN;q=0.8", "zh-TW,zh;q=0.8,en;q=0.9"]),
            "Referer": random.choice(self.REFERERS),
            "Connection": "keep-alive",
            "Accept-Encoding": random.choice(["gzip, deflate", "gzip", "deflate", "identity"]),
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }

    def convert_view_count(self, view_text):
        """Convert view count text to a number, handling the W+ format"""
        if not view_text:
            return "0"

        # Remove whitespace
        view_text = view_text.strip()

        # Check for W+ (or 万+)
        if 'W+' in view_text.upper() or '万+' in view_text:
            # Extract the number part
            number_match = re.search(r'([\d.]+)', view_text)
            if number_match:
                number = float(number_match.group(1))
                # Multiply by 10000
                converted_number = int(number * 10000)
                return str(converted_number)

        # If not W+ format, try to extract plain digits
        number_match = re.search(r'(\d+)', view_text)
        if number_match:
            return number_match.group(1)

        # If no digits found, return the original text
        return view_text

    def extract_crack_method_from_tippy(self, tippy_content):
        """Extract the activation method from data-tippy-content"""
        if not tippy_content:
            return "Unknown"

        # Parse the HTML inside tippy_content
        try:
            soup = BeautifulSoup(tippy_content, "html.parser")
            # Find the activation-method row ("激活方式")
            activation_elements = soup.find_all(class_="attr-key")
            for element in activation_elements:
                if "激活方式" in element.get_text():
                    parent_div = element.parent
                    attr_value = parent_div.find(class_="attr-value")
                    if attr_value:
                        return attr_value.get_text(strip=True)
        except Exception as e:
            print(f"Failed to parse tippy content: {e}")

        return "Unknown"

    def toggle_display_filter(self):
        """Toggle the display filter based on the last-24h checkbox"""
        if hasattr(self, 'all_software_data_cache'):  # check for cached data
            if self.show_recent_only_var.get():  # only show updates from last 24h
                self.apply_time_filter()
            else:  # show all data
                self.show_all_cached_data()

    def apply_time_filter(self):
        """Apply the time filter, showing only data from the last 24 hours"""
        # Clear the current table
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Show only data from the last 24 hours
        for software in self.all_software_data_cache:
            update_time = software["Updated"]
            parsed_time = self.parse_datetime(update_time)
            current_time = datetime.now()
            time_diff = current_time - parsed_time

            if time_diff <= timedelta(hours=24):
                values = (
                    software["Name"],
                    software["Version"],
                    software["Description"],
                    software["Updated"],
                    software["Comments"],
                    software["Views"],
                    software["Likes"],
                    software["Activation"],
                    software["Link"]
                )
                item_id = self.tree.insert("", tk.END, values=values)

                # Set color tags - favorites win
                tags = []
                if software["Name"] in self.favorites:
                    tags.append('favorite')  # favorite wins
                else:
                    tags.append('recent')  # within 24 hours
                self.tree.item(item_id, tags=tuple(tags))

    def show_all_cached_data(self):
        """Show all cached data"""
        # Clear the current table
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Show all cached data
        for software in self.all_software_data_cache:
            values = (
                software["Name"],
                software["Version"],
                software["Description"],
                software["Updated"],
                software["Comments"],
                software["Views"],
                software["Likes"],
                software["Activation"],
                software["Link"]
            )
            item_id = self.tree.insert("", tk.END, values=values)

            # Set color tags - favorites win
            tags = []
            # Check whether within the last 24 hours
            update_time = software["Updated"]
            parsed_time = self.parse_datetime(update_time)
            current_time = datetime.now()
            time_diff = current_time - parsed_time

            if software["Name"] in self.favorites:
                tags.append('favorite')  # favorite wins
            elif time_diff <= timedelta(hours=24):
                tags.append('recent')  # only show as recent when not a favorite

            self.tree.item(item_id, tags=tuple(tags))

    def fetch_webpage(self, url):
        """Send a request and return the page content"""
        try:
            # Random delay to avoid being blocked for rapid requests
            delay = random.uniform(5, 10)
            self.log_message(f"Waiting {delay:.1f}s before requesting the page...")
            time.sleep(delay)

            # Check whether we should stop
            if self.stop_flag.is_set():
                return None

            # Use random headers for every request
            headers = self.generate_random_headers()

            response = requests.get(url, headers=headers, timeout=15, verify=False)
            # Check the response status code
            response.raise_for_status()
            # Set the correct encoding (avoid mojibake)
            response.encoding = response.apparent_encoding
            return response.text
        except requests.exceptions.RequestException as e:
            self.log_message(f"Request failed: {e}")
            return None

    def parse_software_list(self, html_text):
        """Parse page HTML and extract the software list"""
        software_list = []
        if not html_text:
            return software_list

        soup = BeautifulSoup(html_text, "html.parser")

        # Select the right elements for the actual HTML structure
        software_items = soup.select("posts.posts-item.ajax-item.card")

        for item in software_items:
            try:
                # Check whether we should stop
                if self.stop_flag.is_set():
                    break

                # Check for pinned content (no longer used as a stop condition)
                is_pinned = bool(item.select_one("badge.img-badge.left"))

                # 1. Software name and version
                title_elem = item.select_one("h2.item-heading a")
                full_title = title_elem.get_text(strip=True) if title_elem else "Unknown"

                # Split name and version from the title
                name = "Unknown"
                version = "Unknown"
                crack_method = "Unknown"
                if full_title:
                    # Try to split name and version with a regex
                    match = re.search(r'^(.+?)\s+(\d+\.\d+(?:\.\d+)?)', full_title)
                    if match:
                        name = match.group(1).strip()
                        version = match.group(2)
                    else:
                        name = full_title

                # Extract the activation method
                link_elem_with_attrs = item.select_one("h2.item-heading a[data-tippy-content]")
                if link_elem_with_attrs:
                    tippy_content = link_elem_with_attrs.get('data-tippy-content', '')
                    crack_method = self.extract_crack_method_from_tippy(tippy_content)

                # 2. Link (join into a full URL to avoid relative paths)
                link_elem = item.select_one("h2.item-heading a")
                link = link_elem["href"] if link_elem else ""
                full_link = requests.compat.urljoin(self.BASE_URL, link) if link else ""

                # 3. Description
                desc_elem = item.select_one("div.item-body div[style*='color: #888']")
                description = desc_elem.get_text(strip=True) if desc_elem else "No description"

                # 4. Update time
                time_elem = item.select_one("item[title]")
                update_time = time_elem["title"] if time_elem else "Unknown"

                # 5. Comment count
                comment_elem = item.select_one("item.meta-comm a")
                comment_count = "0"
                if comment_elem:
                    # Extract the count, e.g. digits out of "icon 0"
                    comment_text = comment_elem.get_text(strip=True)
                    numbers = re.findall(r'\d+', comment_text)
                    comment_count = numbers[0] if numbers else "0"

                # 6. View count - handle the W+ format
                view_elem = item.select_one("item.meta-view")
                if not view_elem:
                    view_elem = item.select_one(".meta-view, .views, .view-count")
                view_count = "0"
                if view_elem:
                    view_text = view_elem.get_text(strip=True)
                    # Convert the view format (e.g. 1.1W+ -> 11000)
                    view_count = self.convert_view_count(view_text)

                # 7. Like count
                like_elem = item.select_one("item.meta-like")
                like_count = "0"
                if like_elem:
                    like_text = like_elem.get_text(strip=True)
                    numbers = re.findall(r'\d+', like_text)
                    like_count = numbers[0] if numbers else "0"

                # Assemble the dictionary
                software_info = {
                    "Name": name,
                    "Version": version,
                    "Description": description,
                    "Updated": update_time,
                    "Comments": comment_count,
                    "Views": view_count,  # now a converted number
                    "Likes": like_count,
                    "Activation": crack_method,
                    "Link": full_link
                }
                software_list.append(software_info)
                self.log_message(f"Extracted: {name} v{version} (updated: {update_time}, views: {view_count}, activation: {crack_method})")

            except Exception as e:
                self.log_message(f"Failed to parse item: {e}")
                continue

        return software_list

    def get_next_page_url(self, current_url, page_num):
        """Build the next page URL"""
        if page_num == 1:
            # Page 1 to page 2
            return f"{self.BASE_URL}page/2/"
        else:
            # Page 2 and later
            return f"{self.BASE_URL}page/{page_num + 1}/"

    def scrape_multiple_pages(self, total_pages=5):
        """Scrape the requested number of pages"""
        all_software_data = []
        current_url = self.BASE_URL
        page_num = 1

        self.log_message(f"Starting scrape of {total_pages} page(s)...")

        while page_num <= total_pages and not self.stop_flag.is_set():
            self.log_message(f"Fetching page {page_num}: {current_url}")

            # Update the progress bar
            progress_value = (page_num - 1) / total_pages * 100
            self.progress['value'] = progress_value
            self.root.update_idletasks()

            # Check whether we should stop
            if self.stop_flag.is_set():
                self.log_message("Stop requested by user")
                break

            # Fetch the current page
            html = self.fetch_webpage(current_url)
            if not html:
                self.log_message(f"Could not fetch page {page_num}, aborting")
                break

            # Parse the current page
            page_data = self.parse_software_list(html)

            # Cache the data
            all_software_data.extend(page_data)

            # Add the current page's data to the table
            for software in page_data:
                values = (
                    software["Name"],
                    software["Version"],
                    software["Description"],
                    software["Updated"],
                    software["Comments"],
                    software["Views"],
                    software["Likes"],
                    software["Activation"],
                    software["Link"]
                )
                # If the last-24h filter is on, only show matching rows
                if self.show_recent_only_var.get():
                    update_time = software["Updated"]
                    parsed_time = self.parse_datetime(update_time)
                    current_time = datetime.now()
                    time_diff = current_time - parsed_time

                    if time_diff <= timedelta(hours=24):
                        item_id = self.tree.insert("", tk.END, values=values)

                        # Set color tags - favorites win
                        tags = []
                        if software["Name"] in self.favorites:
                            tags.append('favorite')  # favorite wins
                        else:
                            tags.append('recent')  # within 24 hours
                        self.tree.item(item_id, tags=tuple(tags))
                else:
                    # No filter, add directly
                    item_id = self.tree.insert("", tk.END, values=values)

                    # Compute the time difference for tag assignment
                    update_time = software["Updated"]
                    parsed_time = self.parse_datetime(update_time)
                    current_time = datetime.now()
                    time_diff = current_time - parsed_time

                    # Set color tags - favorites win
                    tags = []
                    if software["Name"] in self.favorites:
                        tags.append('favorite')  # favorite wins
                    elif time_diff <= timedelta(hours=24):
                        tags.append('recent')  # only show as recent when not a favorite

                    self.tree.item(item_id, tags=tuple(tags))

            # Add the current page's data to the global cache
            self.all_software_data_cache.extend(page_data)

            # If this is the last page, end the loop
            if page_num >= total_pages:
                self.log_message(f"Reached the configured {total_pages} page(s), stopping")
                break

            # Check whether we should stop
            if self.stop_flag.is_set():
                self.log_message("Stop requested by user")
                break

            # Pause for the configured delay before the next page
            delay_seconds = int(self.delay_var.get())
            self.log_message(f"Page {page_num} done, pausing {delay_seconds}s before continuing...")

            # Keep checking the stop flag during the pause
            for _ in range(delay_seconds):
                if self.stop_flag.is_set():
                    self.log_message("Stop requested by user")
                    return all_software_data
                time.sleep(1)

            # Build the next page URL
            next_url = self.get_next_page_url(current_url, page_num)

            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
            else:
                self.log_message("No next page found, stopping")
                break

        # Finish the progress bar
        self.progress['value'] = 100
        return all_software_data

    def start_scraping(self):
        """Start scraping (runs in a thread)"""
        # Reset the stop flag
        self.stop_flag.clear()

        # Disable Start, enable Stop
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Clear the table
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Reset the progress bar
        self.progress['value'] = 0

        # Read the settings
        try:
            total_pages = int(self.pages_var.get())
            if total_pages <= 0:
                raise ValueError("Pages must be greater than 0")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of pages")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            return

        # Run the scrape in a new thread
        def scraping_task():
            try:
                # Scrape the data
                software_data = self.scrape_multiple_pages(total_pages=total_pages)

                if not software_data:
                    self.log_message("No software information extracted")
                else:
                    # Update the global cache
                    self.all_software_data_cache = software_data

                    self.log_message(f"Scrape complete! Extracted {len(software_data)} items")
                    # Auto-sort by time after scraping
                    self.auto_sort_by_time()

                    # Apply the filter according to the checkbox
                    if self.show_recent_only_var.get():
                        self.apply_time_filter()

            except Exception as e:
                self.log_message(f"Error during scraping: {e}")
            finally:
                # Re-enable Start, disable Stop
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.progress['value'] = 0

        # Start the scraping thread
        thread = threading.Thread(target=scraping_task)
        thread.daemon = True
        thread.start()

    def stop_scraping(self):
        """Stop scraping"""
        self.stop_flag.set()
        self.log_message("Stopping...")
        self.stop_btn.config(state=tk.DISABLED)
def get_app_version():
    """Get the application version"""
    try:
        with open('version.json', 'r') as f:
            config = json.load(f)
            return config.get('version', 'Unknown')
    except FileNotFoundError:
        # Try the resource path (location after packaging)
        import os
        resource_path = os.path.join(os.path.dirname(__file__), 'version.json')
        try:
            with open(resource_path, 'r') as f:
                config = json.load(f)
                return config.get('version', 'Unknown')
        except FileNotFoundError:
            return '1.0.0'
def main():
    root = tk.Tk()
    app = MackedScraperGUI(root)

    # Save the configuration when the app closes
    def on_closing():
        app.save_config()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    # Disable SSL warnings to avoid noise from verify=False requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
