from qbittorrentapi import Client
import json
import datetime
import os
import sys

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

def clean_old_files():
    """删除旧的种子列表文件"""
    try:
        if os.path.exists("torrents_to_delete.json"):
            os.remove("torrents_to_delete.json")
            print("已删除旧的种子列表文件")
    except Exception as e:
        print(f"删除旧文件时发生错误: {str(e)}")

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            # 验证配置文件格式
            if not isinstance(config, dict):
                raise ValueError("配置文件格式错误：根对象必须是字典类型")
            if "local_server" not in config:
                raise ValueError("配置文件缺少 'local_server' 配置")
            
            # 验证本地服务器配置
            local_config = config["local_server"]
            required_fields = ["url", "username", "password", "tag"]
            for field in required_fields:
                if field not in local_config:
                    raise ValueError(f"本地服务器配置缺少必要字段: {field}")
            
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件JSON格式错误: {str(e)}")
    except FileNotFoundError:
        raise FileNotFoundError("找不到配置文件 config.json")

def check_local_torrents():
    try:
        # 清理旧文件
        clean_old_files()
        
        # 加载配置
        config = load_config()
        local_config = config["local_server"]
        
        print(f"\n正在连接本地服务器: {local_config['url']}")
        
        # 连接本地 qBittorrent
        qb = Client(
            host=local_config["url"],
            username=local_config["username"],
            password=local_config["password"]
        )
        
        try:
            qb.auth_log_in()
            print("已成功连接到服务器")
            
            # 获取所有种子
            print("正在获取种子列表...")
            torrents = qb.torrents_info()
            
            # 筛选进度为0且满足条件的种子
            target_torrents = []
            total_size = 0
            
            for torrent in torrents:
                if (torrent.progress == 0 and 
                    local_config["tag"] in torrent.tags.split(",") and
                    (not local_config["category"] or torrent.category == local_config["category"])):
                    
                    target_torrents.append({
                        "name": torrent.name,
                        "hash": torrent.hash,
                        "size": torrent.size,
                        "category": torrent.category,
                        "tags": torrent.tags
                    })
                    total_size += torrent.size
            
            if target_torrents:
                # 将种子信息写入文件
                with open("torrents_to_delete.json", "w", encoding="utf-8") as f:
                    json.dump(target_torrents, f, ensure_ascii=False, indent=4)
                
                # 打印结果
                print(f"\n找到 {len(target_torrents)} 个符合条件的种子:")
                print(f"总大小: {format_size(total_size)}")
                print("\n种子列表:")
                for idx, torrent in enumerate(target_torrents, 1):
                    print(f"{idx}. {torrent['name']} (大小: {format_size(torrent['size'])})")
                    print(f"   标签: {torrent['tags']}")
                    if torrent['category']:
                        print(f"   分类: {torrent['category']}")
                
                print(f"\n种子列表已保存至: torrents_to_delete.json")
            else:
                print("\n未找到符合条件的种子")
            
        except Exception as e:
            print(f"处理种子时发生错误: {str(e)}")
        finally:
            qb.auth_log_out()
            
    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")

if __name__ == "__main__":
    check_local_torrents() 