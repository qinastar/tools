# qBittorrent Batch Cleaner

一个用于批量清理 qBittorrent 种子的工具集。包含本地种子检查和远程种子删除功能。

## 功能特点

- 支持按标签和分类筛选目标种子
- 支持多服务器并行处理
- 完整的日志记录功能
- 支持调试模式预览

## 使用方法

### 1. 配置文件

在使用工具前，需要创建 `config.json` 配置文件：

```json
{
    "local_server": {
        "url": "http://localhost:8080",
        "username": "admin",
        "password": "adminadmin",
        "tag": "test",
        "category": ""
    },
    "remote_servers": [
        {
            "name": "Server1",
            "url": "http://server1:8080",
            "username": "admin",
            "password": "adminadmin"
        }
    ]
}
```

### 2. 检查本地种子

运行 `check_local_torrents.py` 来检查本地服务器中的种子：

```bash
python check_local_torrents.py
```

脚本会根据配置文件中的标签和分类筛选种子，并生成待删除种子列表文件 `torrents_to_delete.json`。

### 3. 删除远程种子

运行 `delete_remote_torrents.py` 来删除远程服务器中的种子：

```bash
# 调试模式（只检查不删除）
python delete_remote_torrents.py --debug

# 执行删除
python delete_remote_torrents.py
```

脚本会读取 `torrents_to_delete.json` 文件，并在远程服务器中查找和删除对应的种子。所有操作都会记录在 `logs` 目录下。

## 注意事项

1. 请在执行删除操作前，先使用调试模式确认要删除的种子
2. 确保配置文件中的服务器信息正确
3. 建议定期备份种子数据 