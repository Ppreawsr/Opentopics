from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# ตั้งค่า Selenium WebDriver (ใช้ Chrome)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# เปิดหน้าเว็บ Pantip ที่มี tag "หุ้น"
url = "https://pantip.com/tag/หุ้น"
driver.get(url)
time.sleep(5)  # รอให้หน้าเว็บโหลดข้อมูลเสร็จ

# ดึง HTML ที่ render แล้ว
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# เลือกโพสต์แต่ละอันโดยใช้ selector สำหรับ <li class="pt-list-item">
posts = soup.select("li.pt-list-item")
print("จำนวนโพสต์ที่พบ:", len(posts))

for post in posts:
    # ดึงหัวข้อโพสต์และลิงก์จาก <div class="pt-list-item__title"> ภายใน <li>
    title_tag = post.select_one("div.pt-list-item__title a")
    if title_tag:
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")
        print("หัวข้อกระทู้:", title)
        print("ลิงก์:", link)
    else:
        print("ไม่พบหัวข้อโพสต์")
    
    # ดึงข้อมูลวันที่-เวลาจาก <div class="pt-list-item__info"> โดยดูที่ <span>
    info_span = post.select_one("div.pt-list-item__info span")
    if info_span:
        date_time = info_span.get("title", "ไม่พบข้อมูลวันที่")
        elapsed = info_span.get_text(strip=True)
        print("วันที่-เวลา:", date_time, f"({elapsed})")
    else:
        print("ไม่พบข้อมูลวันที่ในโพสต์")
    
    print("-" * 50)

driver.quit()
