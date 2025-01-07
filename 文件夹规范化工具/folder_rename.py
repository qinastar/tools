import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os
import re

class FolderRenameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件夹规范化工具")
        self.root.geometry("800x600")
        
        # 设置样式
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", padding=5)
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 选择目录按钮
        self.select_btn = ttk.Button(main_frame, text="选择目录", command=self.select_directory)
        self.select_btn.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # 显示选中的目录路径
        self.path_var = tk.StringVar()
        self.path_label = ttk.Label(main_frame, textvariable=self.path_var)
        self.path_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 递归处理选项
        self.recursive_var = tk.BooleanVar(value=False)
        self.recursive_check = ttk.Checkbutton(
            main_frame, 
            text="递归处理子目录", 
            variable=self.recursive_var
        )
        self.recursive_check.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # 开始处理按钮
        self.process_btn = ttk.Button(main_frame, text="开始处理", command=self.process_directories)
        self.process_btn.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # 日志区域
        log_label = ttk.Label(main_frame, text="处理日志:")
        log_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(main_frame, width=80, height=20)
        self.log_area.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 视频文件扩展名
        self.video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
        
    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
            self.log_message(f"已选择目录: {directory}")
    
    def log_message(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
    
    def rename_directory(self, dir_path, dir_name):
        has_extension = False
        new_name = dir_name
        
        for ext in self.video_extensions:
            if dir_name.lower().endswith(ext):
                has_extension = True
                new_name = dir_name[:-len(ext)]
                break
        
        if has_extension:
            old_path = os.path.join(dir_path, dir_name)
            new_path = os.path.join(dir_path, new_name)
            
            try:
                os.rename(old_path, new_path)
                self.log_message(f"已重命名: {dir_name} -> {new_name}")
                return 1
            except Exception as e:
                self.log_message(f"重命名失败 {dir_name}: {str(e)}")
        return 0
    
    def process_directories(self):
        directory = self.path_var.get()
        if not directory:
            self.log_message("请先选择一个目录！")
            return
            
        self.log_message("开始处理文件夹...")
        count = 0
        
        if self.recursive_var.get():
            # 递归处理所有子目录
            for root, dirs, files in os.walk(directory):
                for dir_name in dirs[:]:  # 使用切片创建副本以避免修改迭代中的列表
                    count += self.rename_directory(root, dir_name)
        else:
            # 只处理当前目录
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir():
                        count += self.rename_directory(directory, entry.name)
        
        self.log_message(f"\n处理完成！共重命名 {count} 个文件夹。")

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderRenameApp(root)
    root.mainloop() 