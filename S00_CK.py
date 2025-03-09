import os
import time
import cv2
import numpy as np
import pytesseract
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

# 配置文件路径
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'image.jpg')
SCREENSHOT_PATH = '/tmp/screenshot.png'

def preprocess_image(image_path):
    """图像预处理增强匹配精度"""
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.GaussianBlur(img, (5,5), 0)
    return img

def find_verify_position():
    """通过模板匹配定位验证框"""
    screenshot = preprocess_image(SCREENSHOT_PATH)
    template = preprocess_image(TEMPLATE_PATH)
    
    # 多尺度模板匹配
    found = None
    for scale in np.linspace(0.8, 1.2, 5):
        resized = cv2.resize(template, (0,0), fx=scale, fy=scale)
        result = cv2.matchTemplate(screenshot, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if found is None or max_val > found[0]:
            found = (max_val, max_loc, resized.shape)
    
    if found and found[0] > 0.7:  # 匹配阈值
        (_, max_loc, (h, w)) = found
        x = max_loc[0] + w//2
        y = max_loc[1] + h//2
        return (x, y)
    return None

def check_success():
    """OCR验证成功文本"""
    img = Image.open(SCREENSHOT_PATH)
    # 截取右下角区域（假设成功提示在此区域）
    region = img.crop((img.width//2, img.height-100, img.width, img.height))
    text = pytesseract.image_to_string(region, config='--psm 6')
    return any(kw in text.lower() for kw in ['success', 'verified', 'passed'])

def main():
    # 配置无头浏览器
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get("https://www.serv00.com/offer/create_new_account")
        time.sleep(8)  # 等待页面完全加载
        
        # 首次截图匹配验证框
        driver.save_screenshot(SCREENSHOT_PATH)
        button_pos = find_verify_position()
        if not button_pos:
            raise Exception("验证框定位失败")

        # 精确点击
        action = ActionChains(driver)
        body = driver.find_element(By.TAG_NAME, 'body')
        action.move_to_element_with_offset(body, button_pos[0], button_pos[1]).click().perform()
        
        # 等待并验证结果
        success = False
        for _ in range(15):
            time.sleep(1)
            driver.save_screenshot(SCREENSHOT_PATH)
            if check_success():
                success = True
                break
        
        if not success:
            raise Exception("验证未通过")
        
        # 获取Cookie（实际需根据目标网站调整）
        cookies = driver.get_cookies()
        print("##[set-output name=cookies;]%s" % cookies)
        return 0
    except Exception as e:
        print(f"##[error] {str(e)}")
        return 1
    finally:
        driver.quit()

if __name__ == "__main__":
    exit(main())
