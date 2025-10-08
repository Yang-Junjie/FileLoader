from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, make_response
from werkzeug.utils import secure_filename
import os
import random
import io
from PIL import Image, ImageDraw, ImageFont
from config import SECRET_KEY, UPLOAD_FOLDER, PASSWORD

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ========== 工具函数 ==========
import math

# 生成验证码文本
def generate_captcha_text(length=6):
    # 使用字母和数字的组合，移除容易混淆的字符
    chars = '23456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ'
    return ''.join(random.choice(chars) for _ in range(length))

# 生成验证码图片
def generate_captcha():
    # 图片大小和背景
    width, height = 200, 80
    # 随机背景色，避免纯色背景
    bg_r, bg_g, bg_b = random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)
    image = Image.new('RGB', (width, height), color=(bg_r, bg_g, bg_b))
    draw = ImageDraw.Draw(image)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        font = ImageFont.truetype("simhei.ttf", 48)  # 尝试加载系统中的黑体
    except:
        font = ImageFont.load_default()
    
    # 生成验证码文本，增加长度到6个字符
    captcha_text = generate_captcha_text(6)
    
    # 绘制验证码文本，添加更多变化
    for i, char in enumerate(captcha_text):
        # 随机颜色（与背景色有较大反差）
        r = random.randint(0, 100) if bg_r > 150 else random.randint(150, 255)
        g = random.randint(0, 100) if bg_g > 150 else random.randint(150, 255)
        b = random.randint(0, 100) if bg_b > 150 else random.randint(150, 255)
        
        # 随机字体大小
        font_size = random.randint(32, 48)
        try:
            char_font = ImageFont.truetype("simhei.ttf", font_size)
        except:
            char_font = ImageFont.load_default()
        
        # 计算位置，增加随机性
        x = 20 + i * 28 + random.randint(-8, 8)
        y = random.randint(5, 25)
        
        # 创建旋转后的字符层
        # 使用getbbox替代deprecated的textsize方法
        bbox = char_font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        char_height = bbox[3] - bbox[1]
        
        char_image = Image.new('RGBA', (char_width * 2, char_height * 2), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_image)
        char_draw.text((char_width//2, char_height//2), char, font=char_font, fill=(r, g, b))
        
        # 随机旋转字符，角度范围更大
        rotation = random.randint(-30, 30)
        rotated_char = char_image.rotate(rotation, expand=1)
        
        # 粘贴旋转后的字符到主图像
        image.paste(rotated_char, (x, y), rotated_char)
    
    # 绘制干扰线
    for _ in range(10):
        r, g, b = random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        # 使用不同的线宽
        line_width = random.randint(1, 3)
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=line_width)
    
    # 绘制波浪线干扰
    for _ in range(3):
        r, g, b = random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)
        y_offset = random.randint(0, height)
        amplitude = random.randint(5, 15)
        frequency = random.randint(1, 3)
        points = []
        for x in range(0, width, 5):
            y = y_offset + amplitude * random.uniform(0.8, 1.2) * math.sin(x * 0.01 * frequency)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=(r, g, b), width=2)
    
    # 绘制更多噪点
    for _ in range(300):
        r, g, b = random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)
        x, y = random.randint(0, width), random.randint(0, height)
        # 使用不同大小的点
        point_size = random.randint(1, 2)
        draw.ellipse([(x, y), (x + point_size, y + point_size)], fill=(r, g, b))
    
    # 添加干扰几何形状
    for _ in range(10):
        r, g, b = random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)
        x, y = random.randint(0, width), random.randint(0, height)
        shape_type = random.choice(['circle', 'rectangle'])
        
        if shape_type == 'circle':
            radius = random.randint(3, 10)
            draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], outline=(r, g, b), width=1)
        else:
            w, h = random.randint(5, 20), random.randint(5, 20)
            draw.rectangle([(x, y), (x+w, y+h)], outline=(r, g, b), width=1)
    
    # 保存验证码文本到session
    session['captcha'] = captcha_text.lower()  # 转为小写以忽略大小写
    
    # 将图片保存到内存
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    buf.seek(0)
    
    return buf


# ========== 路由 ==========
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        captcha = request.form.get('captcha')
        if password == PASSWORD and captcha and captcha.lower() == session.get('captcha'):
            session['logged_in'] = True
            return redirect(url_for('upload_page'))
        else:
            return render_template('login.html', error='密码或验证码错误')

    # GET 请求时不需要生成验证码文本，只渲染页面
    return render_template('login.html')


# 验证码图片路由
@app.route('/captcha.png')
def captcha_png():
    captcha_image = generate_captcha()
    response = make_response(captcha_image.read())
    response.headers['Content-Type'] = 'image/png'
    return response


@app.route('/upload_page')
def upload_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    file = request.files.get('file')
    if not file:
        return "没有选择文件", 400

    # 获取用户输入的上传路径
    upload_path = request.form.get('upload_path', '').strip()
    
    # 安全处理上传路径，防止目录遍历攻击
    safe_upload_path = secure_filename(upload_path) if upload_path else ''
    
    # 构建完整的保存路径
    filename = secure_filename(file.filename)
    if safe_upload_path:
        save_dir = os.path.join(app.config['UPLOAD_FOLDER'], safe_upload_path)
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        # 保存相对路径以便在成功页面显示，使用正斜杠确保URL正确性
        display_path = f"{safe_upload_path}/{filename}"
    else:
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        display_path = filename
    
    # 保存文件
    file.save(save_path)
    return render_template('success.html', filename=display_path)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # 使用path转换器确保能够正确处理包含子目录的路径
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
