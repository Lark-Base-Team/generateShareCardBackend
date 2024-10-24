from flask import Flask, render_template, request, send_file, jsonify
from datetime import datetime
from io import BytesIO
from weasyprint import HTML
from PIL import Image, ImageChops
# import office
import fitz  # PyMuPDF
import os
from weasyprint import CSS
from weasyprint.text.fonts import FontConfiguration
import string
import requests
from datetime import datetime
from pdf2image import convert_from_path
import random
import time

app = Flask(__name__)

# 时间戳
start_time = 0.0
mid_time = 0.0


def record_time(desc):
    global start_time, mid_time  # 声明全局变量
    now_time = time.time()
    print(
        f"{desc}, accumulated time: {now_time - start_time:.2f}s, last stage time: {now_time - mid_time:.2f}s"
    )
    mid_time = now_time


# 全局缓存字典
font_config = FontConfiguration()
css_cache = {}


# 预加载所有字体和 CSS
def preload_fonts_and_css():
    print('start preload fonts and css...')
    global css_cache

    css_files = [
        'card1.css', 'card2.css', 'card3.css', 'card4.css', 'card5.css'
    ]

    css_path_base = os.path.join(os.path.dirname(__file__), 'static', 'styles')

    # 预加载每个 CSS 文件
    for css_file in css_files:
        css_path = os.path.join(css_path_base, css_file)
        css_cache[css_file] = CSS(filename=css_path, font_config=font_config)


# 在应用启动时加载字体和 CSS
preload_fonts_and_css()
print('finish preload fonts and css')


def format_date():
    # 获取当前日期
    current_date = datetime.now()

    # 获取年份、月份和日期
    year = current_date.year
    month = current_date.month
    day = current_date.day

    # 生成yyyy/mm/dd格式的字符串
    return f"{year}/{month:02d}/{day:02d}"


# 调用上传阿里云oss的接口
def call_upload_file2oss_service(img_data, file_name):
    upload_url = 'https://util-transfer-file-2-cdn-wuyi.replit.app/upload-special-zdjj-card'

    files = {'file': (file_name, img_data, 'image/png')}

    # 发送接口请求
    response = requests.post(upload_url, files=files)

    if response.status_code == 200:
        return response.json()['url']
    else:
        return None


# 定义一个根路由，显示 "Hello World"
@app.route('/')
def hello_world():
    return 'Hello, World!'


def trim_image(image):
    """去除图片的空白边界"""
    bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    if bbox:
        return image.crop(bbox)
    return image


class CardGenerator:

    def __init__(self, content, **kwargs):
        self.content = content
        self.title = kwargs.get('title')
        self.name = kwargs.get('name')
        self.time = kwargs.get('time')
        self.source = kwargs.get('source')
        self.css_selector = kwargs.get('css_selector')
        self.align_value = kwargs.get('align_value')
        self.zoom = kwargs.get('zoom', 8)  # Default zoom is 1 if not provided

    def generate_card(self):

        record_time('step in generate_card function')

        # 渲染 card.html 模板
        rendered_html = render_template(
            'card.html',
            content=self.content,
            title=self.title,
            name=self.name,
            time=self.time,
            source=self.source,
            align_value=self.align_value,
            # css_url=css_url
        )

        record_time('finish render template')

        # 获取静态文件的本地路径
        css_file = 'card' + str(self.css_selector) + '.css'
        # css_path = os.path.join(os.path.dirname(__file__), 'static', 'styles',
        #                         css_file)

        # # 创建 CSS 对象
        # font_config = FontConfiguration()
        # css = CSS(filename=css_path, font_config=font_config)

        css = css_cache.get(css_file)

        record_time('start convert html to pdf...')
        # 使用 WeasyPrint 生成 PDF 字节流，并传递 CSS
        pdf_file = HTML(string=rendered_html).write_pdf(
            stylesheets=[css], font_config=font_config)
        record_time('finish convert html to pdf')

        # 生成随机的6位字符
        pdf_id = ''.join(
            random.choices(string.ascii_letters + string.digits, k=6))
        output_pdf_path = os.path.join(os.path.dirname(__file__), 'output',
                                       f'generated_card-{pdf_id}.pdf')

        record_time('finish generate pdf_file')

        # 保存 PDF 文件到本地
        with open(output_pdf_path, 'wb') as f:
            f.write(pdf_file)

        record_time('finish save pdf_file')

        # 将 PDF 转换为 PNG 图片
        img_data, img_width, img_height = self.pdf_to_cropped_png(
            output_pdf_path, self.zoom)

        record_time('finish crop png')

        # 删除临时 PDF 文件
        os.remove(output_pdf_path)

        # 返回生成的图片
        return img_data, img_width, img_height

    def pdf_to_cropped_png(self, pdf_path, zoom):
        # 将PDF的每一页转换为图片
        record_time('start convert pdf to png...')
        images = convert_from_path(pdf_path, dpi=120 * zoom, fmt='png')
        record_time('finish convert pdf to png')
        image = images[0]

        # 裁剪图片的空白区域
        cropped_image = trim_image(image)

        # 将裁剪后的图片保存为字节流
        img_byte_arr = BytesIO()
        cropped_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return img_byte_arr, image.width, image.height


# 生成图片的 API
@app.route('/generate_card', methods=['POST'])
def generate_card_endpoint():
    # 记录开始时间戳
    global start_time, mid_time
    start_time = time.time()
    mid_time = start_time
    print('start counting...')
    # 从请求中获取 JSON 数据
    data = request.get_json()

    # 验证请求数据，只强制要求 'content' 字段存在
    content = data.get('content')
    if not content:
        return {"error": "The 'content' field is required."}, 400
    content = content.replace('\n', '<br>')

    # 获取其他可选字段，如果不存在则设置默认值
    title = data.get('title', '')
    name = data.get('name', '')
    if name != '':
        name = "@" + name
    timestamp = data.get('time', None)  # 时间戳可以为空
    print(time)
    source = data.get('source', '')
    zoom = int(data.get('zoom', 2))  # 缩放比例，默认为 2，1~5
    css_selector = int(data.get('css_selector', 1))  # 选择css样式，默认为1
    align_value = data.get('align_value', 'start')  # 文本对齐方式，默认为左对齐
    print(content, title, name, timestamp, source, zoom, css_selector)

    # 验证 css_selector 如果有值，必须在 1 到 5 的整数范围内
    if css_selector:
        try:
            css_selector_value = int(css_selector)
            if css_selector_value < 1 or css_selector_value > 5:
                return {
                    "error":
                    "The 'css_selector' field must be an integer between 1 and 5."
                }, 400
        except ValueError:
            return {
                "error": "The 'css_selector' field must be a valid integer."
            }, 400
    # 如果时间戳存在，将其转换为日期格式，否则使用默认时间
    if timestamp:
        date_time = datetime.fromtimestamp(timestamp)
        data_time = date_time.strftime("%B %d, %Y")
        print(data_time)
    else:
        data_time = ""

    time_name = datetime.fromtimestamp(
        (datetime.now().timestamp() + 8 * 3600)).strftime("%Y-%m-%d-%H%M")

    # 生成随机的4位ID
    random_id = ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6))

    # 调用核心函数生成图片
    # 假设 generate_card 函数返回一个字节流
    cardGenerator = CardGenerator(content,
                                  title=title,
                                  name=name,
                                  data_time=data_time,
                                  zoom=zoom,
                                  source=source,
                                  time=data_time,
                                  css_selector=css_selector,
                                  align_value=align_value)
    img_data, img_width, img_height = cardGenerator.generate_card()

    # 创建文件名
    filename = f"{time_name}-{random_id}.png"

    # 返回生成的图片作为响应
    # return send_file(img_data,
    #                  mimetype='image/png',
    #                  as_attachment=True,
    #                  download_name=filename)

    # 调用上传服务并获取URL
    record_time('start call_upload_file2oss_service...')
    src = call_upload_file2oss_service(img_data, filename)
    record_time('start call_upload_file2oss_service...')

    # 返回生成的图片URL
    if src:
        return jsonify({
            'src': src,
            'name': filename,
            'width': img_width,
            'height': img_height
        })
    else:
        return jsonify({'error': 'Failed to upload image.'}), 500
