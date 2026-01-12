import os
import socket
import qrcode
import threading
import tkinter as tk
from PIL import Image, ImageTk
from flask import Flask, render_template_string, request, send_file, abort, redirect, url_for

# 创建Flask应用
app = Flask(__name__)

# 使用相对路径：程序所在目录下的uploads文件夹
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 * 1024  # 100GB限制


# 获取本机局域网IP
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return socket.gethostbyname(socket.gethostname())


LOCAL_IP = get_local_ip()
PORT = 5000
ACCESS_URL = f"http://{LOCAL_IP}:{PORT}"

# HTML模板（包含删除按钮）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>文件传输</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .box { margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .btn { background: #007bff; color: white; border: none; padding: 8px 15px; 
               border-radius: 4px; cursor: pointer; margin: 5px 0; text-decoration: none; display: inline-block; }
        .btn-delete { background: #dc3545; }
        .btn-download { background: #28a745; }
        .file-item { padding: 10px; margin: 8px 0; border: 1px solid #eee; border-radius: 4px; 
                     display: flex; justify-content: space-between; align-items: center; }
        .file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .actions { display: flex; gap: 5px; }
        .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>📁 文件传输</h1>
    <p>访问地址: <strong>{{ url }}</strong></p>

    <div class="box">
        <h3>⬆️ 上传文件</h3>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit" class="btn">上传</button>
        </form>
        {% if message %}
        <div class="message {% if success %}success{% else %}error{% endif %}">
            {{ message }}
        </div>
        {% endif %}
    </div>

    <div class="box">
        <h3>⬇️ 文件列表</h3>
        {% if files %}
            {% for file in files %}
            <div class="file-item">
                <div class="file-name">{{ file }}</div>
                <div class="actions">
                    <a href="/download/{{ file }}" class="btn btn-download">下载</a>
                    <a href="/delete/{{ file }}" class="btn btn-delete" 
                       onclick="return confirm('确定要删除 {{ file }} 吗？')">删除</a>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <p style="text-align: center; color: #666;">暂无文件，快上传一个吧！</p>
        {% endif %}
    </div>
</body>
</html>
'''


@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    success = False

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                try:
                    filename = file.filename
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    message = f'✅ 文件 "{filename}" 上传成功！'
                    success = True
                except Exception as e:
                    message = f'❌ 上传失败: {str(e)}'
                    success = False

    files = []
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                files.append(filename)
    except Exception as e:
        print(f"获取文件列表失败: {e}")

    return render_template_string(HTML_TEMPLATE,
                                  url=ACCESS_URL,
                                  files=files,
                                  message=message,
                                  success=success)


@app.route('/download/<filename>')
def download_file(filename):
    try:
        # 确保文件名安全
        filename = os.path.basename(filename)
        if not filename:
            abort(400, "无效的文件名")

        # 构建完整文件路径
        filepath = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename)

        # 验证文件是否存在
        if not os.path.exists(filepath):
            abort(404, "文件不存在")

        if not os.path.isfile(filepath):
            abort(400, "无效的文件路径")

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        abort(500, f"下载失败: {str(e)}")


@app.route('/delete/<filename>')
def delete_file(filename):
    try:
        # 确保文件名安全
        filename = os.path.basename(filename)
        if not filename:
            abort(400, "无效的文件名")

        # 构建完整文件路径
        filepath = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename)

        # 验证文件是否存在
        if not os.path.exists(filepath):
            return redirect(url_for('index', message=f'❌ 文件 "{filename}" 不存在', success='false'))

        if not os.path.isfile(filepath):
            return redirect(url_for('index', message=f'❌ "{filename}" 不是文件', success='false'))

        # 删除文件
        os.remove(filepath)

        return redirect(url_for('index', message=f'✅ 文件 "{filename}" 已删除', success='true'))
    except Exception as e:
        return redirect(url_for('index', message=f'❌ 删除失败: {str(e)}', success='false'))


def run_flask_server():
    """运行Flask服务器"""
    app.run(host='0.0.0.0', port=PORT, debug=False)


class FileTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件传输工具")
        self.root.geometry("400x450")
        self.root.resizable(False, False)

        # 标题
        tk.Label(root, text="局域网文件传输", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(root, text="手机扫描二维码访问网页", font=("Arial", 10)).pack(pady=5)

        # 生成并显示二维码
        self.generate_qr_code()

        # 显示访问地址
        url_frame = tk.Frame(root)
        url_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(url_frame, text="访问地址:", font=("Arial", 9)).pack(side='left')
        self.url_entry = tk.Entry(url_frame, width=30, font=("Arial", 9))
        self.url_entry.insert(0, ACCESS_URL)
        self.url_entry.pack(side='left', padx=5, fill='x', expand=True)

        # 按钮区域
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=15)

        # 复制地址按钮
        tk.Button(btn_frame, text="复制地址", command=self.copy_url,
                  bg='#007bff', fg='white', width=10).pack(side='left', padx=5)

        # 打开文件夹按钮（新增）
        tk.Button(btn_frame, text="打开文件夹", command=self.open_folder,
                  bg='#28a745', fg='white', width=10).pack(side='left', padx=5)

        # 退出按钮
        tk.Button(btn_frame, text="退出", command=root.quit,
                  bg='#dc3545', fg='white', width=10).pack(side='left', padx=5)

        # 状态标签
        self.status_label = tk.Label(root, text="✅ 服务已启动", fg='#28a745', font=("Arial", 9))
        self.status_label.pack(pady=5)

    def generate_qr_code(self):
        """生成二维码"""
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(ACCESS_URL)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((250, 250))

        self.qr_photo = ImageTk.PhotoImage(img)
        tk.Label(self.root, image=self.qr_photo).pack(pady=10)

    def copy_url(self):
        """复制URL到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(ACCESS_URL)
        self.root.update()
        self.status_label.config(text="✅ 地址已复制", fg='#28a745')

    def open_folder(self):
        """打开上传文件夹"""
        try:
            folder_path = os.path.join(os.getcwd(), UPLOAD_FOLDER)
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            else:
                import webbrowser
                webbrowser.open(folder_path)
            self.status_label.config(text="📁 文件夹已打开", fg='#007bff')
        except Exception as e:
            self.status_label.config(text=f"❌ 打开失败: {str(e)}", fg='#dc3545')


def main():
    # 启动Flask服务器
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()

    # 创建GUI
    root = tk.Tk()
    app = FileTransferApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
