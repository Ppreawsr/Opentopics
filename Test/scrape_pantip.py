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

# ใช้ CSS Selector เพื่อดึง container หลักที่แสดงโพสต์
container = soup.select("#__next > div > div > div > div.container > div:nth-child(6)")
if container:
    print("พบ container หลักแล้ว")
    # จาก container ให้เลือก <ul> ที่มี class "pt-list"
    post_list = container[0].select("ul.pt-list")
    if post_list:
        # จาก <ul> ให้ดึงโพสต์แต่ละอัน ซึ่งเป็น <li class="pt-list-item">
        posts = post_list[0].select("li.pt-list-item")
        print("จำนวนโพสต์ที่พบ:", len(posts))
        if posts:
            for post in posts:
                # หาข้อมูลหัวข้อโพสต์ใน <div class="pt-list-item__title">
                title_div = post.find("div", class_="pt-list-item__title")
                if title_div:
                    # หาตัว tag <a> ภายใน <h2> ที่เก็บหัวข้อและลิงก์
                    a_tag = title_div.find("a")
                    if a_tag:
                        title = a_tag.get_text(strip=True)
                        link = a_tag.get("href")
                        print("หัวข้อกระทู้:", title)
                        print("ลิงก์:", link)
                        print("-" * 50)
        else:
            print("ไม่พบโพสต์ภายใน <ul> ที่เลือก")
    else:
        print("ไม่พบ <ul> ที่มี class 'pt-list' ใน container")
else:
    print("ไม่พบ container ตาม CSS Selector ที่ให้มา")

driver.quit()
