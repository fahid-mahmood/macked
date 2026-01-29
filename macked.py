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

# 尝试导入PIL，用于处理图标
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("注意：未安装PIL库，图标功能可能受限")

class ClickableTreeview(ttk.Treeview):
    """可点击链接的Treeview"""
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.bind("<ButtonRelease-1>", self.on_click)
        
    def on_click(self, event):
        region = self.identify("region", event.x, event.y)
        if region == "cell":
            row_id = self.identify_row(event.y)
            col_id = self.identify_column(event.x)
            # 获取列索引
            col_index = int(col_id.replace('#', '')) - 1  # 转换为0基索引
            if col_index == 8:  # 正文链接列（索引8）
                values = self.item(row_id)['values']
                if values and len(values) > 8:
                    link = values[8]  # 正文链接
                    if link and link.startswith(('http://', 'https://')):
                        webbrowser.open(link)

class MackedScraperGUI:
    def __init__(self, root):
        self.root = root
        version = get_app_version()
        self.root.title(f"Macked v{version}")
        self.root.geometry("1000x700")
        
        # 设置程序图标
        self.set_icon()
        
        # 居中显示窗口
        self.center_window()
        
        # 配置项
        self.BASE_URL = "https://macked.app/"
        
        # 用户代理列表，模拟不同的浏览器
        self.USER_AGENTS = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

        # Referer 列表，模拟来自不同网站的访问
        self.REFERERS = [
            "https://www.qq.com",
            "https://www.sohu.com",
            "https://www.cctv.com",
            "https://www.1688.com",
            "https://www.12306.cn",
            "https://www.youku.com",
            "https://www.douban.com"
        ]
        
        self.stop_flag = threading.Event()  # 用于停止抓取的标志
        self.software_data_cache = []  # 缓存抓取的数据
        self.all_software_data_cache = []  # 全局缓存所有数据
        self.config_file = "app_config.json"  # 配置文件
        self.load_config()  # 加载配置
        self.setup_ui()
        
    def set_icon(self):
        # 尝试多种方法设置图标
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_paths = [
            os.path.join(script_dir, "macked.icns"),
            os.path.join(script_dir, "macked.png"),
            os.path.join(script_dir, "macked.ico"),  # 添加ico格式
            "macked.icns",
            "macked.png",
            "macked.ico"
        ]
    
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # 尝试使用PIL处理图像
                    if PIL_AVAILABLE:
                        img = Image.open(icon_path)
                        # 如果是PNG/JPG，转换为适合图标的尺寸
                        if icon_path.endswith(('.png', '.jpg', '.jpeg', '.ico')):
                            img = img.resize((32, 32))  # 调整尺寸
                        photo = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, photo)
                        # 保持对图像的引用，防止被垃圾回收
                        self.icon_photo = photo
                        print(f"成功设置图标：{icon_path}")
                        return
                except Exception as e:
                    print(f"设置图标失败 ({icon_path}): {e}")
                    continue
    
        print("未找到图标文件或设置图标失败")
    
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.column_widths = config.get('column_widths', {
                        '软件名称': 110,
                        '软件版本': 69,
                        '简介': 192,
                        '更新时间': 142,
                        '评论数': 49,
                        '浏览量': 81,
                        '点赞量': 50,
                        '破解方式': 53,
                        '正文链接': 205
                    })
                    self.window_size = config.get('window_size', [1000, 700])
                self.root.geometry(f"{self.window_size[0]}x{self.window_size[1]}")
            else:
                # 默认列宽
                self.column_widths = {
                    '软件名称': 110,
                    '软件版本': 69,
                    '简介': 192,
                    '更新时间': 142,
                    '评论数': 49,
                    '浏览量': 81,
                    '点赞量': 50,
                    '破解方式': 53,
                    '正文链接': 205
                }
                self.window_size = [1000, 700]
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.column_widths = {
                '软件名称': 110,
                '软件版本': 69,
                '简介': 192,
                '更新时间': 142,
                '评论数': 49,
                '浏览量': 81,
                '点赞量': 50,
                '破解方式': 53,
                '正文链接': 205
            }
            self.window_size = [1000, 700]
    
    def save_config(self):
        """保存配置文件"""
        try:
            # 获取当前窗口大小
            self.window_size = [self.root.winfo_width(), self.root.winfo_height()]
            
            # 获取当前列宽
            for col in self.tree['columns']:
                self.column_widths[col] = self.tree.column(col, 'width')
            
            config = {
                'column_widths': self.column_widths,
                'window_size': self.window_size
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="设置", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 抓取页数设置
        ttk.Label(settings_frame, text="抓取页数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.pages_var = tk.StringVar(value="3")
        pages_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, width=10, textvariable=self.pages_var)
        pages_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 暂停时间设置
        ttk.Label(settings_frame, text="页面间暂停时间(秒):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.delay_var = tk.StringVar(value="1")
        delay_spinbox = ttk.Spinbox(settings_frame, from_=1, to=300, width=10, textvariable=self.delay_var)
        delay_spinbox.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # 仅显示24小时内更新的复选框
        self.show_recent_only_var = tk.BooleanVar()
        self.recent_only_check = ttk.Checkbutton(settings_frame, text="仅显示24小时内更新", 
                                                 variable=self.show_recent_only_var, 
                                                 command=self.toggle_display_filter)
        self.recent_only_check.grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        
        # 开始和结束按钮
        self.start_btn = ttk.Button(settings_frame, text="开始", command=self.start_scraping)
        self.start_btn.grid(row=0, column=5, padx=(10, 5))
        
        self.stop_btn = ttk.Button(settings_frame, text="结束", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=6, padx=(0, 0))
        
        # 数据表格区域
        table_frame = ttk.LabelFrame(main_frame, text="抓取结果", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建可点击链接的Treeview
        columns = ("软件名称", "软件版本", "简介", "更新时间", "评论数", "浏览量", "点赞量", "破解方式", "正文链接")
        self.tree = ClickableTreeview(table_frame, columns=columns, show="headings", height=20)  # 增加了height值
        
        # 设置列标题和宽度
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            # 使用保存的列宽，如果没有则使用默认值
            width = self.column_widths.get(col, 120)
            self.tree.column(col, width=width, anchor=tk.W)
        
        # 添加滚动条
        tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # 布局Treeview和滚动条
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        # 绑定列宽改变事件
        self.tree.bind('<B1-Motion>', self.on_column_resize)
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 状态输出区域 - 高度减少为原来的一半
        status_frame = ttk.LabelFrame(main_frame, text="执行日志", padding=5)
        status_frame.pack(fill=tk.X, expand=False)  # 改为fill=tk.X, expand=False
        
        self.log_text = scrolledtext.ScrolledText(status_frame, height=4, state=tk.DISABLED)  # 从8改为4
        self.log_text.pack(fill=tk.X)  # 改为fill=tk.X
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
        # 初始化样式
        style = ttk.Style()
        style.configure("Green.Treeview", foreground="green")
        
    def on_column_resize(self, event):
        """监听列宽改变事件"""
        # 使用定时器延迟保存，避免频繁保存
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(500, self.save_config)
    
    def sort_column(self, col):
        """按列排序"""
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        # 对时间列特殊处理
        if col == "更新时间":
            # 尝试解析时间并排序
            def parse_time(val):
                # 尝试解析不同格式的时间
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
                
                # 如果标准格式失败，尝试处理相对时间描述（如"18小时前"）
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
                
                # 默认返回当前时间
                return datetime.now()
            
            # 按解析后的时间排序（最新的在前）
            data.sort(key=lambda x: parse_time(x[0]), reverse=True)
        else:
            # 其他列按字母顺序排序
            data.sort(reverse=True)
        
        for index, (_, child) in enumerate(data):
            self.tree.move(child, '', index)
        
        # 更新颜色
        self.update_time_colors()
    
    def auto_sort_by_time(self):
        """自动按更新时间排序（最新的在前）"""
        data = [(self.tree.set(child, "更新时间"), child) for child in self.tree.get_children('')]
        
        # 解析时间并排序
        def parse_time(val):
            # 尝试解析不同格式的时间
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
            
            # 如果标准格式失败，尝试处理相对时间描述（如"18小时前"）
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
            
            # 默认返回当前时间
            return datetime.now()
        
        # 按解析后的时间排序（最新的在前）
        data.sort(key=lambda x: parse_time(x[0]), reverse=True)
        
        for index, (_, child) in enumerate(data):
            self.tree.move(child, '', index)
        
        # 更新颜色
        self.update_time_colors()
    
    def update_time_colors(self):
        """更新时间列的颜色，24小时内为绿色"""
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values and len(values) > 3:  # 确保有更新时间列
                update_time_str = values[3]  # 更新时间列
                
                # 解析时间
                parsed_time = self.parse_datetime(update_time_str)
                current_time = datetime.now()
                time_diff = current_time - parsed_time
                
                # 如果在24小时内，设为绿色
                if time_diff <= timedelta(hours=24):
                    self.tree.item(item, tags=('recent',))
                else:
                    self.tree.item(item, tags=())
        
        # 配置样式
        self.tree.tag_configure('recent', foreground='green')
    
    def parse_datetime(self, date_str):
        """解析日期时间字符串，转换为datetime对象"""
        # 处理不同格式的时间字符串
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
        
        # 如果标准格式都失败，尝试处理相对时间描述（如"18小时前"）
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
        
        # 默认返回当前时间
        return datetime.now()
    
    def log_message(self, message):
        """向日志框添加消息"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def generate_random_headers(self):
        """生成随机请求头，每次请求都不同"""
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
        """将浏览量文本转换为数字，处理W+格式"""
        if not view_text:
            return "0"
        
        # 移除空白字符
        view_text = view_text.strip()
        
        # 检查是否包含W+
        if 'W+' in view_text.upper() or '万+' in view_text:
            # 提取数字部分
            number_match = re.search(r'([\d.]+)', view_text)
            if number_match:
                number = float(number_match.group(1))
                # 将数字乘以10000
                converted_number = int(number * 10000)
                return str(converted_number)
        
        # 如果不是W+格式，尝试提取纯数字
        number_match = re.search(r'(\d+)', view_text)
        if number_match:
            return number_match.group(1)
        
        # 如果没有找到数字，返回原始文本
        return view_text
    
    def extract_crack_method_from_tippy(self, tippy_content):
        """从data-tippy-content中提取破解方式"""
        if not tippy_content:
            return "未知破解方式"
        
        # 解析tippy_content中的HTML
        try:
            soup = BeautifulSoup(tippy_content, "html.parser")
            # 查找激活方式那一行
            activation_elements = soup.find_all(class_="attr-key")
            for element in activation_elements:
                if "激活方式" in element.get_text():
                    parent_div = element.parent
                    attr_value = parent_div.find(class_="attr-value")
                    if attr_value:
                        return attr_value.get_text(strip=True)
        except Exception as e:
            print(f"解析tippy_content失败: {e}")
        
        return "未知破解方式"
    
    def toggle_display_filter(self):
        """切换显示过滤器，根据是否只显示24小时内更新的数据"""
        if hasattr(self, 'all_software_data_cache'):  # 检查是否有缓存数据
            if self.show_recent_only_var.get():  # 如果勾选了仅显示24小时内更新
                self.apply_time_filter()
            else:  # 显示所有数据
                self.show_all_cached_data()
    
    def apply_time_filter(self):
        """应用时间过滤器，只显示24小时内的数据"""
        # 清空当前表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 只显示24小时内的数据
        for software in self.all_software_data_cache:
            update_time = software["更新时间"]
            parsed_time = self.parse_datetime(update_time)
            current_time = datetime.now()
            time_diff = current_time - parsed_time
            
            if time_diff <= timedelta(hours=24):
                values = (
                    software["软件名称"],
                    software["软件版本"],
                    software["简介"],
                    software["更新时间"],
                    software["评论数"],
                    software["浏览量"],
                    software["点赞量"],
                    software["破解方式"],
                    software["正文链接"]
                )
                item_id = self.tree.insert("", tk.END, values=values)
                
                # 设置颜色
                if time_diff <= timedelta(hours=24):
                    self.tree.item(item_id, tags=('recent',))
    
    def show_all_cached_data(self):
        """显示所有缓存的数据"""
        # 清空当前表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 显示所有缓存数据
        for software in self.all_software_data_cache:
            values = (
                software["软件名称"],
                software["软件版本"],
                software["简介"],
                software["更新时间"],
                software["评论数"],
                software["浏览量"],
                software["点赞量"],
                software["破解方式"],
                software["正文链接"]
            )
            item_id = self.tree.insert("", tk.END, values=values)
            
            # 检查是否在24小时内，设置颜色
            update_time = software["更新时间"]
            parsed_time = self.parse_datetime(update_time)
            current_time = datetime.now()
            time_diff = current_time - parsed_time
            
            if time_diff <= timedelta(hours=24):
                self.tree.item(item_id, tags=('recent',))
    
    def fetch_webpage(self, url):
        """发送请求获取网页内容"""
        try:
            # 随机延迟，避免频繁请求被封
            delay = random.uniform(10, 30)
            self.log_message(f"等待 {delay:.1f} 秒后请求页面...")
            time.sleep(delay)
            
            # 检查是否需要停止
            if self.stop_flag.is_set():
                return None
            
            # 每次请求都使用随机的请求头
            headers = self.generate_random_headers()
            
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            # 检查响应状态码
            response.raise_for_status()
            # 设置正确的编码（避免乱码）
            response.encoding = response.apparent_encoding
            return response.text
        except requests.exceptions.RequestException as e:
            self.log_message(f"请求网页失败：{e}")
            return None
    
    def parse_software_list(self, html_text):
        """解析网页HTML，提取软件列表信息"""
        software_list = []
        if not html_text:
            return software_list

        soup = BeautifulSoup(html_text, "html.parser")
        
        # 根据实际HTML结构选择正确的元素
        software_items = soup.select("posts.posts-item.ajax-item.card")

        for item in software_items:
            try:
                # 检查是否需要停止
                if self.stop_flag.is_set():
                    break
                
                # 检查是否是置顶内容（但不再作为停止条件）
                is_pinned = bool(item.select_one("badge.img-badge.left"))
                
                # 1. 软件名称和版本
                title_elem = item.select_one("h2.item-heading a")
                full_title = title_elem.get_text(strip=True) if title_elem else "未知名称"
                
                # 从标题中分离软件名称和版本号
                name = "未知名称"
                version = "未知版本"
                crack_method = "未知破解方式"
                if full_title:
                    # 尝试用正则表达式分离名称和版本
                    match = re.search(r'^(.+?)\s+(\d+\.\d+(?:\.\d+)?)', full_title)
                    if match:
                        name = match.group(1).strip()
                        version = match.group(2)
                    else:
                        name = full_title
                
                # 提取破解方式信息
                link_elem_with_attrs = item.select_one("h2.item-heading a[data-tippy-content]")
                if link_elem_with_attrs:
                    tippy_content = link_elem_with_attrs.get('data-tippy-content', '')
                    crack_method = self.extract_crack_method_from_tippy(tippy_content)
                
                # 2. 正文链接（拼接完整URL，避免相对路径）
                link_elem = item.select_one("h2.item-heading a")
                link = link_elem["href"] if link_elem else ""
                full_link = requests.compat.urljoin(self.BASE_URL, link) if link else ""

                # 3. 简介
                desc_elem = item.select_one("div.item-body div[style*='color: #888']")
                description = desc_elem.get_text(strip=True) if desc_elem else "无简介"

                # 4. 更新时间
                time_elem = item.select_one("item[title]")
                update_time = time_elem["title"] if time_elem else "未知时间"

                # 5. 评论数
                comment_elem = item.select_one("item.meta-comm a")
                comment_count = "0"
                if comment_elem:
                    # 提取评论数，例如从 "图标 0" 中提取数字
                    comment_text = comment_elem.get_text(strip=True)
                    numbers = re.findall(r'\d+', comment_text)
                    comment_count = numbers[0] if numbers else "0"

                # 6. 浏览量 - 处理W+格式
                view_elem = item.select_one("item.meta-view")
                if not view_elem:
                    view_elem = item.select_one(".meta-view, .views, .view-count")
                view_count = "0"
                if view_elem:
                    view_text = view_elem.get_text(strip=True)
                    # 转换浏览量格式（如 1.1W+ -> 11000）
                    view_count = self.convert_view_count(view_text)

                # 7. 点赞量
                like_elem = item.select_one("item.meta-like")
                like_count = "0"
                if like_elem:
                    like_text = like_elem.get_text(strip=True)
                    numbers = re.findall(r'\d+', like_text)
                    like_count = numbers[0] if numbers else "0"

                # 组装成字典
                software_info = {
                    "软件名称": name,
                    "软件版本": version,
                    "简介": description,
                    "更新时间": update_time,
                    "评论数": comment_count,
                    "浏览量": view_count,  # 现在是转换后的数字格式
                    "点赞量": like_count,
                    "破解方式": crack_method,
                    "正文链接": full_link
                }
                software_list.append(software_info)
                self.log_message(f"已提取：{name} v{version} (更新时间: {update_time}, 浏览量: {view_count}, 破解方式: {crack_method})")

            except Exception as e:
                self.log_message(f"解析单个软件项失败：{e}")
                continue

        return software_list

    def get_next_page_url(self, current_url, page_num):
        """构造下一页的URL"""
        if page_num == 1:
            # 第一页到第二页
            return f"{self.BASE_URL}page/2/"
        else:
            # 第二页及以后
            return f"{self.BASE_URL}page/{page_num + 1}/"

    def scrape_multiple_pages(self, total_pages=5):
        """抓取指定数量的页面内容"""
        all_software_data = []
        current_url = self.BASE_URL
        page_num = 1
        
        self.log_message(f"开始抓取，总共抓取 {total_pages} 页...")
        
        while page_num <= total_pages and not self.stop_flag.is_set():
            self.log_message(f"正在抓取第 {page_num} 页: {current_url}")
            
            # 更新进度条
            progress_value = (page_num - 1) / total_pages * 100
            self.progress['value'] = progress_value
            self.root.update_idletasks()
            
            # 检查是否需要停止
            if self.stop_flag.is_set():
                self.log_message("用户请求停止抓取")
                break
            
            # 获取当前页面内容
            html = self.fetch_webpage(current_url)
            if not html:
                self.log_message(f"无法获取第 {page_num} 页内容，跳过")
                break
            
            # 解析当前页面数据
            page_data = self.parse_software_list(html)
            
            # 缓存数据
            all_software_data.extend(page_data)
            
            # 添加当前页面数据到表格
            for software in page_data:
                values = (
                    software["软件名称"],
                    software["软件版本"],
                    software["简介"],
                    software["更新时间"],
                    software["评论数"],
                    software["浏览量"],
                    software["点赞量"],
                    software["破解方式"],
                    software["正文链接"]
                )
                # 如果启用了仅显示24小时内更新的选项，则只显示符合条件的数据
                if self.show_recent_only_var.get():
                    update_time = software["更新时间"]
                    parsed_time = self.parse_datetime(update_time)
                    current_time = datetime.now()
                    time_diff = current_time - parsed_time
                    
                    if time_diff <= timedelta(hours=24):
                        item_id = self.tree.insert("", tk.END, values=values)
                        
                        # 检查是否在24小时内，设置颜色
                        if time_diff <= timedelta(hours=24):
                            self.tree.item(item_id, tags=('recent',))
                else:
                    # 不过滤，直接添加
                    item_id = self.tree.insert("", tk.END, values=values)
                    
                    # 检查是否在24小时内，设置颜色
                    update_time = software["更新时间"]
                    parsed_time = self.parse_datetime(update_time)
                    current_time = datetime.now()
                    time_diff = current_time - parsed_time
                    
                    if time_diff <= timedelta(hours=24):
                        self.tree.item(item_id, tags=('recent',))
            
            # 将当前页面数据添加到全局缓存
            self.all_software_data_cache.extend(page_data)
            
            # 如果已经是最后一页，结束循环
            if page_num >= total_pages:
                self.log_message(f"已达到设定的 {total_pages} 页，停止抓取")
                break
            
            # 检查是否需要停止
            if self.stop_flag.is_set():
                self.log_message("用户请求停止抓取")
                break
            
            # 在抓取下一页之前暂停指定时间
            delay_seconds = int(self.delay_var.get())
            self.log_message(f"第 {page_num} 页抓取完成，暂停 {delay_seconds} 秒后继续...")
            
            # 在暂停期间检查停止标志
            for _ in range(delay_seconds):
                if self.stop_flag.is_set():
                    self.log_message("用户请求停止抓取")
                    return all_software_data
                time.sleep(1)
            
            # 构造下一页URL
            next_url = self.get_next_page_url(current_url, page_num)
            
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
            else:
                self.log_message("没有找到下一页，结束抓取")
                break
        
        # 完成进度
        self.progress['value'] = 100
        return all_software_data

    def start_scraping(self):
        """开始抓取的线程函数"""
        # 重置停止标志
        self.stop_flag.clear()
        
        # 禁用开始按钮，启用结束按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 清空进度条
        self.progress['value'] = 0
        
        # 获取设置值
        try:
            total_pages = int(self.pages_var.get())
            if total_pages <= 0:
                raise ValueError("页数必须大于0")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的抓取页数")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            return
        
        # 在新线程中执行抓取任务
        def scraping_task():
            try:
                # 抓取数据
                software_data = self.scrape_multiple_pages(total_pages=total_pages)
                
                if not software_data:
                    self.log_message("未提取到任何软件信息")
                else:
                    # 更新全局缓存
                    self.all_software_data_cache = software_data
                    
                    self.log_message(f"抓取完成！共提取 {len(software_data)} 个软件信息")
                    # 抓取完成后自动按时间排序
                    self.auto_sort_by_time()
                    
                    # 根据复选框状态应用过滤
                    if self.show_recent_only_var.get():
                        self.apply_time_filter()
                
            except Exception as e:
                self.log_message(f"抓取过程中发生错误：{e}")
            finally:
                # 重新启用开始按钮，禁用结束按钮
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.progress['value'] = 0
        
        # 启动抓取线程
        thread = threading.Thread(target=scraping_task)
        thread.daemon = True
        thread.start()

    def stop_scraping(self):
        """停止抓取"""
        self.stop_flag.set()
        self.log_message("正在停止抓取...")
        self.stop_btn.config(state=tk.DISABLED)
def get_app_version():
    """获取应用程序版本"""
    try:
        with open('version.json', 'r') as f:
            config = json.load(f)
            return config.get('version', 'Unknown')
    except FileNotFoundError:
        # 尝试从资源路径加载（打包后的位置）
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
    
    # 在程序关闭时保存配置
    def on_closing():
        app.save_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    # 为了解决SSL验证问题，禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()