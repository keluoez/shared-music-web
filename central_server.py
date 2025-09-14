import socket
import threading
import json
import os

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
            return {'status': 'success', 'message': f'共享了 {len(files)} 个文件'}
        
        elif command == 'search':
            keyword = message.get('keyword', '').lower()
            results = {}
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

if __name__ == "__main__":
    server = CentralServer()
    server.start()
