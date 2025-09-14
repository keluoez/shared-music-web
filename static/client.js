// Web客户端P2P节点实现
class WebMusicPeer {
    constructor() {
        this.peerId = this.generatePeerId();
        this.peerPort = Math.floor(5000 + Math.random() * 1000); // 随机端口号
        this.centralHost = 'localhost';
        this.centralPort = 5000;
        this.sharedDir = 'shared_music';
        this.downloadDir = 'downloads';
        this.running = true;
        this.socket = null;
        this.webSocket = null;
        this.uploadingFiles = new Map(); // 存储正在上传的文件
        this.downloadingFiles = new Map(); // 存储正在下载的文件
        
        console.log(`Web节点初始化成功，ID: ${this.peerId}`);
        this.init();
    }
    
    generatePeerId() {
        return 'web_' + Math.random().toString(36).substr(2, 8);
    }
    
    async init() {
        try {
            // 初始化WebSocket连接
            this.initWebSocket();
            
            // 注册到中心服务器
            await this.registerWithCentralServer();
            
            // 定期更新节点状态
            this.startHeartbeat();
            
            console.log('Web节点初始化完成');
        } catch (error) {
            console.error('Web节点初始化失败:', error);
        }
    }
    
    initWebSocket() {
        // 在index.html中已经初始化了Socket.IO连接
        // 这里可以添加更多的WebSocket事件处理
    }
    
    async registerWithCentralServer() {
        try {
            const response = await fetch(`http://${this.centralHost}:${this.centralPort}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    peer_id: this.peerId,
                    peer_port: this.peerPort
                })
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                console.log('已成功注册到中心服务器');
            } else {
                console.error('注册到中心服务器失败:', data.message);
            }
        } catch (error) {
            console.error('注册到中心服务器时发生错误:', error);
            // 如果直接连接失败，尝试通过Web服务器转发
            this.registerViaWebServer();
        }
    }
    
    async registerViaWebServer() {
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    peer_id: this.peerId,
                    peer_port: this.peerPort
                })
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                console.log('通过Web服务器成功注册到中心服务器');
            } else {
                console.error('通过Web服务器注册失败:', data.message);
            }
        } catch (error) {
            console.error('通过Web服务器注册时发生错误:', error);
        }
    }
    
    startHeartbeat() {
        // 每30秒发送一次心跳包
        setInterval(() => {
            this.sendHeartbeat();
        }, 30000);
    }
    
    async sendHeartbeat() {
        try {
            await fetch('/api/heartbeat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    peer_id: this.peerId
                })
            });
        } catch (error) {
            console.error('发送心跳包失败:', error);
        }
    }
    
    async shareFile(file) {
        try {
            // 上传文件到服务器
            const formData = new FormData();
            formData.append('file', file);
            formData.append('peer_id', this.peerId);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                console.log(`文件 ${file.name} 共享成功`);
                return { success: true, message: data.message };
            } else {
                console.error(`文件 ${file.name} 共享失败:`, data.message);
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error(`文件 ${file.name} 共享时发生错误:`, error);
            return { success: false, message: error.message };
        }
    }
    
    async downloadFile(filename, peerAddress, onProgress) {
        try {
            // 检查是否已经在下载
            if (this.downloadingFiles.has(filename)) {
                return { success: false, message: '文件正在下载中' };
            }
            
            // 创建下载任务
            const downloadTask = {
                filename: filename,
                peerAddress: peerAddress,
                startTime: Date.now(),
                totalSize: 0,
                downloadedSize: 0
            };
            
            this.downloadingFiles.set(filename, downloadTask);
            
            // 通过Web服务器代理下载
            const response = await fetch(`/api/download?filename=${encodeURIComponent(filename)}&peer_ip=${peerAddress[0]}&peer_port=${peerAddress[1]}`);
            
            if (!response.ok) {
                throw new Error(`下载失败: HTTP ${response.status}`);
            }
            
            // 获取文件大小
            const contentLength = response.headers.get('content-length');
            downloadTask.totalSize = contentLength ? parseInt(contentLength) : 0;
            
            // 创建文件下载
            const blob = await response.blob();
            
            // 创建下载链接并触发下载
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // 更新进度为100%
            if (onProgress) {
                onProgress(100);
            }
            
            // 从下载列表中移除
            this.downloadingFiles.delete(filename);
            
            console.log(`文件 ${filename} 下载成功`);
            return { success: true, message: '下载成功' };
        } catch (error) {
            console.error(`文件 ${filename} 下载时发生错误:`, error);
            this.downloadingFiles.delete(filename);
            return { success: false, message: error.message };
        }
    }
    
    async searchFiles(keyword) {
        try {
            const response = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                return { success: true, results: data.results };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('搜索文件时发生错误:', error);
            return { success: false, message: error.message };
        }
    }
    
    async getAvailableFiles() {
        try {
            const response = await fetch('/api/files');
            const data = await response.json();
            
            if (data.status === 'success') {
                return { success: true, files: data.files };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('获取可用文件列表时发生错误:', error);
            return { success: false, message: error.message };
        }
    }
    
    async getActivePeers() {
        try {
            const response = await fetch('/api/peers');
            const data = await response.json();
            
            if (data.status === 'success') {
                return { success: true, peers: data.peers };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('获取活跃节点列表时发生错误:', error);
            return { success: false, message: error.message };
        }
    }
    
    async stop() {
        this.running = false;
        
        try {
            // 通知服务器节点下线
            await fetch('/api/unregister', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    peer_id: this.peerId
                })
            });
        } catch (error) {
            console.error('注销节点时发生错误:', error);
        }
        
        console.log('Web节点已停止');
    }
}

// 创建全局实例
let webMusicPeer = null;

// 初始化WebMusicPeer
function initWebMusicPeer() {
    if (!webMusicPeer) {
        webMusicPeer = new WebMusicPeer();
    }
    return webMusicPeer;
}

// 文件上传处理
async function handleFileUpload(files) {
    const peer = initWebMusicPeer();
    const results = [];
    
    for (const file of files) {
        // 检查文件类型
        if (!file.type.startsWith('audio/') && !['.mp3', '.wav', '.flac', '.m4a'].some(ext => file.name.toLowerCase().endsWith(ext))) {
            results.push({ file: file.name, success: false, message: '不支持的文件类型' });
            continue;
        }
        
        // 上传文件
        const result = await peer.shareFile(file);
        results.push({ file: file.name, ...result });
    }
    
    return results;
}

// 文件下载处理
async function handleFileDownload(filename, peerAddress, onProgress) {
    const peer = initWebMusicPeer();
    return await peer.downloadFile(filename, peerAddress, onProgress);
}

// 搜索文件处理
async function handleFileSearch(keyword) {
    const peer = initWebMusicPeer();
    return await peer.searchFiles(keyword);
}

// 刷新文件列表
async function refreshFileList() {
    const peer = initWebMusicPeer();
    return await peer.getAvailableFiles();
}

// 刷新节点列表
async function refreshPeerList() {
    const peer = initWebMusicPeer();
    return await peer.getActivePeers();
}

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (webMusicPeer) {
        webMusicPeer.stop();
    }
});

// 暴露全局函数到window对象
window.initWebMusicPeer = initWebMusicPeer;
window.handleFileUpload = handleFileUpload;
window.handleFileDownload = handleFileDownload;
window.handleFileSearch = handleFileSearch;
window.refreshFileList = refreshFileList;
window.refreshPeerList = refreshPeerList;