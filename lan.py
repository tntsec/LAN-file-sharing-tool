import os
import socket
import qrcode
import tkinter as tk
from tkinter import Label, Button, filedialog, messagebox
from PIL import Image, ImageTk
from io import BytesIO
from threading import Thread
from flask import Flask, render_template_string, request, send_from_directory, redirect, url_for

# 创建Flask应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 * 1024  # 100GB limit

# 确保上传文件夹存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# 获取本机局域网IP地址
def get_local_ip():
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个公共DNS服务器（不实际发送数据）
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # 备用方法
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


# Flask路由
@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>局域网文件共享</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .upload-form { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
            .file-list { margin: 20px 0; }
            .file-item { padding: 8px; border-bottom: 1px solid #ddd; }
            .file-item:hover { background: #f0f0f0; }
            .btn { padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            .btn:hover { background: #0056b3; }
            .btn-download { background: #28a745; }
            .btn-download:hover { background: #218838; }
            .btn-delete { background: #dc3545; }
            .btn-delete:hover { background: #c82333; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>局域网文件共享</h1>

            <div class="upload-form">
                <h2>上传文件</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input type="file" name="file" required>
                    <button type="submit" class="btn">上传</button>
                </form>
            </div>

            <div class="file-list">
                <h2>文件列表</h2>
                {% if files %}
                    {% for file in files %}
                        <div class="file-item">
                            <span>{{ file }}</span>
                            <a href="{{ url_for('download_file', filename=file) }}" class="btn btn-download">下载</a>
                            <a href="{{ url_for('delete_file', filename=file) }}" class="btn btn-delete" onclick="return confirm('确定要删除这个文件吗？')">删除</a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>暂无文件</p>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    ''', files=files)


@app.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('index'))


# GUI应用程序
class FileShareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("局域网文件共享工具")
        self.root.geometry("400x500")

        # 获取本机IP
        self.local_ip = get_local_ip()
        self.port = 5000

        # 创建UI元素
        self.create_widgets()

        # 启动Flask服务器
        self.start_flask_server()

        # 生成并显示二维码
        self.generate_qr_code()

    def create_widgets(self):
        # 标题
        title_label = Label(self.root, text="局域网文件共享", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        # IP地址显示
        ip_frame = tk.Frame(self.root)
        ip_frame.pack(pady=10)

        ip_label = Label(ip_frame, text="访问地址:", font=("Arial", 10))
        ip_label.pack(side=tk.LEFT)

        self.ip_text = Label(ip_frame, text=f"http://{self.local_ip}:{self.port}",
                             font=("Arial", 10, "bold"), fg="blue")
        self.ip_text.pack(side=tk.LEFT, padx=5)

        # 二维码显示区域
        self.qr_label = Label(self.root)
        self.qr_label.pack(pady=20)

        # 说明文字
        instructions = Label(self.root, text="使用手机扫描二维码\n或在浏览器中输入上述地址",
                             font=("Arial", 10), justify=tk.CENTER)
        instructions.pack(pady=10)

        # 操作按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)

        open_btn = Button(btn_frame, text="打开文件夹", command=self.open_upload_folder,
                          font=("Arial", 10), width=12)
        open_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = Button(btn_frame, text="刷新二维码", command=self.generate_qr_code,
                             font=("Arial", 10), width=12)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        exit_btn = Button(btn_frame, text="退出程序", command=self.root.quit,
                          font=("Arial", 10), width=12, bg="#dc3545", fg="white")
        exit_btn.pack(side=tk.LEFT, padx=5)

    def start_flask_server(self):
        """在单独的线程中启动Flask服务器"""

        def run_server():
            app.run(host='0.0.0.0', port=self.port, debug=False)

        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        print(f"Flask服务器已启动，访问地址: http://{self.local_ip}:{self.port}")

    def generate_qr_code(self):
        """生成并显示二维码"""
        url = f"http://{self.local_ip}:{self.port}"

        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # 创建二维码图像
        img = qr.make_image(fill_color="black", back_color="white")

        # 调整大小以适应GUI
        img = img.resize((200, 200), Image.Resampling.LANCZOS)

        # 转换为Tkinter可用的格式
        img_tk = ImageTk.PhotoImage(img)

        # 显示在标签上
        self.qr_label.configure(image=img_tk)
        self.qr_label.image = img_tk  # 保持引用，防止被垃圾回收

    def open_upload_folder(self):
        """打开上传文件夹"""
        try:
            os.startfile(app.config['UPLOAD_FOLDER'])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")


def main():
    # 安装所需的库（如果未安装）
    try:
        import qrcode
        from PIL import Image
        import flask
    except ImportError:
        print("需要安装依赖库，请运行以下命令：")
        print("pip install flask qrcode[pil] pillow")
        return

    # 创建主窗口
    root = tk.Tk()
    app = FileShareApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
