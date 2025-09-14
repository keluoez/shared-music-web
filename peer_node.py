import socket
import threading
import json
import os
import uuid
import time
from tkinter import Tk, Listbox, Entry, Button, Label, filedialog, messagebox, Scrollbar, Frame

class MusicSharingPeer:
    def __init__(self, central_host='localhost', central_port=5000, peer_port=5001):
        self.central_host = central_host
        self.central_port = central_port
        self.peer_port = peer_port
        self.peer_id = str(uuid.uuid4())[:8]  # 生成简短的节点ID
        self.shared_dir = "shared_music"  # 共享音乐目录
        self.download_dir = "downloads"   # 下载目录
        self.running = True
        
        # 创建必要的目录
        if not os.path.exists(self.shared_dir):
            os.makedirs(self.shared_dir)
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        # 启动节点服务器（用于接收其他节点的文件请求）
        self.peer_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_server_socket.bind(('0.0.0.0', self.peer_port))
        self.peer_server_socket.listen(5)
        threading.Thread(target=self.start_peer_server, daemon=True).start()
        
        # 连接到中心服务器并注册
        self.register_with_central_server()
        
        # 共享本地文件
        self.share_local_files()
        
        # 创建GUI
        self.create_gui()

    def register_with_central_server(self):
        """向中心服务器注册节点"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = {
                    'command': 'register',
                    'peer_id': self.peer_id,
                    'peer_port': self.peer_port
                }
                s.send(json.dumps(message).encode('utf-8'))
                response = json.loads(s.recv(1024).decode('utf-8'))
                if response['status'] == 'success':
                    print(f"节点注册成功，ID: {self.peer_id}")
                else:
                    print(f"节点注册失败: {response['message']}")
        except Exception as e:
            print(f"注册到中心服务器时出错: {e}")

    def share_local_files(self):
        """共享本地音乐文件到网络"""
        try:
            # 获取共享目录中的所有音乐文件
            music_files = [f for f in os.listdir(self.shared_dir) 
                          if os.path.isfile(os.path.join(self.shared_dir, f)) 
                          and f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = {
                    'command': 'share',
                    'peer_id': self.peer_id,
                    'files': music_files
                }
                s.send(json.dumps(message).encode('utf-8'))
                response = json.loads(s.recv(1024).decode('utf-8'))
                print(response['message'])
                
                # 更新GUI中的本地文件列表
                self.update_local_files_list()
        except Exception as e:
            print(f"共享文件时出错: {e}")

    def search_files(self, keyword):
        """搜索网络中的音乐文件"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = {
                    'command': 'search',
                    'keyword': keyword
                }
                s.send(json.dumps(message).encode('utf-8'))
                response = json.loads(s.recv(4096).decode('utf-8'))
                
                if response['status'] == 'success':
                    self.search_results = response['results']
                    self.update_search_results()
                else:
                    messagebox.showerror("错误", response['message'])
        except Exception as e:
            print(f"搜索文件时出错: {e}")
            messagebox.showerror("错误", f"搜索失败: {str(e)}")

    def download_file(self, filename, peer_address):
        """从指定节点下载文件"""
        try:
            ip, port = peer_address
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                message = {
                    'command': 'download',
                    'filename': filename
                }
                s.send(json.dumps(message).encode('utf-8'))
                
                # 接收文件大小
                file_size_data = s.recv(1024).decode('utf-8')
                if not file_size_data:
                    raise Exception("未收到文件大小信息")
                
                file_size = int(file_size_data)
                s.send(b"ready")  # 确认已收到文件大小
                
                # 接收文件内容
                download_path = os.path.join(self.download_dir, filename)
                received_size = 0
                
                with open(download_path, 'wb') as f:
                    while received_size < file_size:
                        data = s.recv(4096)
                        if not data:
                            break
                        f.write(data)
                        received_size += len(data)
                        # 更新进度（简化版）
                        self.update_download_status(f"下载中: {received_size}/{file_size} bytes")
                
                if received_size == file_size:
                    messagebox.showinfo("成功", f"文件 {filename} 下载完成！")
                    self.update_download_status("下载完成")
                    # 下载完成后，将文件加入共享
                    self.share_local_files()
                else:
                    messagebox.showerror("错误", f"文件下载不完整，只收到 {received_size}/{file_size} bytes")
        except Exception as e:
            print(f"下载文件时出错: {e}")
            messagebox.showerror("错误", f"下载失败: {str(e)}")

    def start_peer_server(self):
        """启动节点服务器，处理其他节点的文件请求"""
        print(f"节点服务器启动在端口 {self.peer_port}")
        while self.running:
            client_socket, client_address = self.peer_server_socket.accept()
            threading.Thread(target=self.handle_peer_request, args=(client_socket, client_address), daemon=True).start()

    def handle_peer_request(self, client_socket, client_address):
        """处理其他节点的请求（主要是文件下载请求）"""
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                return
            
            message = json.loads(data)
            if message['command'] == 'download':
                filename = message['filename']
                file_path = os.path.join(self.shared_dir, filename)
                
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    # 发送文件大小
                    file_size = os.path.getsize(file_path)
                    client_socket.send(str(file_size).encode('utf-8'))
                    
                    # 等待客户端确认
                    client_socket.recv(1024)
                    
                    # 发送文件内容
                    with open(file_path, 'rb') as f:
                        while True:
                            data = f.read(4096)
                            if not data:
                                break
                            client_socket.send(data)
                    print(f"已向 {client_address} 发送文件: {filename}")
                else:
                    client_socket.send(b"0")  # 表示文件不存在
        except Exception as e:
            print(f"处理节点请求时出错: {e}")
        finally:
            client_socket.close()

    def add_local_file(self):
        """添加本地文件到共享目录"""
        file_paths = filedialog.askopenfilenames(
            title="选择音乐文件",
            filetypes=[("音乐文件", "*.mp3 *.wav *.flac *.m4a")]
        )
        
        if file_paths:
            for file_path in file_paths:
                try:
                    # 复制文件到共享目录
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(self.shared_dir, filename)
                    
                    with open(file_path, 'rb') as src, open(dest_path, 'wb') as dest:
                        dest.write(src.read())
                    
                    print(f"已添加文件到共享: {filename}")
                except Exception as e:
                    print(f"添加文件时出错: {e}")
            
            # 重新共享文件列表
            self.share_local_files()

    # GUI相关方法
    def create_gui(self):
        self.root = Tk()
        self.root.title(f"P2P音乐共享 - 节点ID: {self.peer_id}")
        self.root.geometry("800x600")
        
        # 创建主框架
        main_frame = Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 搜索区域
        search_frame = Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        Label(search_frame, text="搜索音乐:").pack(side="left", padx=(0, 5))
        self.search_entry = Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        search_button = Button(search_frame, text="搜索", command=self.on_search)
        search_button.pack(side="left")
        
        # 搜索结果区域
        Label(main_frame, text="搜索结果:").pack(anchor="w")
        results_frame = Frame(main_frame)
        results_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.results_listbox = Listbox(results_frame)
        self.results_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(results_frame, command=self.results_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.results_listbox.config(yscrollcommand=scrollbar.set)
        
        download_button = Button(main_frame, text="下载选中文件", command=self.on_download)
        download_button.pack(fill="x", pady=(0, 10))
        
        self.download_status = Label(main_frame, text="", fg="blue")
        self.download_status.pack(anchor="w", pady=(0, 10))
        
        # 本地文件区域
        Label(main_frame, text="我的共享文件:").pack(anchor="w")
        local_files_frame = Frame(main_frame)
        local_files_frame.pack(fill="both", expand=True)
        
        self.local_files_listbox = Listbox(local_files_frame)
        self.local_files_listbox.pack(side="left", fill="both", expand=True)
        scrollbar2 = Scrollbar(local_files_frame, command=self.local_files_listbox.yview)
        scrollbar2.pack(side="right", fill="y")
        self.local_files_listbox.config(yscrollcommand=scrollbar2.set)
        
        add_file_button = Button(main_frame, text="添加本地音乐到共享", command=self.add_local_file)
        add_file_button.pack(fill="x", pady=(10, 0))
        
        # 关闭窗口时的处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_search(self):
        """处理搜索按钮点击"""
        keyword = self.search_entry.get()
        if keyword:
            self.search_files(keyword)
        else:
            messagebox.showwarning("提示", "请输入搜索关键词")

    def on_download(self):
        """处理下载按钮点击"""
        selected_index = self.results_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("提示", "请先选择要下载的文件")
            return
        
        selected_text = self.results_listbox.get(selected_index[0])
        # 解析选中的文本，获取文件名和节点信息
        # 格式如: "filename - 可从 192.168.1.100:5001 下载"
        filename = selected_text.split(" - ")[0]
        
        if filename in self.search_results and self.search_results[filename]:
            # 选择第一个可用节点进行下载
            peer_address = self.search_results[filename][0]
            self.download_file(filename, peer_address)

    def update_search_results(self):
        """更新搜索结果列表"""
        self.results_listbox.delete(0, "end")
        if not self.search_results:
            self.results_listbox.insert("end", "没有找到匹配的文件")
            return
        
        for filename, peers in self.search_results.items():
            peers_str = ", ".join([f"{ip}:{port}" for ip, port in peers])
            self.results_listbox.insert("end", f"{filename} - 可从 {peers_str} 下载")

    def update_local_files_list(self):
        """更新本地共享文件列表"""
        self.local_files_listbox.delete(0, "end")
        music_files = [f for f in os.listdir(self.shared_dir) 
                      if os.path.isfile(os.path.join(self.shared_dir, f)) 
                      and f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
        
        if not music_files:
            self.local_files_listbox.insert("end", "没有共享文件，点击下方按钮添加")
        else:
            for file in music_files:
                self.local_files_listbox.insert("end", file)

    def update_download_status(self, message):
        """更新下载状态"""
        self.download_status.config(text=message)
        self.root.update_idletasks()

    def on_close(self):
        """关闭窗口时的清理工作"""
        self.running = False
        self.peer_server_socket.close()
        self.root.destroy()

    def run(self):
        """运行GUI主循环"""
        self.root.mainloop()

if __name__ == "__main__":
    # 可以指定不同的端口号来运行多个节点
    import sys
    peer_port = 5001
    if len(sys.argv) > 1:
        try:
            peer_port = int(sys.argv[1])
        except ValueError:
            pass
    
    peer = MusicSharingPeer(peer_port=peer_port)
    peer.run()
