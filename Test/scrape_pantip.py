from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# ตั้งค่า Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# เปิดหน้าเว็บที่มี tag "หุ้น"
url = "https://pantip.com/tag/หุ้น"
driver.get(url)
time.sleep(5)  # รอให้หน้าเว็บโหลดข้อมูล

# ดึง HTML ที่ render แล้ว
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# ใช้ CSS Selector ที่คุณได้มาจาก Inspect Element
container = soup.select("#__next > div > div > div > div.container > div:nth-child(6)")
print("Container ที่เลือกได้:", container)

if container:
    # สมมุติว่าใน container นี้มีหลายโพสต์ และแต่ละโพสต์มี element ที่มี class "post-item"
    posts = container[0].select("div.post-item")
    if posts:
        for post in posts:
            # ตรวจสอบโพสต์แต่ละอันว่ามีหัวข้อและลิงก์หรือไม่
            title_tag = post.find("a", class_="display-post-title")
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href")
                print("หัวข้อกระทู้:", title)
                print("ลิงก์:", link)
                print("-" * 50)
    else:
        print("ไม่พบโพสต์ภายใน container ที่เลือก")
else:
    print("ไม่พบ container ตาม CSS Selector ที่ให้มา")

driver.quit()
