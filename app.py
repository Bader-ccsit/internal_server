import os
import sys
import threading
import socket
import tkinter as tk
from tkinter import filedialog, Label, Button, Toplevel, messagebox
from flask import Flask, request, send_from_directory, render_template_string, jsonify
from PIL import Image, ImageTk
import qrcode

# Dynamically determine the base directory
if getattr(sys, 'frozen', False):
    # If the application is run as a bundled executable, use the executable's directory
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If running as a script, use the script's directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def upload_form():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Files</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f4f4f4; }
            .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1); }
            form { margin: 20px 0; }
            input[type="file"] { display: block; margin: 10px auto; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 10px 0; }
            a { text-decoration: none; color: blue; font-weight: bold; }
            .message { margin-top: 10px; font-weight: bold; }
        </style>
        <script>
            async function uploadFile(event) {
                event.preventDefault(); // Prevent the form from submitting the traditional way

                const formData = new FormData(event.target); // Get the form data
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json(); // Parse the JSON response

                // Display the message
                const messageDiv = document.querySelector('.message');
                messageDiv.textContent = result.message;
                messageDiv.style.color = result.color;

                // Refresh the list of files
                if (result.success) {
                    const fileList = document.querySelector('ul');
                    fileList.innerHTML = result.files.map(file => `
                        <li><a href="/uploads/${file}" target="_blank">${file}</a></li>
                    `).join('');
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Upload Files</h1>
            <form onsubmit="uploadFile(event)">
                <input type="file" name="file">
                <input type="submit" value="Upload">
            </form>
            <div class="message" style="color: black;"></div>
            <h2>Received Files</h2>
            <ul>
                {% for img in files %}
                    <li><a href="/uploads/{{ img }}" target="_blank">{{ img }}</a></li>
                {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    ''', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No file part',
            'color': 'red',
            'files': os.listdir(app.config['UPLOAD_FOLDER'])
        })
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'No selected file',
            'color': 'red',
            'files': os.listdir(app.config['UPLOAD_FOLDER'])
        })
    try:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'color': 'green',
            'files': os.listdir(app.config['UPLOAD_FOLDER'])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error uploading file: {str(e)}',
            'color': 'red',
            'files': os.listdir(app.config['UPLOAD_FOLDER'])
        })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def generate_qr_code(url):
    qr = qrcode.make(url)
    qr_path = "server_qr.png"
    qr.save(qr_path)
    return qr_path

class FileTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer App")
        self.root.geometry("500x550")  # Increased height to accommodate the footer
        
        self.label = Label(root, text="Server Status: Stopped", fg="red")
        self.label.pack(pady=10)
        
        self.start_button = Button(root, text="Start Server", command=self.start_server)
        self.start_button.pack(pady=5)
        
        self.stop_button = Button(root, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        self.preview_button = Button(root, text="Preview Uploads", command=self.preview_uploads)
        self.preview_button.pack(pady=5)
        
        self.qr_label = Label(root)
        self.qr_label.pack(pady=10)
        
        # Add Help button
        self.help_button = Button(root, text="Help", command=self.show_help)
        self.help_button.pack(pady=5)
        
        # Add footer
        self.footer_label = Label(root, text="Made by Bader", font=("Arial", 10))
        self.footer_label.pack(side=tk.BOTTOM, pady=10)
        
        self.server_thread = None
        self.server_url = ""
    
    def run_flask_server(self):
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    
    def start_server(self):
        if not self.server_thread:
            self.server_thread = threading.Thread(target=self.run_flask_server, daemon=True)
            self.server_thread.start()
            self.server_url = f"http://{get_local_ip()}:5000"
            self.label.config(text=f"Server Status: Running on {self.server_url}", fg="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            qr_path = generate_qr_code(self.server_url)
            qr_img = Image.open(qr_path)
            qr_img = qr_img.resize((150, 150))
            self.qr_code = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=self.qr_code)
    
    def stop_server(self):
        os._exit(0)  # Force stop the server
    
    def preview_uploads(self):
        os.system(f'start {self.server_url}')  # Opens the upload page in default browser
    
    def show_help(self):
        # Create a new window for help
        help_window = Toplevel(self.root)
        help_window.title("Help")
        help_window.geometry("550x350")
        
        help_text = (
            "This application allows you to transfer files between devices on the same network.\n\n"
            "1. Click 'Start Server' to start the file transfer server.\n"
            "2. Scan the QR code or open the provided URL in a browser on another device.\n"
            "3. Upload files using the web interface.\n"
            "4. Files will be saved in the 'uploads' folder on the server.\n"
            "5. Click 'Preview Uploads' to view uploaded files in your browser.\n\n"
            "---------------------------------------------------------------------------------\n\n"
            "1. تأكد من أن طرفا النقل متصلين بنفس شبكة الانترنت"
            "\n2. يقوم هذا الزر بتشغيل السيرفر مما يسمح بنقل الملفات Start Server"
            "\n3. QR code او من خلال مسح ال Preview Uploads توجه الى صفحة نقل الملفات اما عن طريق النقر على  "
            "\n4. Open ثم اختر الملف المطلوب نقله ثم اختر  Choose File لرفع الملفات انقر على  "
            "\n5. Recived Files ثم جدد الصفحة وستجد الملفات تحت قسم  Upload لتأكيد رفع الملفات انقر على "
            "\n6. Stop Server عند الانتهاء اوقف السيرفر/الخادم من خلال النقر على "
            "\n\n"
        )
        
        help_label = Label(help_window, text=help_text, justify=tk.LEFT, padx=10, pady=10)
        help_label.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app_gui = FileTransferApp(root)
    root.mainloop()