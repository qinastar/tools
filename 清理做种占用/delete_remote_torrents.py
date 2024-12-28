from qbittorrentapi import Client
import json
import datetime
import os
import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置控制台输出编码为UTF-8
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def format_size(size_bytes):
    """将字节大小转换为人类可读的格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            if not isinstance(config, dict):
                raise ValueError("配置文件格式错误：根对象必须是字典类型")
            if "remote_servers" not in config:
                raise ValueError("配置文件缺少 'remote_servers' 配置")
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件JSON格式错误: {str(e)}")
    except FileNotFoundError:
        raise FileNotFoundError("找不到配置文件 config.json")

def create_log_directory():
    if not os.path.exists("logs"):
        os.makedirs("logs")

def get_log_filenames():
    log_file = "logs/delete_log.txt"
    json_file = "logs/delete_records.json"
    return log_file, json_file

def load_existing_records(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("records", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def process_server(server, torrents_to_delete, debug_mode, log_file, lock):
    """处理单个服务器的种子删除"""
    mode_str = "[调试模式]" if debug_mode else ""
    server_records = []
    server_found = 0
    server_size = 0
    action_str = "找到" if debug_mode else "删除"
    
    try:
        print(f"\n{mode_str}正在连接服务器 {server['name']}: {server['url']}")
        
        # 连接远程 qBittorrent
        qb = Client(
            host=server["url"],
            username=server["username"],
            password=server["password"]
        )
        
        try:
            qb.auth_log_in()
            with lock:
                print(f"已成功连接到服务器 {server['name']}")
            
            torrents = qb.torrents_info()
            with lock:
                print(f"正在检查服务器 {server['name']} 的种子...")
            
            # 创建要删除的种子名称集合
            target_names = set()
            for target in torrents_to_delete:
                target_names.add(target.get("name", "") if isinstance(target, dict) else target)
            
            # 检查/删除匹配的种子
            for torrent in torrents:
                if torrent.name in target_names:  # 使用集合来提高查找效率
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 在调试模式下只检查不删除
                    if not debug_mode:
                        qb.torrents_delete(delete_files=True, torrent_hashes=torrent.hash)
                        action = "deleted"
                    else:
                        action = "found"
                    
                    # 准备日志记录
                    log_entry = {
                        "timestamp": current_time,
                        "server_name": server["name"],
                        "torrent_name": torrent.name,
                        "torrent_hash": torrent.hash,
                        "torrent_size": torrent.size,
                        "action": action,
                        "debug_mode": debug_mode
                    }
                    
                    server_records.append(log_entry)
                    server_size += torrent.size
                    
                    # 打印和写入文本日志
                    size_str = format_size(torrent.size)
                    log_message = f"[{current_time}] {mode_str}服务器[{server['name']}] {action_str}种子: {torrent.name} (大小: {size_str})"
                    with lock:
                        print(log_message)
                    
                    if not debug_mode:
                        with lock:  # 使用锁来保护文件写入
                            with open(log_file, "a", encoding="utf-8") as f:
                                f.write(log_message + "\n")
                    
                    server_found += 1
            
            with lock:
                if server_found > 0:
                    print(f"在服务器 {server['name']} 上{action_str}了 {server_found} 个种子 (总大小: {format_size(server_size)})")
                else:
                    print(f"在服务器 {server['name']} 上未找到需要{action_str}的种子")
            
        except Exception as e:
            error_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_message = f"[{error_time}] {mode_str}处理服务器 {server['name']} 时发生错误: {str(e)}"
            with lock:
                print(error_message)
                if not debug_mode:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(error_message + "\n")
        finally:
            qb.auth_log_out()
            
    except Exception as e:
        with lock:
            print(f"连接服务器 {server['name']} 时发生错误: {str(e)}")
    
    return server_records, server_found, server_size

def delete_remote_torrents(debug_mode=False):
    create_log_directory()
    log_file, json_file = get_log_filenames()
    
    try:
        # 加载现有记录
        existing_records = load_existing_records(json_file)
        deletion_records = existing_records
        
        # 读取要删除的种子列表
        try:
            with open("torrents_to_delete.json", "r", encoding="utf-8") as f:
                torrents_to_delete = json.load(f)
                if not isinstance(torrents_to_delete, list):
                    raise ValueError("torrents_to_delete.json 格式错误：必须是数组类型")
        except FileNotFoundError:
            print("未找到要删除的种子列表文件")
            return
        except json.JSONDecodeError as e:
            print(f"种子列表文件JSON格式错误: {str(e)}")
            return
        
        # 加载配置
        config = load_config()
        remote_servers = config["remote_servers"]
        
        mode_str = "[调试模式]" if debug_mode else ""
        total_found = 0
        total_size = 0
        action_str = "找到" if debug_mode else "删除"
        
        # 创建线程锁
        lock = threading.Lock()
        
        # 使用线程池同时处理多个服务器
        with ThreadPoolExecutor(max_workers=len(remote_servers)) as executor:
            # 提交所有任务
            future_to_server = {
                executor.submit(
                    process_server, server, torrents_to_delete, debug_mode, log_file, lock
                ): server for server in remote_servers
            }
            
            # 收集结果
            for future in as_completed(future_to_server):
                server = future_to_server[future]
                try:
                    server_records, server_found, server_size = future.result()
                    if not debug_mode:
                        deletion_records.extend(server_records)
                    total_found += server_found
                    total_size += server_size
                except Exception as e:
                    with lock:
                        print(f"处理服务器 {server['name']} 时发生错误: {str(e)}")
        
        # 打印总结
        print(f"\n=== 总结 ===")
        print(f"所有服务器共{action_str}了 {total_found} 个种子")
        print(f"总大小: {format_size(total_size)}")
        
        # 只在非调试模式���更新JSON记录
        if not debug_mode and total_found > 0:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump({
                    "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_records": len(deletion_records),
                    "records": deletion_records
                }, f, ensure_ascii=False, indent=4)
            
            print(f"日志已更新至: {log_file}")
            print(f"JSON记录已更新至: {json_file}")
        elif debug_mode:
            print(f"\n调试模式检查完成！未执行任何删除操作")
            
    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='远程种子删除工具')
    parser.add_argument('--debug', '-d', action='store_true', help='启用调试模式（只检查不删除）')
    args = parser.parse_args()
    
    delete_remote_torrents(debug_mode=args.debug) 