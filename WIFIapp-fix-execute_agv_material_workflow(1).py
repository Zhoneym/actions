import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import socket
import threading
import time
import re
import json
import os
from datetime import datetime
from agv_comunicate import ModbusMaster

class DeviceController:
    def __init__(self, root):
        self.root = root
        self.root.title("欢迎使用实验室无人称重平台")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # 字体配置
        self.font_small = ("微软雅黑", 12)    # 原来10 -> 12
        self.font_normal = ("微软雅黑", 14)   # 原来12 -> 14  
        self.font_large = ("微软雅黑", 16)    # 原来14 -> 16
        self.font_xlarge = ("微软雅黑", 18)   # 原来16 -> 18
        self.font_bold = ("微软雅黑", 14, "bold")  # 原来12,bold -> 14,bold
        self.font_large_bold = ("微软雅黑", 18, "bold")  # 原来16,bold -> 18,bold
        
        # 配置ttk样式
        self.style = ttk.Style()
        self.style.configure('TLabel', font=self.font_normal)
        self.style.configure('TButton', font=self.font_normal)
        self.style.configure('TEntry', font=self.font_normal)
        self.style.configure('TCombobox', font=self.font_normal)
        self.style.configure('TRadiobutton', font=self.font_normal)
        self.style.configure('TCheckbutton', font=self.font_normal)
        self.style.configure('TFrame', font=self.font_normal)
        self.style.configure('TLabelframe', font=self.font_normal)
        self.style.configure('TLabelframe.Label', font=self.font_bold)
        self.style.configure('TNotebook', font=self.font_normal)
        self.style.configure('TNotebook.Tab', font=self.font_normal)

        # 网络连接状态
        self.socket = None
        self.connected = False
        self.client_socket = None
        self.receive_thread = None
       
        # 设备连接状态跟踪
        self.connected_devices = set()  # 已连接的设备IP集合
        self.device_connection_times = {}  # 设备连接时间记录

        # 配置数据
        self.config_data = {
            'default_ip': '127.0.0.1',
            'default_port': '8888',
            'timeout': '10',
            'auto_reconnect': True
        }

        # 加载配置文件
        self.load_config()

        # 加载配方数据
        self.load_recipe_data()

        # 初始化物料控件字典
        self.material_widgets = {}
        # 初始化工艺阶段数据字典
        self.process_stages_data = {}

        # 创建菜单
        self.create_menu()

        # 创建UI
        self.create_widgets()

        # 确保线程正确退出
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    def get_local_ip(self):
        """获取本地IP地址"""
        try:
            # 创建一个临时socket连接来获取本地IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # 连接到公共DNS服务器
            local_ip = s.getsockname()[0]
            s.close()
            # 记录获取到的IP地址
            print(f"获取到本地IP地址: {local_ip}")
            return local_ip
        except Exception as e:
            print(f"获取本地IP失败: {str(e)}")
            return "127.0.0.1"  # 失败时返回默认值
    
    def execute_agv_material_workflow(self):
        """执行完整的 AGV 物料转运流程（基于 Modbus 协议）"""
        try:
            # 初始化 AGV 连接（使用配置或默认 IP）
            agv_ip = getattr(self, 'agv_ip', '192.168.192.236')  # 可从配置读取
            agv = ModbusMaster(host=agv_ip, port=502, slave_id=1)
            
            if not agv.connect():
                messagebox.showerror("连接失败", "无法连接到 AGV 控制器")
                return

            def move_to_station(station_id):
                """控制 AGV 移动到指定站点"""
                print(f"🚚 AGV 移动到站点 {station_id}")
                success = agv.write_register(address=0, value=station_id)  # 寄存器 00001
                if success:
                    time.sleep(3)  # 等待移动完成

            def lift_up():
                """顶升机构上升（抓取容器）"""
                print("↑ 顶升机构上升（抓取容器）")
                agv.write_register(address=49, value=1)  # 00050
                time.sleep(2)

            def lift_down():
                """顶升机构下降（放置容器）"""
                print("↓ 顶升机构下降（放置容器）")
                agv.write_register(address=50, value=1)  # 00051
                time.sleep(2)

            def dosing(material_name, target_weight):
                """模拟供料过程"""
                print(f"🧪 开始加入 [{material_name}]，目标: {target_weight}g")
                time.sleep(4)  # 模拟供料时间

            def lift_control(address,value):
                #验证机械臂初始状态，0表示就绪状态
                registers = agv.read_holding_registers(address=address, count=1)
                if registers:
                    print("操作前读取到的寄存器值:", registers)
                if registers[0] != 0:
                    print("机械臂未就绪，操作终止");  
                    return   
                #控制机械臂    
                agv.write_register(address=address, value=value)  
                #等待执行结束
                while True:
                    time.sleep(5)
                    registers = agv.read_holding_registers(address=address, count=1)
                    if registers:
                        print("操作后读取到的寄存器值:", registers)
                    if registers[0] == 0:  
                        break   
                return
            
            # ========================
            # 🚀 执行容器1流程
            # ========================
            print('点2取杯')
            lift_control(49100,3)
            print('点1放杯')
            lift_control(49100,2)
            print('点1取杯')
            lift_control(49100,1)
            print('点2放杯')
            lift_control(49100,4)

            """
            move_to_station(1)
            lift_up()                     # 抓取容器1
            move_to_station(2)
            lift_down()                   # 放置容器1
            dosing("材料1（液体）", 100.0)
            lift_up()                     # 抓取容器1
            move_to_station(3)
            lift_down()                   # 放置容器1
            dosing("材料2（粘稠）", 50.0)
            lift_up()                     # 抓取容器1
            move_to_station(4)
            lift_down()                   # 最终放置容器1

            # ========================
            # 🚀 执行容器2流程
            # ========================
            move_to_station(5)
            lift_up()                     # 抓取容器2
            move_to_station(6)
            lift_down()                   # 放置容器2
            dosing("材料3（固体）", 200.0)
            lift_up()                     # 抓取容器2
            move_to_station(7)
            lift_down()                   # 最终放置容器2

            # ========================
            # 🔄 复位
            # ========================
            print("🔄 AGV 与顶升机构复位中...")
            move_to_station(0)            # 假设 0 为 home 站点
            lift_down()                   # 确保顶升处于下降状态
            """    

            messagebox.showinfo("完成", "✅ 全部物料投放流程执行完毕！")

        except Exception as e:
            error_msg = f"流程执行异常: {str(e)}"
            print(error_msg)
            messagebox.showerror("流程错误", error_msg)
        finally:
            try:
                agv.close()
            except:
                pass

    def start_agv_workflow_threaded(self):
        """在线程中启动 AGV 工艺流程，防止界面冻结"""
        def run():
            self.execute_agv_material_workflow()
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "current.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 更新配置数据，保持默认值
                    self.config_data.update(loaded_config)
                
                # 初始化设备列表
                self.device_list = []
                if 'devices' in loaded_config and isinstance(loaded_config['devices'], list):
                    self.device_list = loaded_config['devices']
                    self.log(f"从配置文件加载了 {len(self.device_list)} 个设备配置")
                else:
                    self.log("配置文件中没有找到有效的设备列表，使用空列表")
                    
                self.log("配置文件加载成功")
            except Exception as e:
                self.log(f"配置文件加载失败: {str(e)}")
                # 初始化空的设备列表
                self.device_list = []
        else:
            self.log("未找到配置文件，使用默认设置")
            # 初始化空的设备列表
            self.device_list = []
    def save_config(self, config_data=None):
        """保存配置文件"""
        try:
            if config_data:
                self.config_data.update(config_data)
            
            # 确保设备列表被保存到配置中
            if hasattr(self, 'device_list'):
                self.config_data['devices'] = self.device_list
                self.config_data['device_count'] = len(self.device_list)
                self.config_data['last_modified'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open("current.json", 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            
            self.log("配置文件保存成功")
            return True
        except Exception as e:
            self.log(f"配置文件保存失败: {str(e)}")
            return False
    def load_recipe_data(self):
        """加载配方数据，初始化全局数据结构"""
        # 初始化全局配方数据结构
        self.recipe_data = {}
        
        # 确保recipe_data目录存在
        recipe_dir = os.path.join(os.path.dirname(__file__), "recipe_data")
        if not os.path.exists(recipe_dir):
            os.makedirs(recipe_dir)
            self.log(f"创建配方数据目录: {recipe_dir}")
        
        # 主配方文件路径
        recipe_file = os.path.join(recipe_dir, "recipes.json")
        
        if os.path.exists(recipe_file):
            try:
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # 根据JSON格式加载配方数据
                if isinstance(loaded_data, dict) and 'recipes' in loaded_data and isinstance(loaded_data['recipes'], list):
                    # 处理包含recipes数组的结构
                    for recipe in loaded_data['recipes']:
                        if isinstance(recipe, dict) and 'name' in recipe:
                            recipe_name = recipe['name']
                            # 标准化配方数据结构
                            self.recipe_data[recipe_name] = {
                                'name': recipe.get('name', ''),
                                'description': recipe.get('description', ''),
                                'created_time': recipe.get('created_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                'modified_time': recipe.get('modified_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                'materials': recipe.get('materials', []),
                                'process_config': recipe.get('process_config', {})
                            }
                    
                    self.log(f"配方数据{recipe_file}加载成功，共 {len(self.recipe_data)} 个配方")
                    print(self.recipe_data)
                    # 统计工艺配置信息
                    total_process_configs = 0
                    for recipe_name, recipe_info in self.recipe_data.items():
                        process_config = recipe_info.get('process_config', {})
                        if process_config:
                            total_process_configs += len(process_config)
                            self.log(f"配方 '{recipe_name}' 包含 {len(process_config)} 个物料工艺配置")
                    
                    if total_process_configs > 0:
                        self.log(f"总共加载了 {total_process_configs} 个工艺配置")
                
                else:
                    self.log("配方数据格式错误，初始化空数据结构")
                    self.recipe_data = {}
                    
            except Exception as e:
                self.log(f"配方数据加载失败: {str(e)}")
                self.recipe_data = {}
        else:
            self.log("未找到配方数据文件，初始化空配方数据结构")
            # 创建空的配方数据文件
            self.save_recipe_data()

        
        self.log("配方数据结构初始化完成")
    def save_recipe_data(self, recipe_name=None, original_filepath=None):
        """保存配方数据到文件
        
        Args:
            recipe_name: 特定配方名称，如果提供则只保存该配方到原始文件
            original_filepath: 原始配方文件路径，如果提供则保存到该文件
        """
        try:
            if not hasattr(self, 'recipe_data'):
                self.log("没有配方数据需要保存")
                return False
            
            # 如果指定了配方名称和原始文件路径，则保存到原始文件
            if recipe_name and original_filepath and os.path.exists(original_filepath):
                # 读取原始文件内容
                with open(original_filepath, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                # 更新配方数据 - 处理recipes数组结构
                if 'recipes' in original_data and isinstance(original_data['recipes'], list):
                    recipe_found = False
                    for i, recipe in enumerate(original_data['recipes']):
                        if recipe.get('name') == recipe_name:
                            # 更新配方数据
                            if recipe_name in self.recipe_data:
                                original_data['recipes'][i] = self.recipe_data[recipe_name]
                            recipe_found = True
                            break
                    
                    # 如果没找到配方，添加新配方
                    if not recipe_found and recipe_name in self.recipe_data:
                        original_data['recipes'].append(self.recipe_data[recipe_name])
                        # 更新导出信息
                        if 'total_recipes' in original_data:
                            original_data['total_recipes'] = len(original_data['recipes'])
                        if 'export_time' in original_data:
                            original_data['export_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 保存回原始文件
                with open(original_filepath, 'w', encoding='utf-8') as f:
                    json.dump(original_data, f, ensure_ascii=False, indent=4)
                
                self.log(f"配方 '{recipe_name}' 已保存到原始文件: {original_filepath}")
                return True
            
            # 默认保存到应用程序的配方数据文件
            recipe_dir = "recipe_data"
            if not os.path.exists(recipe_dir):
                os.makedirs(recipe_dir)
            
            filepath = os.path.join(recipe_dir, "recipes.json")
            
            # 转换为标准的recipes数组格式
            recipes_array = list(self.recipe_data.values())
            save_data = {"recipes": recipes_array}
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"配方数据已保存到: {filepath}")
            return True
            
        except Exception as e:
            self.log(f"保存配方数据失败: {str(e)}")
            return False
    def get_available_process_types(self):
        """获取可用的工艺类型"""
        return ['固态供料', '液态供料', '胶体供料', '称重', '机器人控制']
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="登录", command=self.login)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_close)

        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="设备IP与端口设置", command=self.show_ip_port_settings)
        settings_menu.add_command(label="配方管理", command=self.show_recipe_management)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    def login(self):
        """登录功能"""
        # 创建登录对话框
        login_window = tk.Toplevel(self.root)
        login_window.title("用户登录")
        login_window.geometry("300x200")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()

        # 居中显示
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() - login_window.winfo_width()) // 2
        y = (login_window.winfo_screenheight() - login_window.winfo_height()) // 2
        login_window.geometry(f"+{x}+{y}")

        # 登录表单
        frame = ttk.Frame(login_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        username_entry = ttk.Entry(frame, width=20)
        username_entry.grid(row=0, column=1, padx=5, pady=10)

        ttk.Label(frame, text="密码:").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        password_entry = ttk.Entry(frame, width=20, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=10)

        def do_login():
            username = username_entry.get()
            password = password_entry.get()
            
            if not username or not password:
                messagebox.showwarning("输入错误", "请输入用户名和密码")
                return
            
            # 简单的登录验证（实际应用中应该连接数据库或认证服务）
            if username == "admin" and password == "admin":
                messagebox.showinfo("登录成功", f"欢迎 {username}！")
                self.log(f"用户 {username} 登录成功")
                login_window.destroy()
            else:
                messagebox.showerror("登录失败", "用户名或密码错误")

        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="登录", command=do_login).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=login_window.destroy).pack(side=tk.LEFT, padx=10)

        # 设置焦点
        username_entry.focus_set()
    def show_connection_settings(self):
        """显示连接设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("连接设置")
        settings_window.geometry("450x350")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()

        # 居中显示
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() - settings_window.winfo_width()) // 2
        y = (settings_window.winfo_screenheight() - settings_window.winfo_height()) // 2
        settings_window.geometry(f"+{x}+{y}")

        # 设置内容
        frame = ttk.Frame(settings_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 默认连接设置
        ttk.Label(frame, text="默认IP地址:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        default_ip_entry = ttk.Entry(frame, width=15)
        default_ip_entry.grid(row=0, column=1, padx=5, pady=10)
        # 总是显示当前设备的实际IP地址
        current_ip = self.get_local_ip()
        default_ip_entry.insert(0, current_ip)

        ttk.Label(frame, text="默认端口:").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        default_port_entry = ttk.Entry(frame, width=10)
        default_port_entry.grid(row=1, column=1, padx=5, pady=10)
        default_port_entry.insert(0, self.config_data['default_port'])

        # 连接超时设置
        ttk.Label(frame, text="连接超时(秒):").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        timeout_entry = ttk.Entry(frame, width=10)
        timeout_entry.grid(row=2, column=1, padx=5, pady=10)
        timeout_entry.insert(0, self.config_data['timeout'])

        # 自动重连
        auto_reconnect_var = tk.BooleanVar(value=self.config_data['auto_reconnect'])
        auto_reconnect_check = ttk.Checkbutton(frame, text="自动重连", variable=auto_reconnect_var)
        auto_reconnect_check.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W)

        

       
        def save_settings():
            """保存设置到current.json"""
            config_data = {
                'default_ip': default_ip_entry.get(),
                'default_port': default_port_entry.get(),
                'timeout': timeout_entry.get(),
                'auto_reconnect': auto_reconnect_var.get()
            }
            
            if self.save_config(config_data):
                messagebox.showinfo("保存成功", "设置已保存到 current.json")
                settings_window.destroy()
            else:
                messagebox.showerror("保存失败", "设置保存失败")

        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        # 导入导出按钮
        io_frame = ttk.Frame(btn_frame)
        io_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(io_frame, text="导入", command=import_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(io_frame, text="导出", command=export_settings).pack(side=tk.LEFT, padx=5)

        # 保存取消按钮
        save_frame = ttk.Frame(btn_frame)
        save_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Button(save_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="取消", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    def show_device_config(self):
        """显示设备配置对话框"""
        config_window = tk.Toplevel(self.root)
        config_window.title("设备配置")
        config_window.geometry("500x400")
        config_window.resizable(False, False)
        config_window.transient(self.root)
        config_window.grab_set()

        # 居中显示
        config_window.update_idletasks()
        x = (config_window.winfo_screenwidth() - config_window.winfo_width()) // 2
        y = (config_window.winfo_screenheight() - config_window.winfo_height()) // 2
        config_window.geometry(f"+{x}+{y}")

        # 创建选项卡
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 步进电机配置
        step_frame = ttk.Frame(notebook, padding="10")
        notebook.add(step_frame, text="步进电机")

        # 蠕动泵配置
        pump_frame = ttk.Frame(notebook, padding="10")
        notebook.add(pump_frame, text="蠕动泵")

        # 运动设备配置
        move_frame = ttk.Frame(notebook, padding="10")
        notebook.add(move_frame, text="运动设备")

        def save_config():
            messagebox.showinfo("配置", "设备配置已保存")
            config_window.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(config_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="保存", command=save_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=config_window.destroy).pack(side=tk.LEFT, padx=10)
    def show_ip_port_settings(self):
        """显示设备IP与端口设置对话框"""
        ip_port_window = tk.Toplevel(self.root)
        ip_port_window.title("设备IP与端口设置")
        ip_port_window.geometry("600x500")
        ip_port_window.resizable(True, True)
        ip_port_window.transient(self.root)
        ip_port_window.grab_set()

        # 居中显示
        ip_port_window.update_idletasks()
        x = (ip_port_window.winfo_screenwidth() - ip_port_window.winfo_width()) // 2
        y = (ip_port_window.winfo_screenheight() - ip_port_window.winfo_height()) // 2
        ip_port_window.geometry(f"+{x}+{y}")

        # 初始化当前选中索引
        self.current_selected_index = None
        
        # 设备列表已在load_config()中初始化，直接使用
        if not hasattr(self, 'device_list'):
            self.device_list = []
            self.log("设备列表未初始化，创建空列表")
        else:
            self.log(f"使用已加载的设备列表，共 {len(self.device_list)} 个设备")

        # 主框架
        main_frame = ttk.Frame(ip_port_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 设备输入区域
        input_frame = ttk.LabelFrame(main_frame, text="设备配置", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # 设备类型选择
        ttk.Label(input_frame, text="设备类型:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        device_type_var = tk.StringVar()
        device_type_combo = ttk.Combobox(input_frame, textvariable=device_type_var, width=20, state="readonly")
        device_type_combo['values'] = ('固态供料工作站', '供水工作站', '添加剂加注工作站')
        device_type_combo.grid(row=0, column=1, padx=5, pady=5)
        device_type_combo.current(0)

        # IP地址输入
        ttk.Label(input_frame, text="当前IP地址:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ip_entry = ttk.Entry(input_frame, width=15)
        ip_entry.grid(row=0, column=3, padx=5, pady=5)
        # 初始化IP地址：如果有选中的设备则使用设备IP，否则使用默认值
        if hasattr(self, 'device_list') and self.device_list and self.current_selected_index is not None:
            ip_entry.insert(0, self.device_list[self.current_selected_index]['ip'])
        else:
            ip_entry.insert(0, "192.168.1.100")

        # 端口输入
        ttk.Label(input_frame, text="端口:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        port_entry = ttk.Entry(input_frame, width=10)
        port_entry.grid(row=0, column=5, padx=5, pady=5)
        # 初始化端口：如果有选中的设备则使用设备端口，否则使用默认值
        if hasattr(self, 'device_list') and self.device_list and self.current_selected_index is not None:
            port_entry.insert(0, self.device_list[self.current_selected_index]['port'])
        else:
            port_entry.insert(0, "8888")

        # 生效设备列表区域
        list_frame = ttk.LabelFrame(main_frame, text="生效设备列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 设备列表
        device_listbox = tk.Listbox(list_frame, height=8)
        device_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def add_device():
            """添加设备到列表"""
            device_type = device_type_var.get()
            ip = ip_entry.get()
            port = port_entry.get()

            if not device_type or not ip or not port:
                messagebox.showwarning("输入错误", "请填写完整的设备信息")
                return

            # 验证IP地址格式
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                messagebox.showwarning("输入错误", "请输入有效的IP地址")
                return

            # 验证端口格式
            if not re.match(r'^\d+$', port) or not (0 < int(port) <= 65535):
                messagebox.showwarning("输入错误", "请输入有效的端口号(1-65535)")
                return

            device_info = {
                'type': device_type,
                'ip': ip,
                'port': port
            }

            self.device_list.append(device_info)
            update_device_list()
            clear_inputs()

        def delete_device():
            """删除选中的设备"""
            selected_index = device_listbox.curselection()
            if not selected_index:
                messagebox.showwarning("选择错误", "请先选择一个设备")
                return

            index = selected_index[0]
            if 0 <= index < len(self.device_list):
                self.device_list.pop(index)
                update_device_list()
                clear_inputs()
                self.current_selected_index = None

        def update_device():
            """更新选中的设备信息"""
            if self.current_selected_index is None:
                messagebox.showwarning("选择错误", "请先选择一个设备进行更新")
                return

            device_type = device_type_var.get()
            ip = ip_entry.get()
            port = port_entry.get()

            if not device_type or not ip or not port:
                messagebox.showwarning("输入错误", "请填写完整的设备信息")
                return

            # 验证IP地址格式
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                messagebox.showwarning("输入错误", "请输入有效的IP地址")
                return

            # 验证端口格式
            if not re.match(r'^\d+$', port) or not (0 < int(port) <= 65535):
                messagebox.showwarning("输入错误", "请输入有效的端口号(1-65535)")
                return

            device_info = {
                'type': device_type,
                'ip': ip,
                'port': port
            }

            self.device_list[self.current_selected_index] = device_info
            update_device_list()
            clear_inputs()
            self.current_selected_index = None

        def on_device_select(event):
            """设备列表选择事件"""
            selected_index = device_listbox.curselection()
            if not selected_index:
                return

            index = selected_index[0]
            if 0 <= index < len(self.device_list):
                device_info = self.device_list[index]
                device_type_var.set(device_info['type'])
                ip_entry.delete(0, tk.END)
                ip_entry.insert(0, device_info['ip'])
                port_entry.delete(0, tk.END)
                port_entry.insert(0, device_info['port'])
                self.current_selected_index = index
                
                # 设置焦点到设备列表，保持选中状态
                device_listbox.focus_set()
                device_listbox.selection_set(index)

        def clear_inputs():
            """清空输入框"""
            device_type_combo.current(0)
            ip_entry.delete(0, tk.END)
            ip_entry.insert(0, "192.168.1.100")
            port_entry.delete(0, tk.END)
            port_entry.insert(0, "8888")

        def update_device_list():
            """更新设备列表显示"""
            device_listbox.delete(0, tk.END)
            for i, device in enumerate(self.device_list):
                display_text = f"{i+1}. {device['type']} - {device['ip']}:{device['port']}"
                device_listbox.insert(tk.END, display_text)

        def import_devices():
            """从JSON文件导入设备配置"""
            filename = filedialog.askopenfilename(
                title="选择设备配置文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if not filename:
                return
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                # 检查导入的数据结构
                if 'devices' in import_data:
                    self.device_list = import_data['devices']
                    update_device_list()
                    messagebox.showinfo("导入成功", f"成功导入 {len(self.device_list)} 个设备配置")
                    self.log(f"设备配置导入成功: {filename}, 共 {len(self.device_list)} 个设备")
                else:
                    messagebox.showwarning("导入失败", "配置文件格式不正确，缺少设备列表")
                    
            except Exception as e:
                messagebox.showerror("导入失败", f"导入失败: {str(e)}")
                self.log(f"设备配置导入失败: {str(e)}")


        def export_devices():
            """导出设备配置到时间戳命名的JSON文件"""
            if not self.device_list:
                messagebox.showwarning("导出失败", "没有设备配置可导出")
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"device_settings_{timestamp}.json"
            
            export_data = {
                'devices': self.device_list,
                'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_devices': len(self.device_list)
            }
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("导出成功", f"设备配置已导出到 {filename}")
                self.log(f"设备配置导出成功: {filename}, 共 {len(self.device_list)} 个设备")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出失败: {str(e)}")
                self.log(f"设备配置导出失败: {str(e)}")

        def save_settings():
            """保存设备配置到current.json"""
            if not self.device_list:
                messagebox.showwarning("保存错误", "请至少添加一个设备配置")
                return
            
            # 更新配置数据中的设备列表
            config_data = {
                'devices': self.device_list,
                'device_count': len(self.device_list),
                'last_modified': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if self.save_config(config_data):
                messagebox.showinfo("保存成功", f"设备配置已保存到 current.json，共 {len(self.device_list)} 个设备")
                ip_port_window.destroy()
            else:
                messagebox.showerror("保存失败", "设备配置保存失败")

        # 绑定选择事件
        device_listbox.bind('<<ListboxSelect>>', on_device_select)
        
        # 绑定输入框焦点事件，保持设备列表选中状态
        def on_input_focus(event):
            if self.current_selected_index is not None:
                device_listbox.selection_set(self.current_selected_index)
        
        # 绑定下拉列表选择事件，保持设备列表选中状态
        def on_combobox_select(event):
            if self.current_selected_index is not None:
                device_listbox.selection_set(self.current_selected_index)
            # 返回None让事件继续正常处理
            return None
        
        ip_entry.bind('<FocusIn>', on_input_focus)
        port_entry.bind('<FocusIn>', on_input_focus)
        device_type_combo.bind('<FocusIn>', on_input_focus)
        device_type_combo.bind('<<ComboboxSelected>>', on_combobox_select)

        # 控制按钮
        ctrl_btn_frame = ttk.Frame(btn_frame)
        ctrl_btn_frame.pack(side=tk.LEFT, padx=10)

        ttk.Button(ctrl_btn_frame, text="添加", command=add_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_btn_frame, text="删除", command=delete_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_btn_frame, text="更新", command=update_device).pack(side=tk.LEFT, padx=5)

        # 导入导出按钮
        io_btn_frame = ttk.Frame(btn_frame)
        io_btn_frame.pack(side=tk.LEFT, padx=10)

        ttk.Button(io_btn_frame, text="导入", command=import_devices).pack(side=tk.LEFT, padx=5)
        ttk.Button(io_btn_frame, text="导出", command=export_devices).pack(side=tk.LEFT, padx=5)

        # 保存取消按钮
        save_btn_frame = ttk.Frame(btn_frame)
        save_btn_frame.pack(side=tk.RIGHT, padx=10)

        ttk.Button(save_btn_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_btn_frame, text="取消", command=ip_port_window.destroy).pack(side=tk.LEFT, padx=5)

        # 初始化完成后更新设备列表显示
        update_device_list()
    
    def show_recipe_management(self):
        """显示配方管理对话框"""
        recipe_window = tk.Toplevel(self.root)
        recipe_window.title("配方管理")
        recipe_window.geometry("900x700")
        recipe_window.resizable(True, True)
        recipe_window.transient(self.root)
        recipe_window.grab_set()

        # 居中显示
        recipe_window.update_idletasks()
        x = (recipe_window.winfo_screenwidth() - recipe_window.winfo_width()) // 2
        y = (recipe_window.winfo_screenheight() - recipe_window.winfo_height()) // 2
        recipe_window.geometry(f"+{x}+{y}")

        # 创建主框架
        main_frame = ttk.Frame(recipe_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 使用PanedWindow实现可调整大小的分割
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧：配方管理区域
        left_frame = ttk.Frame(paned_window, padding="10")
        paned_window.add(left_frame, weight=1)

        # 右侧：配方详情区域
        right_frame = ttk.Frame(paned_window, padding="10")
        paned_window.add(right_frame, weight=1)

        # 配方管理区域
        recipe_frame = ttk.LabelFrame(left_frame, text="配方列表", padding="10")
        recipe_frame.pack(fill=tk.BOTH, expand=True)

        # 配方列表容器
        list_container = ttk.Frame(recipe_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # 配方列表
        recipe_listbox = tk.Listbox(list_container, height=12, font=self.font_normal)
        recipe_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=recipe_listbox.yview)
        recipe_listbox.configure(yscrollcommand=recipe_scrollbar.set)

        recipe_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        recipe_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 存储配方数据
        if not hasattr(self, 'recipe_data'):
            self.recipe_data = {}

        # 保存配方列表控件的引用
        self.recipe_listbox = recipe_listbox

        def update_recipe_list():
            """更新配方列表显示"""
            recipe_listbox.delete(0, tk.END)
            if hasattr(self, 'recipe_data') and self.recipe_data:
                for recipe_key, recipe_data in self.recipe_data.items():
                    # 显示格式：配方名-时间戳
                    display_name = f"{recipe_data.get('name', recipe_key)}-{recipe_data.get('create_date', '未知时间')}"
                    recipe_listbox.insert(tk.END, display_name)
            else:
                recipe_listbox.insert(tk.END, "暂无配方，请点击添加配方")
     
        # 初始化配方列表
        update_recipe_list()

        # 配方按钮区域
        recipe_btn_frame = ttk.Frame(recipe_frame)
        recipe_btn_frame.pack(fill=tk.X, pady=(10, 0))

        # 第一行按钮
        btn_row1 = ttk.Frame(recipe_btn_frame)
        btn_row1.pack(fill=tk.X, pady=2)

        ttk.Button(btn_row1, text="添加配方", command=self.add_recipe_device, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="编辑配方", command=lambda: self.edit_selected_recipe(recipe_listbox, update_recipe_list), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="删除配方", command=lambda: self.delete_selected_recipe(recipe_listbox, update_recipe_list), width=12).pack(side=tk.LEFT, padx=2)

        # 第二行按钮
        btn_row2 = ttk.Frame(recipe_btn_frame)
        btn_row2.pack(fill=tk.X, pady=2)

        ttk.Button(btn_row2, text="导入配方", command=self.import_recipe, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row2, text="导出配方", command=self.export_recipe, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row2, text="刷新列表", command=update_recipe_list, width=12).pack(side=tk.LEFT, padx=2)

        # 配方详情区域
        detail_frame = ttk.LabelFrame(right_frame, text="配方详情", padding="10")
        detail_frame.pack(fill=tk.BOTH, expand=True)

        # 详情内容容器
        detail_container = ttk.Frame(detail_frame)
        detail_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # 详情显示区域
        detail_text = scrolledtext.ScrolledText(detail_container, height=10, width=40, font=self.font_small, wrap=tk.WORD)
        detail_text.pack(fill=tk.BOTH, expand=True)
        detail_text.config(state=tk.DISABLED)

        # 工艺配置按钮
        process_btn_frame = ttk.Frame(detail_frame)
        process_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(process_btn_frame, text="配置工艺", command=lambda: self.configure_process(recipe_listbox), width=12).pack(side=tk.LEFT, padx=2)

        def show_recipe_details():
            """显示选中配方的详细信息"""
            selected_index = recipe_listbox.curselection()
            if not selected_index:
                detail_text.config(state=tk.NORMAL)
                detail_text.delete(1.0, tk.END)
                detail_text.insert(tk.END, "请从左侧选择一个配方查看详情")
                detail_text.config(state=tk.DISABLED)
                return
            
            if not hasattr(self, 'recipe_data'):
                detail_text.config(state=tk.NORMAL)
                detail_text.delete(1.0, tk.END)
                detail_text.insert(tk.END, "请先添加或导入配方")
                detail_text.config(state=tk.DISABLED)
                return

            recipe_display_name = recipe_listbox.get(selected_index[0])
            recipe_name = recipe_display_name.split('-')[0]  # 提取配方名称

            detail_text.config(state=tk.NORMAL)
            detail_text.delete(1.0, tk.END)

            if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
                recipe_data = self.recipe_data[recipe_name]
                
                detail_text.insert(tk.END, f"配方名称: {recipe_data.get('name', recipe_name)}\n")
                detail_text.insert(tk.END, f"创建时间: {recipe_data.get('create_date', '未知')}\n")
                detail_text.insert(tk.END, f"描述: {recipe_data.get('description', '无描述')}\n\n")

                # 显示物料信息
                if 'materials' in recipe_data and recipe_data['materials']:
                    detail_text.insert(tk.END, "物料配置:\n")
                    for i, material in enumerate(recipe_data['materials'], 1):
                        detail_text.insert(tk.END, f"  {i}. {material.get('type', '未知物料')}: {material.get('weight', '0')}g\n")
                else:
                    detail_text.insert(tk.END, "物料配置: 无物料信息\n")
            else:
                detail_text.insert(tk.END, "未找到配方详细信息")
            
            detail_text.config(state=tk.DISABLED)

        # 绑定配方选择事件
        def on_recipe_select(event):
            # 只有在工艺配置窗口未打开时才更新详情
            if not hasattr(self, '_process_window_open') or not self._process_window_open:
                show_recipe_details()
        
        recipe_listbox.bind('<<ListboxSelect>>', on_recipe_select)

        # 初始显示提示信息
        show_recipe_details()
    def create_new_recipe(self, update_callback=None):
        """创建新配方弹窗"""
        # 创建新建配方窗口
        new_recipe_window = tk.Toplevel(self.root)
        new_recipe_window.title("新建配方")
        new_recipe_window.geometry("400x300")
        new_recipe_window.resizable(False, False)
        new_recipe_window.transient(self.root)
        new_recipe_window.grab_set()

        # 居中显示
        new_recipe_window.update_idletasks()
        x = (new_recipe_window.winfo_screenwidth() - new_recipe_window.winfo_width()) // 2
        y = (new_recipe_window.winfo_screenheight() - new_recipe_window.winfo_height()) // 2
        new_recipe_window.geometry(f"+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(new_recipe_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配方名称
        ttk.Label(main_frame, text="配方名称:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        recipe_name_entry = ttk.Entry(main_frame, width=30)
        recipe_name_entry.grid(row=0, column=1, padx=5, pady=10)

        # 备注
        ttk.Label(main_frame, text="备注:").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        recipe_notes_text = tk.Text(main_frame, width=30, height=5)
        recipe_notes_text.grid(row=1, column=1, padx=5, pady=10)

        # 创建日期（只读显示）
        ttk.Label(main_frame, text="创建日期:").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        create_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        create_date_label = ttk.Label(main_frame, textvariable=create_date_var)
        create_date_label.grid(row=2, column=1, padx=5, pady=10, sticky=tk.W)

        def save_new_recipe():
            """保存新配方"""
            recipe_name = recipe_name_entry.get().strip()
            recipe_notes = recipe_notes_text.get("1.0", tk.END).strip()
            
            # 验证输入
            if not recipe_name:
                messagebox.showwarning("输入错误", "请输入配方名称")
                recipe_name_entry.focus_set()
                return
            
            # 检查配方名称是否重复
            if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
                messagebox.showwarning("重复配方", f"配方名称 '{recipe_name}' 已存在，请使用其他名称")
                recipe_name_entry.focus_set()
                return
            
            # 保存配方数据
            recipe_data = {
                'name': recipe_name,
                'notes': recipe_notes,
                'create_date': create_date_var.get(),
                'last_modified': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 添加到配方数据中
            if hasattr(self, 'recipe_data'):
                self.recipe_data[recipe_name] = recipe_data
            
            # 保存配方数据
            self.save_recipe_data()
            
            # 保存后重新加载recipe_data确保数据同步
            self.load_recipe_data()
            
            # 调用回调函数更新列表
            if update_callback:
                update_callback()
            
            self.log(f"新建配方: {recipe_name}")
            messagebox.showinfo("保存成功", f"配方 '{recipe_name}' 创建成功")
            new_recipe_window.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="保存", command=save_new_recipe).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=new_recipe_window.destroy).pack(side=tk.LEFT, padx=10)

        # 设置焦点
        recipe_name_entry.focus_set()
    def edit_recipe(self, recipe_name, update_callback=None):
        """编辑配方弹窗"""
        if not recipe_name:
            messagebox.showwarning("编辑配方", "请先选择一个配方")
            return
        
        # 创建编辑配方窗口
        edit_recipe_window = tk.Toplevel(self.root)
        edit_recipe_window.title("编辑配方")
        edit_recipe_window.geometry("400x350")
        edit_recipe_window.resizable(False, False)
        edit_recipe_window.transient(self.root)
        edit_recipe_window.grab_set()

        # 居中显示
        edit_recipe_window.update_idletasks()
        x = (edit_recipe_window.winfo_screenwidth() - edit_recipe_window.winfo_width()) // 2
        y = (edit_recipe_window.winfo_screenheight() - edit_recipe_window.winfo_height()) // 2
        edit_recipe_window.geometry(f"+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(edit_recipe_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配方名称
        ttk.Label(main_frame, text="配方名称:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        recipe_name_entry = ttk.Entry(main_frame, width=30)
        recipe_name_entry.grid(row=0, column=1, padx=5, pady=10)
        recipe_name_entry.insert(0, recipe_name)

        # 备注
        ttk.Label(main_frame, text="备注:").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        recipe_notes_text = tk.Text(main_frame, width=30, height=5)
        recipe_notes_text.grid(row=1, column=1, padx=5, pady=10)
        
        # 加载原有的备注信息
        if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
            recipe_notes_text.insert("1.0", self.recipe_data[recipe_name].get('notes', ''))
        else:
            recipe_notes_text.insert("1.0", "")

        # 创建日期（只读显示）
        ttk.Label(main_frame, text="创建日期:").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        create_date_var = tk.StringVar()
        if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
            create_date_var.set(self.recipe_data[recipe_name].get('create_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            create_date_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        create_date_label = ttk.Label(main_frame, textvariable=create_date_var)
        create_date_label.grid(row=2, column=1, padx=5, pady=10, sticky=tk.W)

        # 最后修改日期（只读显示）
        ttk.Label(main_frame, text="最后修改:").grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        modify_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        modify_date_label = ttk.Label(main_frame, textvariable=modify_date_var)
        modify_date_label.grid(row=3, column=1, padx=5, pady=10, sticky=tk.W)

        def save_edited_recipe():
            """保存编辑后的配方"""
            new_recipe_name = recipe_name_entry.get().strip()
            recipe_notes = recipe_notes_text.get("1.0", tk.END).strip()
            
            # 验证输入
            if not new_recipe_name:
                messagebox.showwarning("输入错误", "配方名称不能为空")
                recipe_name_entry.focus_set()
                return
            
            # 检查配方名称是否重复（排除当前编辑的配方）
            if hasattr(self, 'recipe_data') and new_recipe_name != recipe_name and new_recipe_name in self.recipe_data:
                messagebox.showwarning("重复配方", f"配方名称 '{new_recipe_name}' 已存在，请使用其他名称")
                recipe_name_entry.focus_set()
                return
            
            # 保存配方数据
            recipe_data = {
                'name': new_recipe_name,
                'notes': recipe_notes,
                'create_date': create_date_var.get(),
                'last_modified': modify_date_var.get()
            }
            
            # 更新配方数据
            if hasattr(self, 'recipe_data'):
                # 如果配方名称改变了，需要删除旧的并添加新的
                if new_recipe_name != recipe_name:
                    if recipe_name in self.recipe_data:
                        del self.recipe_data[recipe_name]
                self.recipe_data[new_recipe_name] = recipe_data
            
            # 调用回调函数更新列表
            if update_callback:
                update_callback()
            
            # 更新工艺控制页面的配方列表
            if hasattr(self, 'recipe_combo'):
                self.refresh_recipe_list()
            
            self.log(f"编辑配方: {recipe_name} -> {new_recipe_name}")
            messagebox.showinfo("保存成功", f"配方 '{new_recipe_name}' 修改成功")
            edit_recipe_window.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="保存", command=save_edited_recipe).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=edit_recipe_window.destroy).pack(side=tk.LEFT, padx=10)

        # 设置焦点
        recipe_name_entry.focus_set()
    def delete_recipe(self, recipe_name):
        """删除配方"""
        if not recipe_name:
            messagebox.showwarning("删除配方", "请先选择一个配方")
            return
        if messagebox.askyesno("删除配方", f"确定要删除配方 '{recipe_name}' 吗？"):
            # 从配方数据中删除
            if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
                del self.recipe_data[recipe_name]
                
                # 删除原始文件路径记录
                if hasattr(self, 'recipe_original_files') and recipe_name in self.recipe_original_files:
                    del self.recipe_original_files[recipe_name]
                
                # 更新配方列表显示
                if hasattr(self, 'recipe_listbox'):
                    self.update_recipe_list_display()
                
                # 更新工艺控制页面的配方列表
                if hasattr(self, 'recipe_combo'):
                    self.refresh_recipe_list()
                

                
                # 保存配方数据
                self.save_recipe_data()
                
                # 保存后重新加载recipe_data确保数据同步
                self.load_recipe_data()
            
            messagebox.showinfo("删除配方", f"配方 '{recipe_name}' 已删除")
    def add_recipe_device(self):
        """配方详情窗口 - 添加配方"""
        # 创建配方详情窗口
        recipe_detail_window = tk.Toplevel(self.root)
        recipe_detail_window.title("配方详情")
        recipe_detail_window.geometry("700x600")
        recipe_detail_window.resizable(False, False)
        recipe_detail_window.transient(self.root)
        recipe_detail_window.grab_set()

        # 居中显示
        recipe_detail_window.update_idletasks()
        x = (recipe_detail_window.winfo_screenwidth() - recipe_detail_window.winfo_width()) // 2
        y = (recipe_detail_window.winfo_screenheight() - recipe_detail_window.winfo_height()) // 2
        recipe_detail_window.geometry(f"+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(recipe_detail_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 基本信息框架
        basic_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="10")
        basic_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E)

        # 配方名称
        ttk.Label(basic_frame, text="配方名称:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(basic_frame, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W+tk.E)

        # 配方描述框架
        desc_frame = ttk.LabelFrame(main_frame, text="配方描述", padding="10")
        desc_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E+tk.N+tk.S)

        description_entry = tk.Text(desc_frame, width=50, height=4)
        description_entry.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 物料配置框架
        materials_frame = ttk.LabelFrame(main_frame, text="物料配置", padding="10")
        materials_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E+tk.N+tk.S)

        # 物料列表容器
        materials_container = ttk.Frame(materials_frame)
        materials_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 物料列表
        materials_list = []

        def add_material_row():
            """添加物料行"""
            row_frame = ttk.Frame(materials_container)
            row_frame.pack(fill=tk.X, pady=2)

            # 物料类型
            material_type_var = tk.StringVar()
            material_type_combo = ttk.Combobox(row_frame, textvariable=material_type_var, width=12, state="readonly")
            material_type_combo['values'] = ('水泥', '水', '添加剂A', '添加剂B', '添加剂C')
            material_type_combo.pack(side=tk.LEFT, padx=5)
            material_type_combo.current(0)

            # 重量
            weight_var = tk.StringVar()
            weight_entry = ttk.Entry(row_frame, textvariable=weight_var, width=10)
            weight_entry.pack(side=tk.LEFT, padx=5)
            weight_entry.insert(0, "100")

            # 单位
            ttk.Label(row_frame, text="g").pack(side=tk.LEFT, padx=5)

            # 删除按钮
            def remove_row():
                row_frame.destroy()
                materials_list.remove((material_type_var, weight_var))

            remove_btn = ttk.Button(row_frame, text="删除", command=remove_row, width=6)
            remove_btn.pack(side=tk.LEFT, padx=5)

            materials_list.append((material_type_var, weight_var))

        def add_material_row_initial():
            """初始添加两行物料"""
            add_material_row()
            add_material_row()

        # 添加物料按钮
        add_btn_frame = ttk.Frame(materials_frame)
        add_btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(add_btn_frame, text="添加物料", command=add_material_row).pack(side=tk.LEFT, padx=5)

        # 初始添加物料行
        add_material_row_initial()

        def save_recipe_info():
            """保存配方信息"""
            name = name_var.get()
            description = description_entry.get("1.0", tk.END).strip()

            # 验证输入
            if not name:
                messagebox.showwarning("输入错误", "请输入配方名称")
                name_entry.focus_set()
                return

            if len(materials_list) == 0:
                messagebox.showwarning("输入错误", "请至少添加一种物料")
                return

            # 收集物料数据
            materials_data = []
            for material_type_var, weight_var in materials_list:
                material_type = material_type_var.get()
                weight = weight_var.get().strip()
                
                if not material_type:
                    messagebox.showwarning("输入错误", "请选择物料类型")
                    return
                
                if not weight:
                    messagebox.showwarning("输入错误", "请输入物料重量")
                    return
                
                materials_data.append({
                    'type': material_type,
                    'weight': weight
                })

            # 创建配方数据
            recipe_data = {
                'name': name,
                'description': description,
                'materials': materials_data,
                'create_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 保存配方（这里可以添加到配方数据中）
            recipe_key = f"{name}"
            if not hasattr(self, 'recipe_data'):
                self.recipe_data = {}
            
            self.recipe_data[recipe_key] = recipe_data
            
            # 更新配方列表显示
            self.update_recipe_list_display()
            

            
            # 更新工艺控制页面的配方列表
            if hasattr(self, 'recipe_combo'):
                self.refresh_recipe_list()
            
            messagebox.showinfo("保存成功", f"配方 '{name}' 已保存")
            recipe_detail_window.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="保存配方", command=save_recipe_info, width=10).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="取消", command=recipe_detail_window.destroy, width=10).pack(side=tk.RIGHT, padx=10)

    def save_device_info(self):
        """保存设备信息"""
        if not device_type:
            messagebox.showwarning("输入错误", "请选择设备类型")
            device_type_combo.focus_set()
            return

        # 验证IP地址格式
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
            messagebox.showwarning("输入错误", "请输入有效的IP地址")
            ip_entry.focus_set()
            return

        # 验证端口格式
        if not re.match(r'^\d+$', port) or not (0 < int(port) <= 65535):
            messagebox.showwarning("输入错误", "请输入有效的端口号(1-65535)")
            port_entry.focus_set()
            return

        # 保存设备信息（这里可以保存到配方数据中）
        device_info = {
            'ip': ip,
            'port': port,
            'device_type': device_type,
            'added_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 这里可以添加保存到配方数据的逻辑
        self.log(f"添加配方设备: {device_type} - {ip}:{port}")
        messagebox.showinfo("保存成功", f"设备信息已保存IP: {ip}端口: {port}设备类型: {device_type}")
        add_device_window.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="保存", command=save_device_info).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=add_device_window.destroy).pack(side=tk.LEFT, padx=10)

        # 设置焦点
        ip_entry.focus_set()

    def import_recipe(self):
        """导入配方"""
        filename = filedialog.askopenfilename(
            title="选择配方文件",
            filetypes=[("配方文件", "pf_*.json"), ("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 检查配方数据结构
            if 'recipes' in import_data and isinstance(import_data['recipes'], list):
                # 初始化配方数据
                if not hasattr(self, 'recipe_data'):
                    self.recipe_data = {}
                
                # 初始化原始文件路径记录
                if not hasattr(self, 'recipe_original_files'):
                    self.recipe_original_files = {}
                
                imported_count = 0
                skipped_count = 0
                
                for recipe in import_data['recipes']:
                    if 'name' in recipe and recipe['name']:
                        recipe_name = recipe['name']
                        
                        # 检查配方是否已存在
                        if recipe_name in self.recipe_data:
                            # 询问是否覆盖
                            if messagebox.askyesno("配方冲突", f"配方 '{recipe_name}' 已存在，是否覆盖？"):
                                self.recipe_data[recipe_name] = recipe
                                # 记录原始文件路径
                                self.recipe_original_files[recipe_name] = filename
                                imported_count += 1
                            else:
                                skipped_count += 1
                        else:
                            self.recipe_data[recipe_name] = recipe
                            # 记录原始文件路径
                            self.recipe_original_files[recipe_name] = filename
                            imported_count += 1
                
                # 更新配方列表显示
                if hasattr(self, 'recipe_listbox'):
                    self.update_recipe_list_display()
                
                # 更新工艺控制页面的配方列表
                if hasattr(self, 'recipe_combo'):
                    self.refresh_recipe_list()
                

                
                # 导入后重新加载recipe_data确保数据同步
                self.load_recipe_data()
                
                messagebox.showinfo("导入成功", f"成功导入 {imported_count} 个配方，跳过 {skipped_count} 个重复配方")
                self.log(f"配方导入成功: {filename}, 导入 {imported_count} 个，跳过 {skipped_count} 个")
            else:
                messagebox.showwarning("导入失败", "配方文件格式不正确，缺少配方列表")
                
        except Exception as e:
            messagebox.showerror("导入失败", f"导入失败: {str(e)}")
            self.log(f"配方导入失败: {str(e)}")

    def export_recipe(self):
        """导出配方到pf_时间戳.json文件"""
        # 检查是否有配方数据
        if not hasattr(self, 'recipe_data') or not self.recipe_data:
            messagebox.showwarning("导出失败", "没有配方数据可导出")
            return
        
        # 询问导出范围
        export_options = ["导出所有配方", "导出当前选中配方"]
        export_choice = tk.StringVar(value=export_options[0])
        
        # 创建选择对话框
        choice_window = tk.Toplevel(self.root)
        choice_window.title("导出选项")
        choice_window.geometry("350x200")
        choice_window.resizable(False, False)
        choice_window.transient(self.root)
        choice_window.grab_set()
        
        # 居中显示
        choice_window.update_idletasks()
        x = (choice_window.winfo_screenwidth() - choice_window.winfo_width()) // 2
        y = (choice_window.winfo_screenheight() - choice_window.winfo_height()) // 2
        choice_window.geometry(f"+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(choice_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="选择导出范围:").pack(pady=10)
        
        # 导出选项
        for option in export_options:
            ttk.Radiobutton(main_frame, text=option, variable=export_choice, value=option).pack(anchor=tk.W)
        
        def do_export():
            choice_window.destroy()
            
            # 根据选择准备导出数据
            recipes_to_export = []
            
            if export_choice.get() == "导出所有配方":
                # 导出所有配方
                for recipe_name, recipe_data in self.recipe_data.items():
                    recipes_to_export.append(recipe_data)
            else:
                # 导出当前选中配方
                if hasattr(self, 'recipe_listbox'):
                    selected_index = self.recipe_listbox.curselection()
                    if selected_index:
                        recipe_display_name = self.recipe_listbox.get(selected_index[0])
                        recipe_name = recipe_display_name.split('-')[0]
                        if recipe_name in self.recipe_data:
                            recipes_to_export.append(self.recipe_data[recipe_name])
                    else:
                        messagebox.showwarning("导出失败", "请先选择一个配方")
                        return
            
            if not recipes_to_export:
                messagebox.showwarning("导出失败", "没有配方数据可导出")
                return
            
            # 准备导出数据
            export_data = {
                'recipes': recipes_to_export,
                'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_recipes': len(recipes_to_export),
                'exported_by': '实验室无人称重平台'
            }
            
            # 选择保存位置
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"pf_{timestamp}.json"
            
            filename = filedialog.asksaveasfilename(
                title="保存配方文件",
                initialfile=default_filename,
                defaultextension=".json",
                filetypes=[("配方文件", "pf_*.json"), ("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if not filename:
                return
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("导出成功", f"成功导出 {len(recipes_to_export)} 个配方到 {filename}")
                self.log(f"配方导出成功: {filename}, 共 {len(recipes_to_export)} 个配方")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出失败: {str(e)}")
                self.log(f"配方导出失败: {str(e)}")
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="导出", command=do_export).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=choice_window.destroy).pack(side=tk.LEFT, padx=10)
    def configure_process(self, recipe_listbox):
        """配置工艺"""
        # 检查是否选择了配方
        selected_index = recipe_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("选择错误", "请先选择一个配方")
            return
        
        # 获取选中的配方
        recipe_display_name = recipe_listbox.get(selected_index[0])
        recipe_name = recipe_display_name.split('-')[0]
        # 打印当前工艺对应配方名称
        print(f"当前配置工艺的配方: {recipe_name}")
        # 检查配方是否存在
        if not hasattr(self, 'recipe_data') or recipe_name not in self.recipe_data:
            messagebox.showwarning("配方错误", "未找到选中的配方")
            return
        
        recipe_data = self.recipe_data[recipe_name]
        print(f"当前配置工艺的详情: {recipe_data}")
        # 检查配方是否有物料
        if 'materials' not in recipe_data or not recipe_data['materials']:
            messagebox.showwarning("配置错误", "该配方没有物料配置，请先添加物料")
            return

        # 创建工艺配置窗口
        process_window = tk.Toplevel(self.root)
        process_window.title(f"工艺配置 - {recipe_name}")
        process_window.geometry("800x700")
        process_window.resizable(True, True)
        process_window.transient(self.root)
        # 保存当前配方列表的选中状态和控件引用，避免工艺配置窗口干扰
        self._preserved_recipe_selection = recipe_listbox.curselection()
        self._preserved_recipe_listbox = recipe_listbox  # 保存控件引用
        self._process_window_open = True  # 标记工艺配置窗口已打开
        
        # 保存配方名称和原始文件路径到窗口属性
        process_window.recipe_name = recipe_name
        
        # 加载现有的工艺配置数据（如果有）
        if 'process_config' in recipe_data:
            print(f"加载现有工艺配置: {recipe_data}")
        else:
            # 初始化工艺配置数据
            recipe_data['process_config'] = {}
            recipe_data['process_config']['last_modified'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            recipe_data['process_config']['process_config_saved'] = False
        # 重新设计参数创建函数，直接绑定到数据结构
        
        # 居中显示
        process_window.update_idletasks()
        x = (process_window.winfo_screenwidth() - process_window.winfo_width()) // 2
        y = (process_window.winfo_screenheight() - process_window.winfo_height()) // 2
        process_window.geometry(f"+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(process_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部按钮框架（加载和保存）
        top_btn_frame = ttk.Frame(main_frame)
        top_btn_frame.pack(fill=tk.X, pady=(0, 10))

        # 创建选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        def calculate_and_display():
            try:
            # 从全局控件获取值
                n = self.material_widgets[material_key]['target_output_entry'].get()
                
                # 获取A2、A3、C1、C2、C3的值，如果为空则设置自动化默认值
                A2 = self.material_widgets[material_key]['A2_entry'].get()
                A3 = self.material_widgets[material_key]['A3_entry'].get()
                C1 = self.material_widgets[material_key]['C1_entry'].get()
                C2 = self.material_widgets[material_key]['C2_entry'].get()
                C3 = self.material_widgets[material_key]['C3_entry'].get()
                
                # 只有在值为空时才设置自动化默认值
                if not A2 or A2.strip() == "":
                    # 自动化A2：目标值的20%
                    A2_value = float(n) * 0.2
                    # 更新tk.DoubleVar的值，这样控件才会真正更新
                    params = self.material_widgets[material_key].get('params', {})
                    if 'A2' in params:
                        params['A2'].set(A2_value)
                    A2 = str(A2_value)
                    
                if not A3 or A3.strip() == "":
                    # 自动化A3：目标值的5%
                    A3_value = float(n) * 0.05
                    # 更新tk.DoubleVar的值，这样控件才会真正更新
                    params = self.material_widgets[material_key].get('params', {})
                    if 'A3' in params:
                        params['A3'].set(A3_value)
                    A3 = str(A3_value)
                
                if not C1 or C1.strip() == "":
                    # 自动化C1：目标值的2%
                    C1_value = float(n) * 0.02
                    # 更新tk.DoubleVar的值，这样控件才会真正更新
                    params = self.material_widgets[material_key].get('params', {})
                    if 'C1' in params:
                        params['C1'].set(C1_value)
                    C1 = str(C1_value)
                
                if not C2 or C2.strip() == "":
                    # 自动化C2：目标值的1%
                    C2_value = float(n) * 0.01
                    # 更新tk.DoubleVar的值，这样控件才会真正更新
                    params = self.material_widgets[material_key].get('params', {})
                    if 'C2' in params:
                        params['C2'].set(C2_value)
                    C2 = str(C2_value)
                
                if not C3 or C3.strip() == "":
                    # 自动化C3：目标值的0.5%
                    C3_value = float(n) * 0.005
                    # 更新tk.DoubleVar的值，这样控件才会真正更新
                    params = self.material_widgets[material_key].get('params', {})
                    if 'C3' in params:
                        params['C3'].set(C3_value)
                    C3 = str(C3_value)
                    
                print(f"n: {n}, A2: {A2}, A3: {A3}, C1: {C1}, C2: {C2}, C3: {C3}")    
                    # 转换为数值
                n = float(n)
                A2 = float(A2)
                A3 = float(A3)
                C1 = float(C1)
                C2 = float(C2)
                C3 = float(C3)
                    
                    # 计算A1
                A1 = n - A2 - A3
                self.material_widgets[material_key]['A1_value_label'].config(text=f"{A1:.2f}")
                    
                    # 计算控制点
                high_speed_point = A1 - C1
                mid_speed_point = n - A3 - C2
                low_speed_point = n - C3
                    # 检查控制点是否为负数
                if high_speed_point < 0 or mid_speed_point < 0 or low_speed_point < 0:
                    self.material_widgets[material_key]['control_points_text'].delete(1.0, tk.END)
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, "错误：控制点不能为负数！\n")
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"高速阶段控制点: {high_speed_point:.2f}\n")
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"中速阶段控制点: {mid_speed_point:.2f}\n")
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"低速阶段控制点: {low_speed_point:.2f}")
                    self.material_widgets[material_key]['control_points_text'].config(foreground="red")
                else:
                    self.material_widgets[material_key]['control_points_text'].delete(1.0, tk.END)
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"高速阶段控制点: {high_speed_point:.2f}克\n")
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"中速阶段控制点: {mid_speed_point:.2f}克\n")
                    self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"低速阶段控制点: {low_speed_point:.2f}克")
                    self.material_widgets[material_key]['control_points_text'].config(foreground="black")
                    
            except Exception as e:
                self.material_widgets[material_key]['control_points_text'].delete(1.0, tk.END)
                self.material_widgets[material_key]['control_points_text'].insert(tk.END, f"计算错误: {str(e)}")
            
        def create_process_params(params_frame, process_type, stages_data=None, other_params=None, material_key=None, material_weight=None):
            # 清空现有控件
            for widget in params_frame.winfo_children():
                widget.destroy()
            
            # 初始化参数字典
            params = {}
            print(f"create_process_params： {process_type}");
            if process_type in ["固态供料", "液态供料","胶乳供料"]:
                # 确保material_widgets中有当前物料的字典
                if material_key not in self.material_widgets:
                    self.material_widgets[material_key] = {}
                print(f"create_process_params： {material_key}");
                
                # 将params字典存储到material_widgets中，以便calculate_and_display函数可以访问
                self.material_widgets[material_key]['params'] = params
                
                # 从物料重量中获取目标值，去掉"g"后缀
                target_value = 100  # 默认值
                if material_weight:
                    # 去掉"g"后缀并转换为数值
                    weight_str = str(material_weight).replace('g', '').replace('G', '').strip()
                    try:
                        target_value = float(weight_str)
                    except ValueError:
                        target_value = 100
                
                # 参数1：出料目标值 n
                target_output_label = ttk.Label(params_frame, text="出料目标值n(克):")
                target_output_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

                target_output_entry = ttk.Entry(params_frame, width=10)
                target_output_entry.grid(row=0, column=1, padx=5, pady=2)
                target_output_entry.insert(0, str(target_value))

                self.material_widgets[material_key]['target_output_entry'] = target_output_entry
                self.material_widgets[material_key]['target_output_label'] = target_output_label
                
                # 参数2：高速阶段出料量 A1（自动计算，但显示）
                A1_label = ttk.Label(params_frame, text="高速阶段出料量A1(克):")
                A1_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
                
                # A1是自动计算的，使用Label显示而不是Entry
                A1_value_label = ttk.Label(params_frame, text="自动计算", foreground="blue", relief="sunken", width=8)
                A1_value_label.grid(row=1, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['A1_value_label'] = A1_value_label
                self.material_widgets[material_key]['A1_label'] = A1_label
                
                # 参数3：中速阶段出料量 A2
                A2_label = ttk.Label(params_frame, text="中速阶段出料量A2(克):")
                A2_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
                
                # 优先从other_params读取，其次从stages_data，最后使用默认值
                A2_value = 8  # 默认值
                if other_params and 'A2' in other_params:
                    A2_value = other_params['A2']
                elif stages_data and len(stages_data) > 1 and 'output' in stages_data[1]:
                    A2_value = stages_data[1]['output']
                else:
                    # 使用自动化方案：目标值的20%
                    A2_value = target_value * 0.2
                
                params['A2'] = tk.DoubleVar(value=A2_value)
                A2_entry = ttk.Entry(params_frame, textvariable=params['A2'], width=10)
                A2_entry.grid(row=2, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['A2_entry'] = A2_entry
                self.material_widgets[material_key]['A2_label'] = A2_label
                
                # 参数4：低速阶段出料量 A3
                A3_label = ttk.Label(params_frame, text="低速阶段出料量A3(克):")
                A3_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
                
                # 优先从other_params读取，其次从stages_data，最后使用默认值
                A3_value = 2  # 默认值
                if other_params and 'A3' in other_params:
                    A3_value = other_params['A3']
                elif stages_data and len(stages_data) > 2 and 'output' in stages_data[2]:
                    A3_value = stages_data[2]['output']
                else:
                    # 使用自动化方案：目标值的5%
                    A3_value = target_value * 0.05
                
                params['A3'] = tk.DoubleVar(value=A3_value)
                A3_entry = ttk.Entry(params_frame, textvariable=params['A3'], width=10)
                A3_entry.grid(row=3, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['A3_entry'] = A3_entry
                self.material_widgets[material_key]['A3_label'] = A3_label
                
                # 参数5：高速阶段转速 R1
                R1_label = ttk.Label(params_frame, text="高速阶段转速R1(转/分):")
                R1_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
                
                params['R1'] = tk.DoubleVar(value=stages_data[0]['rpm'] if stages_data else 400)
                R1_entry = ttk.Entry(params_frame, textvariable=params['R1'], width=10)
                R1_entry.grid(row=4, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['R1_entry'] = R1_entry
                self.material_widgets[material_key]['R1_label'] = R1_label
                
                # 参数6：中速阶段转速 R2
                R2_label = ttk.Label(params_frame, text="中速阶段转速R2(转/分):")
                R2_label.grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
                
                params['R2'] = tk.DoubleVar(value=stages_data[1]['rpm'] if stages_data else 40)
                R2_entry = ttk.Entry(params_frame, textvariable=params['R2'], width=10)
                R2_entry.grid(row=5, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['R2_entry'] = R2_entry
                self.material_widgets[material_key]['R2_label'] = R2_label
                
                # 参数7：低速阶段转速 R3
                R3_label = ttk.Label(params_frame, text="低速阶段转速R3(转/分):")
                R3_label.grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
                
                params['R3'] = tk.DoubleVar(value=stages_data[2]['rpm'] if stages_data else 4)
                R3_entry = ttk.Entry(params_frame, textvariable=params['R3'], width=10)
                R3_entry.grid(row=6, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['R3_entry'] = R3_entry
                self.material_widgets[material_key]['R3_label'] = R3_label
                
                # 参数8：高速阶段延迟 C1
                C1_label = ttk.Label(params_frame, text="高速阶段延迟C1(克):")
                C1_label.grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
                
                # 优先从other_params读取，其次从stages_data，最后使用默认值
                C1_value = 2  # 默认值
                if other_params and 'C1' in other_params:
                    C1_value = other_params['C1']
                elif stages_data and len(stages_data) > 0 and 'delay_preset' in stages_data[0]:
                    C1_value = stages_data[0]['delay_preset']
                else:
                    # 使用自动化方案：目标值的2%
                    C1_value = target_value * 0.02
                
                params['C1'] = tk.DoubleVar(value=C1_value)
                C1_entry = ttk.Entry(params_frame, textvariable=params['C1'], width=10)
                C1_entry.grid(row=7, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['C1_entry'] = C1_entry
                self.material_widgets[material_key]['C1_label'] = C1_label
                
                # 参数9：中速阶段延迟 C2
                C2_label = ttk.Label(params_frame, text="中速阶段延迟C2(克):")
                C2_label.grid(row=8, column=0, sticky=tk.W, padx=5, pady=2)
                
                # 优先从other_params读取，其次从stages_data，最后使用默认值
                C2_value = 0.5  # 默认值
                if other_params and 'C2' in other_params:
                    C2_value = other_params['C2']
                elif stages_data and len(stages_data) > 1 and 'delay_preset' in stages_data[1]:
                    C2_value = stages_data[1]['delay_preset']
                else:
                    # 使用自动化方案：目标值的1%
                    C2_value = target_value * 0.01
                
                params['C2'] = tk.DoubleVar(value=C2_value)
                C2_entry = ttk.Entry(params_frame, textvariable=params['C2'], width=10)
                C2_entry.grid(row=8, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['C2_entry'] = C2_entry
                self.material_widgets[material_key]['C2_label'] = C2_label
                
                # 参数10：低速阶段延迟 C3
                C3_label = ttk.Label(params_frame, text="低速阶段延迟C3(克):")
                C3_label.grid(row=9, column=0, sticky=tk.W, padx=5, pady=2)
                
                # 优先从other_params读取，其次从stages_data，最后使用默认值
                C3_value = 0.1  # 默认值
                if other_params and 'C3' in other_params:
                    C3_value = other_params['C3']
                elif stages_data and len(stages_data) > 2 and 'delay_preset' in stages_data[2]:
                    C3_value = stages_data[2]['delay_preset']
                else:
                    # 使用自动化方案：目标值的0.5%
                    C3_value = target_value * 0.005
                
                params['C3'] = tk.DoubleVar(value=C3_value)
                C3_entry = ttk.Entry(params_frame, textvariable=params['C3'], width=10)
                C3_entry.grid(row=9, column=1, padx=5, pady=2)
                
                self.material_widgets[material_key]['C3_entry'] = C3_entry
                self.material_widgets[material_key]['C3_label'] = C3_label
                
                # 控制点显示
                control_title_label = ttk.Label(params_frame, text="控制点信息:", font=self.font_bold)
                control_title_label.grid(row=10, column=0, columnspan=2, pady=10)
                
                control_points_text = tk.Text(params_frame, height=4, width=40, font=self.font_small)
                control_points_text.grid(row=11, column=0, columnspan=2, padx=5, pady=5)
                
                self.material_widgets[material_key]['control_points_text'] = control_points_text
                self.material_widgets[material_key]['control_title_label'] = control_title_label
                
               
                # 绑定Entry控件的变化事件（仅当控件存在时）
                if 'target_output_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['target_output_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                if 'A2_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['A2_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                if 'A3_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['A3_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                if 'C1_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['C1_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                if 'C2_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['C2_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                if 'C3_entry' in self.material_widgets[material_key]:
                    self.material_widgets[material_key]['C3_entry'].bind('<KeyRelease>', lambda e: calculate_and_display())
                # 初始计算（仅当控件存在时）
                if 'target_output_entry' in self.material_widgets[material_key]:
                    calculate_and_display()    
                                
            # 计算和显示函数
            
        # 定义tab切换事件处理函数
        def on_tab_changed(event):
            try:
                # 获取当前选中的tab索引
                current_tab_index = notebook.index("current")

                # 获取当前tab的frame
                current_frame = notebook.nametowidget(notebook.tabs()[current_tab_index])

                # 获取物料信息
                if hasattr(current_frame, 'material_id'):
                    material_id = current_frame.material_id
                    material_index = current_frame.material_index
                    
                    print(f"切换到物料tab: {material_id} (索引: {material_index})")
                    
                    # 获取当前物料的工艺类型
                    material_key = f"material_{material_index}"
                    if (hasattr(self, 'material_widgets') and 
                        material_key in self.material_widgets and
                        'process_type_combo' in self.material_widgets[material_key]):
                        current_type = self.material_widgets[material_key]['process_type_combo'].get()
                        print(f"当前物料工艺类型: {current_type}")
                        
                        # 保存前一个tab的数据（如果存在）
                        if hasattr(on_tab_changed, 'last_material_key'):
                            last_key = on_tab_changed.last_material_key
                            if last_key != material_key:
                                try:
                                    if (last_key in self.material_widgets and 
                                        'process_type_combo' in self.material_widgets[last_key]):
                                        last_type = self.material_widgets[last_key]['process_type_combo'].get()
                                        if last_key not in recipe_data['process_config']:
                                            recipe_data['process_config'][last_key] = {}
                                        recipe_data['process_config'][last_key]['process_type'] = last_type
                                        print(f"已保存 {last_key} 的工艺类型: {last_type}")
                                except Exception as save_error:
                                    print(f"保存前一个tab数据时出错: {save_error}")
                        
                        # 记录当前tab
                        on_tab_changed.last_material_key = material_key
                        
                else:
                    print(f"切换到tab索引: {current_tab_index} (无物料信息)")
                    
            except Exception as e:
                print(f"Tab切换时出错: {e}")
        
        # 绑定tab切换事件
        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
        
        # 检查配方是否有工艺配置
        process_config_data = recipe_data.get('process_config', {})
        # 为每个物料创建工艺配置页
        for i, material in enumerate(recipe_data['materials']):
            material_type = material.get('type', '未知物料')
            material_weight = material.get('weight', '0')
            # 生成唯一标识符，确保每个物料都有唯一ID
            material_id = material.get('id')
            if not material_id:
                material_id = f"material_{i}"
                # 为配方数据中的物料添加ID
                material['id'] = material_id
            # 创建物料工艺配置页
            material_frame = ttk.Frame(notebook, padding="10")
            notebook.add(material_frame, text=f"{material_type} ({material_weight}g)")
            # 将物料ID存储到frame的属性中，便于后续查找
            material_frame.material_id = material_id
            material_frame.material_index = i
            # 工艺类型选择
            print(f"##########{i}#######")
            ttk.Label(material_frame, text="工艺类型:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
            # 设置默认值为当前配方的工艺类型
            material_key = f"material_{i}"  # 与 process_config 中的键格式一致
             # 保存控件引用
            if material_key not in self.material_widgets:
                self.material_widgets[material_key] = {}
            print(f"******{material_key}******")    
            process_type_var = tk.StringVar()
            self.material_widgets[material_key]['process_type_combo'] = ttk.Combobox(material_frame, textvariable=process_type_var, width=15, state="readonly")
            
            
            
            # 设置工艺类型选项
            available_process_types = self.get_available_process_types()
            self.material_widgets[material_key]['process_type_combo']['values'] = tuple(available_process_types)
            self.material_widgets[material_key]['process_type_combo'].grid(row=0, column=1, padx=5, pady=10)
            
            # IP地址选择combobox
            ttk.Label(material_frame, text="IP地址:").grid(row=0, column=2, padx=5, pady=10, sticky=tk.W)
            
            # 从device_list获取IP地址列表
            device_ips = []
            if hasattr(self, 'device_list') and self.device_list:
                device_ips = [device['ip'] for device in self.device_list if 'ip' in device]
            
            # 设置默认IP值
            default_ip = "192.168.1.100"
            if material_key in self.recipe_data[recipe_name].get('process_config', {}):
                material_config = self.recipe_data[recipe_name]['process_config'][material_key]
                # 优先从根级别读取IP，如果没有则从other_params中读取（兼容旧数据）
                ip_value = material_config.get('ip')
                if ip_value:
                    default_ip = ip_value
                else:
                    other_params = material_config.get('other_params', {})
                    if 'ip' in other_params:
                        default_ip = other_params['ip']
            
            ip_var = tk.StringVar(value=default_ip)
            self.material_widgets[material_key]['ip_combo'] = ttk.Combobox(material_frame, textvariable=ip_var, width=15, state="readonly")
            self.material_widgets[material_key]['ip_combo']['values'] = tuple(device_ips)
            self.material_widgets[material_key]['ip_combo'].grid(row=0, column=3, padx=5, pady=10)
            
            # 端口输入
            ttk.Label(material_frame, text="端口:").grid(row=0, column=4, padx=5, pady=10, sticky=tk.W)
            port_var = tk.StringVar(value="8888")
            self.material_widgets[material_key]['port_entry'] = ttk.Entry(material_frame, textvariable=port_var, width=8)
            self.material_widgets[material_key]['port_entry'].grid(row=0, column=5, padx=5, pady=10)     
            if material_key in self.recipe_data[recipe_name]['process_config']:
                current_process_type = self.recipe_data[recipe_name]['process_config'][material_key]['process_type']
                self.material_widgets[material_key]['process_type_combo'].set(current_process_type)  # 显示当前工艺类型
                print(f"{current_process_type}:{material_key}")
                
                # 加载保存的IP地址和端口
                material_config = self.recipe_data[recipe_name]['process_config'][material_key]
                other_params = material_config.get('other_params', {})
                
                # 优先从根级别读取IP和端口，如果没有则从other_params中读取（兼容旧数据）
                ip_value = material_config.get('ip')
                if not ip_value:
                    ip_value = other_params.get('ip', '192.168.1.100')
                
                port_value = material_config.get('port')
                if not port_value:
                    port_value = other_params.get('port', '8888')
                
                # 设置IP combobox的值
                self.material_widgets[material_key]['ip_combo'].set(ip_value)
                
                # 设置端口值
                self.material_widgets[material_key]['port_entry'].delete(0, tk.END)
                self.material_widgets[material_key]['port_entry'].insert(0, port_value)
            else:
                self.material_widgets[material_key]['process_type_combo'].set("---请选择工艺类型---")  # 默认值（可选）
            self.root.after(100, lambda combo=self.material_widgets[material_key]['process_type_combo'] , value=current_process_type: combo.set(value))
            # 工艺类型变化时更新参数

            # 工艺参数框架（先创建，再定义函数）
            params_frame = ttk.LabelFrame(material_frame, text="工艺参数", padding="10")
            params_frame.grid(row=1, column=0, columnspan=6, padx=5, pady=10, sticky=tk.W+tk.E)
            
            # 获取配方中保存的工艺类型和配置
            material_config_key = f'material_{i}'
            material_config = process_config_data.get(material_config_key, {})
            saved_type = material_config.get('process_type', '固态供料')
            stages_data = material_config.get('stages', [])
            other_params = material_config.get('other_params', {})
            
            def on_process_type_change(event):
                # 保存当前焦点状态，避免影响父窗口
                current_focus = process_window.focus_get()
                
                # 获取当前物料的保存配置
                material_config_key = f'material_{i}'
                material_config = process_config_data.get(material_config_key, {})
                stages_data = material_config.get('stages', [])
                other_params = material_config.get('other_params', {})
                
                create_process_params(params_frame, process_type_var.get(), stages_data, other_params, material_key, material_weight)
                # 恢复焦点到工艺配置窗口
                if current_focus:
                    current_focus.focus_set()
            
            # 先设置初始值（避免触发事件）
            process_type_var.set(saved_type)
            
            # 初始创建参数框架
            create_process_params(params_frame, saved_type, stages_data, other_params, material_key, material_weight)
            
            # 然后绑定事件
            self.material_widgets[material_key]['process_type_combo'].bind('<<ComboboxSelected>>', on_process_type_change)
            
            # 根据工艺类型显示不同的参数
            
        # 保存按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def close_process_window():
            # 关闭工艺配置窗口时恢复状态
            self._process_window_open = False
            # 恢复配方列表的选中状态
            try:
                if (hasattr(self, '_preserved_recipe_selection') and 
                    self._preserved_recipe_selection and 
                    recipe_listbox.winfo_exists()):
                    recipe_listbox.selection_set(self._preserved_recipe_selection)
            except tk.TclError:
                # 控件已被销毁，忽略错误
                pass
            except Exception as e:
                print(f"恢复配方列表选择时出错: {e}")
            
            # 释放焦点并关闭窗口
            try:
                if process_window.winfo_exists():
                    process_window.grab_release()  # 释放模态锁定
                    process_window.destroy()
            except tk.TclError:
                # 窗口已被销毁，忽略错误
                pass
        
        def save_process_config():
            # 添加调试信息
            print("=== 开始保存工艺配置 ===")
            
            # 收集所有物料的工艺配置数据
            process_config_data = {
                'process_config_saved': True,
                'last_modified': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 遍历所有物料标签页
            total_tabs = notebook.index("end")
            print(f"总标签页数: {total_tabs}")
            
            for i in range(total_tabs):
                material_frame = notebook.nametowidget(notebook.tabs()[i])
                material_name = notebook.tab(i, "text")
                print(f"处理物料标签页 {i}: {material_name}")
                
                # 获取工艺类型
                process_type_combo = None
                for widget in material_frame.winfo_children():
                    if isinstance(widget, ttk.Combobox):
                        process_type_combo = widget
                        break
                
                if process_type_combo:
                    process_type = process_type_combo.get()
                    if not process_type:
                        process_type = "固态"  # 如果为空，设置默认值
                    print(f"工艺类型: {process_type}")
                    
                    # 查找参数框架
                    params_frame = None
                    for widget in material_frame.winfo_children():
                        if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == "工艺参数":
                            params_frame = widget
                            break
                    
                    # 根据工艺类型处理阶段数据
                    stages_data = []
                    if params_frame:
                        print("找到工艺参数框架")
                        
                        # 直接从实例变量中获取阶段配置数据
                        material_key = getattr(material_frame, 'material_id', f"material_{i}")
                        stages_data = []

                        
                        # 直接从内存中的material_widgets中收集参数
                        other_params = {}
                        
                        # 获取当前物料的控件字典
                        if material_key in self.material_widgets:
                            material_widgets = self.material_widgets[material_key]
                            
                            # 收集各个参数的值
                            try:
                                if 'target_output_entry' in material_widgets:
                                    value = material_widgets['target_output_entry'].get()
                                    other_params['target_output'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'A2_entry' in material_widgets:
                                    value = material_widgets['A2_entry'].get()
                                    other_params['A2'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'A3_entry' in material_widgets:
                                    value = material_widgets['A3_entry'].get()
                                    other_params['A3'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'R1_entry' in material_widgets:
                                    value = material_widgets['R1_entry'].get()
                                    other_params['R1'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'R2_entry' in material_widgets:
                                    value = material_widgets['R2_entry'].get()
                                    other_params['R2'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'R3_entry' in material_widgets:
                                    value = material_widgets['R3_entry'].get()
                                    other_params['R3'] = float(value) if value else 0
                            except:
                                pass
                            
                            # 保存IP地址和端口
                            try:
                                if 'ip_combo' in material_widgets:
                                    ip_value = material_widgets['ip_combo'].get()
                                    other_params['ip'] = ip_value if ip_value else "192.168.1.100"
                                elif 'ip_entry' in material_widgets:  # 兼容旧版本
                                    ip_value = material_widgets['ip_entry'].get()
                                    other_params['ip'] = ip_value if ip_value else "192.168.1.100"
                            except:
                                other_params['ip'] = "192.168.1.100"
                            
                            try:
                                if 'port_entry' in material_widgets:
                                    port_value = material_widgets['port_entry'].get()
                                    other_params['port'] = port_value if port_value else "8888"
                            except:
                                other_params['port'] = "8888"
                            
                            try:
                                if 'C1_entry' in material_widgets:
                                    value = material_widgets['C1_entry'].get()
                                    other_params['C1'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'C2_entry' in material_widgets:
                                    value = material_widgets['C2_entry'].get()
                                    other_params['C2'] = float(value) if value else 0
                            except:
                                pass
                            
                            try:
                                if 'C3_entry' in material_widgets:
                                    value = material_widgets['C3_entry'].get()
                                    other_params['C3'] = float(value) if value else 0
                            except:
                                pass
                        
                        print(f"从material_widgets收集到的参数: {other_params}")
                    else:
                        print("未找到工艺参数框架")
                    
                    print(f"最终工艺配置数据: {process_config_data}")
                    print("=== 工艺配置数据收集完成 ===")
                    
                    # 保存到工艺配置数据结构
                    material_config_key = getattr(material_frame, 'material_id', f'material_{i}')
                    
                    # 从other_params中提取IP和端口到根级别
                    ip_value = other_params.pop('ip', '192.168.1.100')
                    port_value = other_params.pop('port', '8888')
                    
                    process_config_data[material_config_key] = {
                        'type': material_name.split('(')[0].strip() if '(' in material_name else material_name,
                        'weight': material_name.split('(')[1].split('g')[0].strip() + 'g' if '(' in material_name and 'g)' in material_name else '0g',
                        'process_type': process_type,
                        'stages': stages_data,
                        'ip': ip_value,
                        'port': port_value,
                        'other_params': other_params
                    }
                    
                    print(f"保存物料配置: {material_config_key} -> {process_config_data[material_config_key]}")
                else:
                    print("未找到工艺类型combobox")
            
            print(f"最终工艺配置数据: {process_config_data}")
            print("=== 工艺配置数据收集完成 ===")
            
            # 将工艺配置保存到配方数据中
            try:
                # 更新配方数据中的工艺配置
                recipe_data['process_config'] = process_config_data
                
                # 保存配方数据到文件，优先保存到原始文件
                if hasattr(process_window, 'original_filepath') and process_window.original_filepath:
                    self.save_recipe_data(recipe_name=process_window.recipe_name, original_filepath=process_window.original_filepath)
                else:
                    self.save_recipe_data()
                
                # 保存后重新加载recipe_data确保数据同步
                self.load_recipe_data()
                
                self.log(f"工艺配置已保存到配方 '{process_window.recipe_name}' 中")
                messagebox.showinfo("保存成功", f"工艺配置已保存到配方 '{process_window.recipe_name}' 中")
                
            except Exception as e:
                self.log(f"保存工艺配置失败: {str(e)}")
                messagebox.showerror("保存失败", f"保存工艺配置时出错:{str(e)}")
            
            # 注释掉关闭窗体的调用，保存后保持窗体打开
            # close_process_window()
        
        ttk.Button(btn_frame, text="保存", command=save_process_config).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="取消", command=close_process_window).pack(side=tk.RIGHT, padx=10)
        
        # 绑定窗口关闭事件
        process_window.protocol("WM_DELETE_WINDOW", close_process_window)
        
        # 设置焦点管理
        process_window.grab_set()  # 模态窗口，阻止其他窗口操作
        process_window.focus_set()  # 设置焦点到工艺配置窗口
        
        # 延迟设置焦点，确保窗口完全显示后再设置
        process_window.after(100, lambda: process_window.focus_force())

    
    def show_help(self):
        """显示使用说明"""
        help_text = """实验室无人称重平台使用说明

1. 网络连接
   - 输入设备IP地址和端口号
   - 点击"连接"按钮建立连接

2. 设备控制
   - 步进电机控制：设置角度、速度、延时等参数
   - 蠕动泵控制：设置旋转角度、方向，启动/停止
   - 运动设备控制：设置目标位置，开始/完成运动

3. 通信日志
   - 实时显示发送和接收的数据
   - 便于调试和监控设备状态

4. 菜单功能
   - 文件：登录、退出
   - 设置：连接设置、设备配置、界面主题
   - 帮助：使用说明、关于信息

技术支持：请联系系统管理员"""

        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("500x400")
        help_window.resizable(True, True)
        help_window.transient(self.root)

        # 居中显示
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() - help_window.winfo_width()) // 2
        y = (help_window.winfo_screenheight() - help_window.winfo_height()) // 2
        help_window.geometry(f"+{x}+{y}")

        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
    def show_about(self):
        """显示关于信息"""
        about_text = """实验室无人称重平台

版本：1.0.0
开发团队：实验室自动化小组

功能描述：
- 多设备远程控制
- 实时数据监控
- 自动化称重流程
- 设备状态管理

技术支持：
- 邮箱：support@lab-automation.com
- 电话：400-123-4567

© 2024 实验室自动化小组 版权所有"""

        messagebox.showinfo("关于", about_text)
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 设备控制选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # ==============================
        # 工艺控制页面（新增，在最左边）
        # ==============================
        self.process_control_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.process_control_frame, text="工艺控制")
        
        # 创建工艺控制 Tab 的内容
        self.create_process_control_tab()

        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # 🔧 在“工艺控制”页底部添加 AGV 控制区域
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        agv_frame = ttk.LabelFrame(self.process_control_frame, text="AGV 物料转运控制", padding=(10, 5))
        agv_frame.pack(fill='x', padx=10, pady=(20, 10), side=tk.BOTTOM)

        ttk.Button(
            agv_frame,
            text="🚀 启动完整物料转运工艺",
            command=self.start_agv_workflow_threaded,  # 使用线程包装函数
            width=30
        ).pack(pady=5)

        # ==============================
        # 日志区域（放在 Notebook 下方）
        # ==============================
        log_frame = ttk.LabelFrame(main_frame, text="通信日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def create_process_control_tab(self):
        """创建工艺控制TAB页面"""
        # 标题
        title_label = ttk.Label(self.process_control_frame, text="工艺控制面板", font=self.font_large_bold)
        title_label.pack(pady=20)
        
        # 配方选择区域
        recipe_frame = ttk.LabelFrame(self.process_control_frame, text="配方选择", padding="10")
        recipe_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 配方列表
        recipe_list_frame = ttk.Frame(recipe_frame)
        recipe_list_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(recipe_list_frame, text="选择配方:").pack(side=tk.LEFT, padx=5)
        
        self.recipe_combo = ttk.Combobox(recipe_list_frame, width=20, state="readonly")
        self.recipe_combo.pack(side=tk.LEFT, padx=5)
        
        # 刷新配方列表按钮
        ttk.Button(recipe_list_frame, text="刷新", command=self.refresh_recipe_list).pack(side=tk.LEFT, padx=5)
        
        # 初始化配方列表
        self.refresh_recipe_list()
 
        # 工艺控制区域
        control_frame = ttk.LabelFrame(self.process_control_frame, text="工艺控制", padding="10")
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10)
        
        # 启动工艺按钮
        self.start_control_btn = ttk.Button(
            button_frame, 
            text="启动工艺", 
            command=self.start_recipe_process,
            width=15,
            style="Accent.TButton"
        )
        self.start_control_btn.pack(side=tk.LEFT, padx=10)
        
        # 停止工艺按钮
        self.stop_control_btn = ttk.Button(
            button_frame, 
            text="停止工艺", 
            command=self.stop_recipe_process,
            width=15
        )
        self.stop_control_btn.pack(side=tk.LEFT, padx=10)
        
        # 工艺状态显示区域
        status_frame = ttk.LabelFrame(self.process_control_frame, text="工艺状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 状态文本
        self.control_status_var = tk.StringVar(value="工艺未启动")
        status_label = ttk.Label(status_frame, textvariable=self.control_status_var, font=self.font_large)
        status_label.pack(pady=10)
        
        # 进度条
        self.control_progress = ttk.Progressbar(status_frame, mode='determinate')
        self.control_progress.pack(fill=tk.X, pady=10)
        
        # 当前步骤显示
        self.current_step_var = tk.StringVar(value="等待启动...")
        current_step_label = ttk.Label(status_frame, textvariable=self.current_step_var, font=self.font_normal)
        current_step_label.pack(pady=5)
        
        # 初始化配方列表
        self.refresh_recipe_list()
        
        # 初始化按钮状态
        self.stop_control_btn.config(state=tk.DISABLED)
    def refresh_recipe_list(self):
        """刷新配方列表"""
        if hasattr(self, 'recipe_combo') and hasattr(self, 'recipe_data'):
            # 获取所有配方名称
            recipe_names = [recipe.get('name', name) for name, recipe in self.recipe_data.items()]
            self.recipe_combo['values'] = recipe_names
            if recipe_names:
                self.recipe_combo.current(0)

    def configure_selected_recipe(self):
        """配置选中的配方"""
        selected_recipe = self.recipe_combo.get()
        if not selected_recipe:
            messagebox.showwarning("选择错误", "请先选择一个配方")
            return
        
        # 调用现有的工艺配置函数
        # 这里需要创建一个模拟的listbox或者修改configure_process函数
        self.log(f"开始配置配方: {selected_recipe}")
        messagebox.showinfo("工艺配置", f"开始配置配方: {selected_recipe}")
    def connect(self,ip,port):
        """连接到泵控制器服务器"""
        try:
            print(f"正在连接到泵控制器: {ip}:{port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, int(port)))
            print(f"已连接到泵控制器: {ip}:{port}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            print("连接已关闭")
    def send_pump_stopcommand(self):
        if not self.socket:
            print("未连接到服务器")
            return None
        try:
            # 生成时间戳
            timestamp = int(time.time())
            
            # 构建命令字符串
            cmd_idendifier = "STOP"
            command = f"[{timestamp}:{cmd_idendifier}]"
            
            # 发送命令
            self.socket.send(command.encode('utf-8'))
            print(f"发送命令: {command}")
            response = self.socket.recv(1024).decode('utf-8')
            print(f"服务器响应: {response}")
            return response
            
        except Exception as e:
            print(f"发送命令失败: {e}")
            return None
    def send_weight_command(self, target_weight, actual_weight,speed,direction):
        """
        发送重量控制命令
        
        Args:
            target_weight: 目标重量 (g)
            actual_weight: 实际重量 (g)
            
        Returns:
            str: 服务器响应
        """
        if not self.socket:
            print("未连接到服务器")
            return None
        
        try:
            # 生成时间戳
            timestamp = int(time.time())
            
            # 构建命令字符串
            command = f"[{timestamp}:{target_weight:.2f}:{actual_weight:.2f}:{speed}:{direction}]"
            
            # 发送命令
            self.socket.send(command.encode('utf-8'))
            print(f"发送命令: {command}")
            
            # 接收响应
            response = self.socket.recv(1024).decode('utf-8')
            print(f"服务器响应: {response}")
            
            return response
            
        except Exception as e:
            print(f"发送命令失败: {e}")
            return None
    def start_recipe_process(self):
        """启动配方工艺流程"""
        selected_recipe = self.recipe_combo.get()
        if not selected_recipe:
            self.log("错误：未选择配方")
            messagebox.showwarning("选择错误", "请先选择一个配方")
            return
        
        if 2>1 :
            print(f"开始启动配方工艺流程: {selected_recipe}")
            self.control_status_var.set("工艺运行中...")
            self.current_step_var.set("正在初始化...")
            print("工艺状态已更新：正在初始化")
            
            # 启动进度条
            self.control_progress['value'] = 0
            
            # 更新按钮状态
            self.start_control_btn.config(state=tk.DISABLED)
            self.stop_control_btn.config(state=tk.NORMAL)
            
            # 检查配方是否存在
            if not hasattr(self, 'recipe_data') or selected_recipe not in self.recipe_data:
                print(f"错误：未找到配方 '{selected_recipe}' 的数据")
                messagebox.showerror("错误", f"未找到配方 '{selected_recipe}' 的数据")
                return
            
            recipe_data = self.recipe_data[selected_recipe]
            print(f"找到配方数据：{selected_recipe}")
            
            # 检查配方是否有工艺配置
            if 'process_config' not in recipe_data or not recipe_data['process_config']:
                print(f"错误：配方 '{selected_recipe}' 没有配置工艺参数")
                messagebox.showerror("错误", f"配方 '{selected_recipe}' 没有配置工艺参数")
                return

            print(f"配方 '{selected_recipe}' 有工艺配置，开始处理")

            # 处理每个物料的工艺配置
            process_config = recipe_data['process_config']
            print(process_config)
            # 遍历所有物料配置
            for material_key in process_config:
                # 跳过非物料字段
                if material_key in ['process_config_saved', 'last_modified']:
                    continue
                print(f"处理物料 {material_key} 的工艺配置")   
                # 从recipe_data结构中用material_key作为索引获取对应的工艺配置
                if material_key not in process_config:
                    print(f"错误：物料 {material_key} 在配方数据中不存在")
                    continue

                # 获取工艺类型
                process_type = recipe_data['process_config'][material_key].get('process_type')
                ip = recipe_data['process_config'][material_key].get('ip')
                print(ip)
                print(type(ip))
                port = recipe_data['process_config'][material_key].get('port')
                print(port)
                print(type(port))
                # 从recipe_data中用material_key作为索引获取对应的工艺配置
                self.connect(ip, port)
                print(f"物料 {material_key} 要访问的IP和端口：{ip}:{port} process_type:{process_type}")
                # 获取其他参数
                other_params = recipe_data['process_config'][material_key].get('other_params', {})
                # 获取目标出料量（单位：克）
                target_output = float(other_params.get('target_output', 0))

                # >>> 新增：如果目标重量 > 0g，则发送去皮指令 <<<
                if target_output > 0:
                    try:
                        # 确保已连接到该物料对应的设备
                        ip = recipe_data['process_config'][material_key].get('ip', '192.168.1.100')
                        port = recipe_data['process_config'][material_key].get('port', '8888')
                        self.connect(ip, port)  # 如果已连，可加判断避免重复连接

                        # 构造去皮命令（格式需与设备协议一致）
                        timestamp = int(time.time())
                        tare_command = f"[{timestamp}:TARE]"
                        
                        self.socket.send(tare_command.encode('utf-8'))
                        print(f"✅ 已发送去皮指令: {tare_command} 到 {ip}:{port}")
                        
                        # 可选：等待设备响应（防止命令丢失）
                        time.sleep(0.3)
                        
                    except Exception as e:
                        error_msg = f"❌ 物料 {material_key} 去皮失败: {str(e)}"
                        print(error_msg)
                        self.log(error_msg)
                        messagebox.showwarning("去皮警告", f"物料去皮失败，请检查设备连接。\n{e}")
                # <<< 新增结束 >>>


                print(process_type)
                # 根据工艺类型计算控制点
                if process_type in ['固态供料','液态供料','胶体供料']:
                    # 获取参数值
                    n = float(other_params.get('target_output', 0))
                    A2 = float(other_params.get('A2'))
                    A3 = float(other_params.get('A3'))
                    C1 = float(other_params.get('C1'))
                    C2 = float(other_params.get('C2'))
                    C3 = float(other_params.get('C3'))
                    R1 = float(other_params.get('R1'))
                    R2 = float(other_params.get('R2'))
                    R3 = float(other_params.get('R3'))
                    # 计算控制点（参考工艺配置窗体中的计算方式）
                    A1 = n - A2 - A3
                    high_speed_point = A1 - C1
                    mid_speed_point = n - A3 - C2
                    low_speed_point = n - C3
                    print(f"物料 {material_key} 计算的控制点：{high_speed_point:.2f}, {mid_speed_point:.2f}, {low_speed_point:.2f}")
                    # 验证控制点
                    if high_speed_point < 0 or mid_speed_point < 0 or low_speed_point < 0:
                        print(f"物料 {material_key} 控制点计算错误：控制点不能为负数")
                        continue

                    # 构造控制命令（参考蠕动泵控制格式）
                    # 命令格式：P,<物料ID>,<工艺类型>,<高速点>,<中速点>,<低速点>
                    actual_weight = 0.0
                    target_weight = high_speed_point
                    while actual_weight<target_weight: 
                        actual_weight+=10
                        response = self.send_weight_command(target_weight, actual_weight,R1,1)

                        if response and "ERROR" in response:
                            print("⚠️  命令执行错误")

                        time.sleep(3)
                    target_weight = mid_speed_point    
                    while actual_weight<target_weight: 
                        actual_weight+=10
                        response = self.send_weight_command(target_weight, actual_weight,R2,1)

                        if response and "ERROR" in response:
                            print("⚠️  命令执行错误")
                        time.sleep(3)
                    target_weight = low_speed_point
                    while actual_weight<target_weight: 
                        actual_weight+=10
                        response = self.send_weight_command(target_weight, actual_weight,R3,1)
                        if response and "ERROR" in response:
                            print("⚠️  命令执行错误")

                        time.sleep(3)
                # 更新状态显示
                self.current_step_var.set(f"正在处理物料: {material_key}")

            messagebox.showinfo("工艺控制", f"配方 '{selected_recipe}' 工艺流程已启动")
            


    def stop_recipe_process(self):
        """停止配方工艺流程"""
        try:
            print("停止工艺流程")
            self.control_status_var.set("工艺已停止")
            self.current_step_var.set("工艺流程已停止")
            
            # 重置进度条
            self.control_progress['value'] = 0
            self.send_pump_stopcommand()
            
            # 更新按钮状态
            self.start_control_btn.config(state=tk.NORMAL, text="启动工艺")
            self.start_control_btn.config(command=self.start_recipe_process)
            self.stop_control_btn.config(state=tk.DISABLED)

            messagebox.showinfo("工艺控制", "工艺流程已停止")

        except Exception as e:
            print(f"停止工艺流程失败: {str(e)}")
            messagebox.showerror("错误", f"停止工艺流程失败: {str(e)}")

   

    
   

    def disconnect(self):
        if self.connected and self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                print(f"断开连接时出错: {str(e)}")

            self.connected = False
            # 清空设备连接状态
            self.connected_devices.clear()
            self.device_connection_times.clear()
            self.status_var.set("未连接")
            self.connect_btn.config(text="连接所有设备")
            print("已断开连接")

    def update_connection_status(self):
        """更新连接状态显示"""
        if not self.connected:
            self.status_var.set("未连接")
            return
            
        # 获取配置中的设备总数
        total_devices = len(self.config_data.get('devices', []))
        
        if total_devices == 0:
            self.status_var.set("已连接（无设备配置）")
            return
            
        # 计算最近5秒内连接的设备数量（去重）
        current_time = datetime.now()
        recent_connected_ips = set()
        
        for device_ip, connect_time in self.device_connection_times.items():
            if (current_time - connect_time).total_seconds() <= 5:
                recent_connected_ips.add(device_ip)
        
        recent_connected = len(recent_connected_ips)
        
        # 更新状态显示
        if recent_connected == total_devices:
            self.status_var.set("所有设备已就绪")
        else:
            self.status_var.set(f"已连接（近5s已连接{recent_connected}/{total_devices}设备）")

    

    

    def send_data(self, data):
        if not self.connected:
            messagebox.showwarning("未连接", "请先连接到服务器")
            return False

        try:
            self.client_socket.sendall(f"{data}\n".encode('utf-8'))
            print(f"发送: {data}")
            return True
        except Exception as e:
            print(f"发送失败: {str(e)}")
            messagebox.showerror("发送错误", f"发送数据失败: {str(e)}")
            return False
    
    def log(self, message):
        """在日志区域显示消息"""
        # 检查log_text是否已创建
        if hasattr(self, 'log_text') and self.log_text :
            self.log_text .config(state=tk.NORMAL)
            timestamp = time.strftime("%H:%M:%S")
            self.log_text .insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text .see(tk.END)  # 滚动到最后
            self.log_text .config(state=tk.DISABLED)
        else:
            # 如果log_text尚未创建，只打印到控制台
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    # 步进电机控制命令
   
    # 蠕动泵控制命令
    

    def update_recipe_list_display(self):
        """更新配方列表显示"""
        if hasattr(self, 'recipe_listbox') and self.recipe_listbox:
            self.recipe_listbox.delete(0, tk.END)
            if hasattr(self, 'recipe_data') and self.recipe_data:
                for recipe_key, recipe_data in self.recipe_data.items():
                    # 显示格式：配方名-时间戳
                    display_name = f"{recipe_data.get('name', recipe_key)}-{recipe_data.get('create_date', '未知时间')}"
                    self.recipe_listbox.insert(tk.END, display_name)
    def edit_selected_recipe(self, recipe_listbox, update_callback):
        """编辑选中的配方"""
        selected_index = recipe_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("编辑配方", "请先选择一个配方")
            return
        
        recipe_display_name = recipe_listbox.get(selected_index[0])
        recipe_name = recipe_display_name.split('-')[0]
        
        if not hasattr(self, 'recipe_data') or recipe_name not in self.recipe_data:
            messagebox.showwarning("编辑配方", "未找到选中的配方")
            return
        
        recipe_data = self.recipe_data[recipe_name]
        
        # 创建编辑配方窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑配方 - {recipe_name}")
        edit_window.geometry("700x600")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 居中显示
        edit_window.update_idletasks()
        x = (edit_window.winfo_screenwidth() - edit_window.winfo_width()) // 2
        y = (edit_window.winfo_screenheight() - edit_window.winfo_height()) // 2
        edit_window.geometry(f"+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(edit_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 基本信息框架
        basic_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="10")
        basic_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E)
        
        # 配方名称
        ttk.Label(basic_frame, text="配方名称:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        name_var = tk.StringVar(value=recipe_data.get('name', recipe_name))
        name_entry = ttk.Entry(basic_frame, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W+tk.E)
        
        # 配方描述框架
        desc_frame = ttk.LabelFrame(main_frame, text="配方描述", padding="10")
        desc_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E+tk.N+tk.S)
        
        description_text = tk.Text(desc_frame, width=50, height=4)
        description_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        description_text.insert("1.0", recipe_data.get('description', ''))
        
        # 物料配置框架
        materials_frame = ttk.LabelFrame(main_frame, text="物料配置", padding="10")
        materials_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # 物料列表容器
        materials_container = ttk.Frame(materials_frame)
        materials_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 存储物料行的列表
        material_rows = []
        
        def add_material_row(material_data=None):
            """添加物料行"""
            row_frame = ttk.Frame(materials_container)
            row_frame.pack(fill=tk.X, pady=2)
            
            # 物料类型
            material_type_var = tk.StringVar()
            material_type_combo = ttk.Combobox(row_frame, textvariable=material_type_var, width=12, state="readonly")
            material_type_combo['values'] = ('水泥', '水', '添加剂A', '添加剂B', '添加剂C')
            material_type_combo.pack(side=tk.LEFT, padx=5)
            
            # 重量
            weight_var = tk.StringVar()
            weight_entry = ttk.Entry(row_frame, textvariable=weight_var, width=10)
            weight_entry.pack(side=tk.LEFT, padx=5)
            
            # 单位
            ttk.Label(row_frame, text="g").pack(side=tk.LEFT, padx=5)
            
            # 设置默认值或加载数据
            if material_data:
                material_type_var.set(material_data.get('type', '水泥'))
                weight_var.set(material_data.get('weight', '100'))
            else:
                material_type_combo.current(0)
                weight_entry.insert(0, "100")
            
            # 删除按钮
            def remove_row():
                row_frame.destroy()
                material_rows.remove((material_type_var, weight_var, row_frame))
            
            remove_btn = ttk.Button(row_frame, text="删除", command=remove_row, width=6)
            remove_btn.pack(side=tk.LEFT, padx=5)
            
            material_rows.append((material_type_var, weight_var, row_frame))
        
        # 添加物料按钮
        add_btn_frame = ttk.Frame(materials_frame)
        add_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(add_btn_frame, text="添加物料", command=lambda: add_material_row()).pack(side=tk.LEFT, padx=5)
        
        # 加载原有的物料数据
        if 'materials' in recipe_data and recipe_data['materials']:
            for material in recipe_data['materials']:
                add_material_row(material)
        else:
            # 如果没有物料，添加一个空行
            add_material_row()
        
        # 创建日期（只读显示）
        ttk.Label(main_frame, text="创建日期:").grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        create_date_var = tk.StringVar(value=recipe_data.get('create_date', '未知'))
        create_date_label = ttk.Label(main_frame, textvariable=create_date_var)
        create_date_label.grid(row=3, column=1, padx=5, pady=10, sticky=tk.W)
        
        # 最后修改日期（只读显示）
        ttk.Label(main_frame, text="最后修改:").grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)
        modify_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        modify_date_label = ttk.Label(main_frame, textvariable=modify_date_var)
        modify_date_label.grid(row=4, column=1, padx=5, pady=10, sticky=tk.W)
        
        def save_edited_recipe():
            """保存编辑后的配方"""
            new_recipe_name = name_var.get().strip()
            description = description_text.get("1.0", tk.END).strip()
            
            # 验证输入
            if not new_recipe_name:
                messagebox.showwarning("输入错误", "配方名称不能为空")
                name_entry.focus_set()
                return
            
            if len(material_rows) == 0:
                messagebox.showwarning("输入错误", "请至少添加一种物料")
                return
            
            # 收集物料数据
            materials_data = []
            for material_type_var, weight_var, _ in material_rows:
                material_type = material_type_var.get()
                weight = weight_var.get().strip()
                
                if not material_type:
                    messagebox.showwarning("输入错误", "请选择物料类型")
                    return
                
                if not weight:
                    messagebox.showwarning("输入错误", "请输入物料重量")
                    return
                
                materials_data.append({
                    'type': material_type,
                    'weight': weight
                })
            
            # 更新配方数据
            updated_recipe_data = {
                'name': new_recipe_name,
                'description': description,
                'materials': materials_data,
                'create_date': recipe_data.get('create_date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                'last_modified': modify_date_var.get()
            }
            
            # 如果配方名称改变了，需要删除旧的并添加新的
            if new_recipe_name != recipe_name:
                if recipe_name in self.recipe_data:
                    del self.recipe_data[recipe_name]
            
            self.recipe_data[new_recipe_name] = updated_recipe_data
            
            # 调用回调函数更新列表
            if update_callback:
                update_callback()
            
            # 更新工艺控制页面的配方列表
            if hasattr(self, 'recipe_combo'):
                self.refresh_recipe_list()
            
            print(f"编辑配方: {recipe_name} -> {new_recipe_name}")
            messagebox.showinfo("保存成功", f"配方 '{new_recipe_name}' 修改成功")
            edit_window.destroy()
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="保存", command=save_edited_recipe, width=10).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy, width=10).pack(side=tk.RIGHT, padx=10)
        
        # 设置焦点
        name_entry.focus_set()
    def delete_selected_recipe(self, recipe_listbox, update_callback):
        """删除选中的配方"""
        selected_index = recipe_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("删除配方", "请先选择一个配方")
            return
        
        recipe_display_name = recipe_listbox.get(selected_index[0])
        recipe_name = recipe_display_name.split('-')[0]
        
        if messagebox.askyesno("删除配方", f"确定要删除配方 '{recipe_name}' 吗？"):
            if hasattr(self, 'recipe_data') and recipe_name in self.recipe_data:
                del self.recipe_data[recipe_name]
                update_callback()
                # 更新工艺控制页面的配方列表
                if hasattr(self, 'recipe_combo'):
                    self.refresh_recipe_list()

                messagebox.showinfo("删除配方", f"配方 '{recipe_name}' 已删除")
            else:
                messagebox.showwarning("删除配方", "未找到选中的配方")
    def on_close(self):
        self.disconnect()
        self.root.destroy()
if __name__ == "__main__":
    root = tk.Tk()
    app = DeviceController(root)
    root.mainloop()