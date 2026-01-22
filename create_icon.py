from PIL import Image, ImageDraw

def create_racing_icon():
    size = (256, 256)
    # 创建透明背景
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 绘制圆形背景 (深赛车绿)
    draw.ellipse([10, 10, 246, 246], fill='#1A1A1A', outline='#28A745', width=10)

    # 2. 绘制方格旗 (Checkerboard pattern)
    # 在右下角绘制
    flag_size = 100
    start_x, start_y = 120, 120
    cell_size = 25
    
    for row in range(4):
        for col in range(4):
            color = 'white' if (row + col) % 2 == 0 else 'black'
            x = start_x + col * cell_size
            y = start_y + row * cell_size
            draw.rectangle([x, y, x + cell_size, y + cell_size], fill=color)

    # 3. 绘制一个简单的汽车侧面轮廓 (红色)
    # 坐标点模拟流线型跑车
    car_color = '#DC3545' # Racing Red
    car_points = [
        (40, 140),  # 车尾下
        (40, 110),  # 车尾上 (尾翼)
        (60, 110),
        (80, 90),   # 后挡风
        (140, 90),  # 车顶
        (180, 110), # 前挡风
        (220, 120), # 车头尖
        (220, 140), # 车头下
    ]
    draw.polygon(car_points, fill=car_color)
    
    # 车轮
    wheel_color = '#333333'
    draw.ellipse([60, 130, 90, 160], fill=wheel_color, outline='gray', width=2) # 后轮
    draw.ellipse([170, 130, 200, 160], fill=wheel_color, outline='gray', width=2) # 前轮

    # 4. 文字 "CCA" (Crazy Car Analyzer)
    # 由于没有加载字体，用简单的线条或矩形模拟，或者直接省略，保持图标简洁
    
    # 保存为 ICO
    img.save('src/assets/app.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Icon created at src/assets/app.ico")

if __name__ == "__main__":
    create_racing_icon()
