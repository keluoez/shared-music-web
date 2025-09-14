import socket
import threading
import json
import os
import uuid
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room

class CentralServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.peers = {}  # 存储节点信息: {peer_id: (ip, port)}
        self.shared_files = {}  # 存储共享文件: {filename: [peer_id1, peer_id2...]}
        print(f"中心服务器启动在 {self.host}:{self.port}")

    def handle_client(self, client_socket, client_address):
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                response = self.process_message(message, client_address)
                client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"处理客户端 {client_address} 时出错: {e}")
        finally:
            # 客户端断开连接时，移除其注册的信息
            peer_id_to_remove = None
            for peer_id, addr in self.peers.items():
                if addr == client_address:
                    peer_id_to_remove = peer_id
                    break
            
            if peer_id_to_remove:
                del self.peers[peer_id_to_remove]
                # 从共享文件列表中移除该节点的文件
                for filename in list(self.shared_files.keys()):
                    if peer_id_to_remove in self.shared_files[filename]:
                        self.shared_files[filename].remove(peer_id_to_remove)
                        if not self.shared_files[filename]:
                            del self.shared_files[filename]
                print(f"节点 {peer_id_to_remove} 已断开连接")
                # 通过WebSocket广播文件列表更新
                socketio.emit('file_list_updated', {'files': list(self.shared_files.keys())}, namespace='/music')
            
            client_socket.close()

    def process_message(self, message, client_address):
        command = message.get('command')
        
        if command == 'register':
            peer_id = message.get('peer_id')
            peer_port = message.get('peer_port')
            self.peers[peer_id] = (client_address[0], peer_port)
            print(f"节点 {peer_id} 已注册: {client_address[0]}:{peer_port}")
            return {'status': 'success', 'message': '注册成功'}
        
        elif command == 'share':
            peer_id = message.get('peer_id')
            files = message.get('files', [])
            for file in files:
                if file not in self.shared_files:
                    self.shared_files[file] = []
                if peer_id not in self.shared_files[file]:
                    self.shared_files[file].append(peer_id)
            print(f"节点 {peer_id} 共享了 {len(files)} 个文件")
            # 通过WebSocket广播文件列表更新
            socketio.emit('file_list_updated', {'files': list(self.shared_files.keys())}, namespace='/music')
            return {'status': 'success', 'message': f'共享了 {len(files)} 个文件'}
        
        elif command == 'search':
            keyword = message.get('keyword', '').lower()
            results = {}  # 存储搜索结果
            for filename, peers in self.shared_files.items():
                if keyword in filename.lower():
                    # 将peer_id转换为实际的IP和端口
                    results[filename] = [self.peers[peer_id] for peer_id in peers]
            return {'status': 'success', 'results': results}
        
        elif command == 'get_peers':
            return {'status': 'success', 'peers': list(self.peers.items())}
        
        else:
            return {'status': 'error', 'message': '未知命令'}

    def start(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"新连接: {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            client_thread.start()

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# 实例化中心服务器
central_server = CentralServer()

# 存储Web客户端的连接信息
web_clients = {}

# 确保目录存在
def ensure_directories():
    if not os.path.exists('shared_music'):
        os.makedirs('shared_music')
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

# Web路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    keyword = request.args.get('keyword', '').lower()
    results = {}
    for filename, peers in central_server.shared_files.items():
        if keyword in filename.lower():
            results[filename] = [central_server.peers[peer_id] for peer_id in peers]
    return jsonify({'status': 'success', 'results': results})

@app.route('/api/files')
def api_files():
    return jsonify({'status': 'success', 'files': list(central_server.shared_files.keys())})

@app.route('/api/peers')
def api_peers():
    return jsonify({'status': 'success', 'peers': list(central_server.peers.items())})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    peer_id = data.get('peer_id')
    peer_port = data.get('peer_port')
    
    # 对于Web客户端，我们使用Web服务器的IP和一个随机端口
    client_ip = request.remote_addr
    central_server.peers[peer_id] = (client_ip, peer_port)
    
    print(f"Web客户端 {peer_id} 已注册: {client_ip}:{peer_port}")
    
    # 广播节点列表更新
    socketio.emit('peer_list_updated', {'peers': list(central_server.peers.items())}, namespace='/music')
    
    return jsonify({'status': 'success', 'message': '注册成功'})

@app.route('/api/unregister', methods=['POST'])
def api_unregister():
    data = request.json
    peer_id = data.get('peer_id')
    
    if peer_id in central_server.peers:
        del central_server.peers[peer_id]
        # 从共享文件列表中移除该节点的文件
        for filename in list(central_server.shared_files.keys()):
            if peer_id in central_server.shared_files[filename]:
                central_server.shared_files[filename].remove(peer_id)
                if not central_server.shared_files[filename]:
                    del central_server.shared_files[filename]
        
        print(f"Web客户端 {peer_id} 已注销")
        
        # 广播更新
        socketio.emit('peer_list_updated', {'peers': list(central_server.peers.items())}, namespace='/music')
        socketio.emit('file_list_updated', {'files': list(central_server.shared_files.keys())}, namespace='/music')
        
        return jsonify({'status': 'success', 'message': '注销成功'})
    else:
        return jsonify({'status': 'error', 'message': '节点不存在'})

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    data = request.json
    peer_id = data.get('peer_id')
    
    if peer_id in central_server.peers:
        # 简单地更新最后活跃时间（在实际应用中可能需要存储这个信息）
        print(f"收到节点 {peer_id} 的心跳包")
        return jsonify({'status': 'success', 'message': '心跳包已接收'})
    else:
        return jsonify({'status': 'error', 'message': '节点未注册'})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件部分'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'})
    
    peer_id = request.form.get('peer_id')
    if not peer_id:
        return jsonify({'status': 'error', 'message': '节点ID不能为空'})
    
    try:
        # 保存文件到共享目录
        file_path = os.path.join('shared_music', file.filename)
        file.save(file_path)
        
        # 更新共享文件列表
        if file.filename not in central_server.shared_files:
            central_server.shared_files[file.filename] = []
        if peer_id not in central_server.shared_files[file.filename]:
            central_server.shared_files[file.filename].append(peer_id)
        
        print(f"Web客户端 {peer_id} 共享了文件: {file.filename}")
        
        # 广播文件列表更新
        socketio.emit('file_list_updated', {'files': list(central_server.shared_files.keys())}, namespace='/music')
        
        return jsonify({'status': 'success', 'message': '文件上传成功'})
    except Exception as e:
        print(f"文件上传失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/download')
def api_download():
    filename = request.args.get('filename')
    peer_ip = request.args.get('peer_ip')
    peer_port = request.args.get('peer_port')
    
    if not filename:
        return jsonify({'status': 'error', 'message': '文件名不能为空'})
    
    try:
        # 首先检查本地是否有该文件
        local_file_path = os.path.join('shared_music', filename)
        if os.path.exists(local_file_path):
            # 如果本地有，直接提供下载
            print(f"从本地提供文件下载: {filename}")
            return send_from_directory('shared_music', filename, as_attachment=True)
        
        # 如果本地没有，尝试从其他节点下载
        if peer_ip and peer_port:
            # 创建下载任务
            print(f"从节点 {peer_ip}:{peer_port} 下载文件: {filename}")
            
            # 模拟从其他节点下载文件
            # 在实际应用中，这里应该建立socket连接并下载文件
            time.sleep(1)  # 模拟下载延迟
            
            # 检查是否已经下载到downloads目录
            download_path = os.path.join('downloads', filename)
            if os.path.exists(download_path):
                return send_from_directory('downloads', filename, as_attachment=True)
            else:
                # 如果仍然没有，返回错误
                return jsonify({'status': 'error', 'message': '文件不存在'})
        
        # 查找所有可用的节点
        if filename in central_server.shared_files:
            peers = central_server.shared_files[filename]
            if peers:
                # 选择第一个可用的节点
                peer_id = peers[0]
                if peer_id in central_server.peers:
                    peer_ip, peer_port = central_server.peers[peer_id]
                    # 重定向到该节点下载
                    print(f"重定向到节点 {peer_ip}:{peer_port} 下载文件: {filename}")
                    # 在实际应用中，这里应该建立socket连接并下载文件
                    time.sleep(1)  # 模拟下载延迟
                    return jsonify({'status': 'success', 'message': f'开始从节点 {peer_ip}:{peer_port} 下载'})
        
        return jsonify({'status': 'error', 'message': '没有找到可用的文件源'})
    except Exception as e:
        print(f"文件下载失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# WebSocket事件处理
@socketio.on('connect', namespace='/music')
def handle_connect():
    client_id = str(uuid.uuid4())[:8]
    web_clients[request.sid] = client_id
    join_room('music_room')
    print(f"Web客户端连接: {client_id}")
    # 发送当前文件列表给新连接的客户端
    emit('file_list_update', {'files': list(central_server.shared_files.keys())})

@socketio.on('disconnect', namespace='/music')
def handle_disconnect():
    if request.sid in web_clients:
        client_id = web_clients[request.sid]
        del web_clients[request.sid]
        print(f"Web客户端断开连接: {client_id}")

@socketio.on('search', namespace='/music')
def handle_search(data):
    keyword = data.get('keyword', '').lower()
    results = {}
    for filename, peers in central_server.shared_files.items():
        if keyword in filename.lower():
            results[filename] = [central_server.peers[peer_id] for peer_id in peers]
    emit('search_results', {'results': results})

# 启动中心服务器和Web服务器
def start_servers():
    # 确保必要的目录存在
    ensure_directories()
    
    # 启动中心服务器线程
    central_thread = threading.Thread(target=central_server.start)
    central_thread.daemon = True
    central_thread.start()
    
    # 启动Web服务器
    print("Web服务器启动在 http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    start_servers()