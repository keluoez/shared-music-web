# P2P音乐共享平台

一个基于Web的P2P音乐共享系统，支持节点管理、文件搜索、共享和下载功能。

## 功能特点

- 🌐 **去中心化架构**：基于P2P网络，没有中心服务器的单点故障问题
- 🔍 **实时搜索**：快速搜索网络中的音乐文件
- 📤 **文件共享**：轻松共享本地音乐文件到网络
- 📥 **文件下载**：从多个节点并行下载音乐文件
- 🎨 **精美界面**：现代化的Web界面，支持响应式设计
- 📊 **实时统计**：显示网络状态、节点数量和文件数量

## 技术栈

### 后端
- Python 3.x
- Flask - Web框架
- Flask-SocketIO - 实时通信
- Socket - 底层网络通信
- Threading - 多线程支持

### 前端
- HTML5, CSS3, JavaScript
- Tailwind CSS - UI框架
- Font Awesome - 图标库
- Chart.js - 数据可视化
- Socket.IO Client - 实时通信

## 项目结构

```
shared-music-web/
├── central_server.py       # 原始中心服务器实现
├── peer_node.py            # 原始P2P节点实现
├── web_server.py           # Web服务器（集成中心服务器功能）
├── requirements.txt        # 项目依赖
├── .gitignore              # Git忽略文件配置
├── templates/
│   └── index.html          # Web界面
├── static/
│   └── client.js           # Web客户端脚本
├── shared_music/           # 共享音乐目录
└── downloads/              # 下载目录
```

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-username/shared-music-web.git
cd shared-music-web
```

### 2. 安装依赖

```bash
# 使用pip安装依赖
pip install -r requirements.txt

# 或者使用虚拟环境
python -m venv venv
# Windows
env\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

## 使用方法

### 启动Web服务器

```bash
python web_server.py
```

Web服务器启动后，可以通过浏览器访问 `http://localhost:5001` 来使用系统。

### 功能使用

1. **搜索音乐**：在搜索框中输入关键词，点击搜索按钮查找音乐文件
2. **下载音乐**：在搜索结果或可下载文件列表中点击下载按钮
3. **共享音乐**：点击"添加文件"按钮选择本地音乐文件进行共享
4. **查看统计**：查看网络状态、活跃节点数和共享文件数的实时统计

## 系统架构

### 中心服务器

- 负责节点管理和资源索引
- 维护活跃节点列表和共享文件索引
- 处理节点注册、注销、文件共享和搜索请求

### Web服务器

- 提供Web界面，允许用户通过浏览器使用系统
- 集成了中心服务器的功能
- 使用Socket.IO实现实时通信
- 提供RESTful API接口

### Web客户端

- 通过浏览器访问系统
- 实现了文件搜索、共享和下载功能
- 实时显示网络状态和文件列表

## 注意事项

- 系统使用端口5000（中心服务器）和5001（Web服务器），请确保这些端口未被占用
- 共享的音乐文件将保存在`shared_music`目录中
- 下载的音乐文件将保存在`downloads`目录中
- 系统目前仅支持.mp3, .wav, .flac, .m4a等常见音乐格式
- 请遵守相关法律法规，不要共享盗版或受版权保护的音乐文件

## 开发说明

### 项目扩展方向

1. 实现更高效的P2P文件传输算法
2. 添加用户认证和权限管理
3. 实现文件分片传输和断点续传
4. 添加音乐播放功能
5. 优化Web界面和用户体验

### 贡献指南

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件

## 致谢

感谢所有为本项目做出贡献的开发者！