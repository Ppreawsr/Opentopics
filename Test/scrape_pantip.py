import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# ตั้งค่า Selenium WebDriver (ใช้ Chrome)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# เปิดหน้าเว็บ Pantip ที่มี tag "หุ้น"
main_url = "https://pantip.com/tag/หุ้น"
driver.get(main_url)
time.sleep(5)  # รอให้หน้าเว็บโหลดข้อมูล

# ดึง HTML ที่ render แล้วจากหน้าเว็บหลัก
main_html = driver.page_source
soup = BeautifulSoup(main_html, "html.parser")

# เลือก container ที่ต้องการ โดยใช้ selector ที่เจาะจงตามที่ระบุ
container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
if container:
    # จาก container นี้ ดึงโพสต์แต่ละอัน โดยโพสต์อยู่ใน <li class="pt-list-item">
    posts = container.select("li.pt-list-item")
    print("จำนวนโพสต์ที่พบใน container ที่เลือก:", len(posts))
else:
    print("ไม่พบ container ตาม CSS Selector ที่กำหนด")
    driver.quit()
    exit()

# เปิดไฟล์ CSV เพื่อบันทึกข้อมูล (UTF-8 รองรับภาษาไทย)
with open("pantip_data.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["ชื่อกระทู้", "วันที่", "เวลา", "เนื้อหาที่คุย"])
    
    # วนลูปแต่ละโพสต์ใน container ที่เลือก
    for post in posts:
        # ดึงหัวข้อและลิงก์จาก <div class="pt-list-item__title"> ภายใน <a>
        title_tag = post.select_one("div.pt-list-item__title a")
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href")
            print("หัวข้อ:", title)
            print("ลิงก์:", link)
            
            # เข้าไปในโพสต์แต่ละอันเพื่อดึงข้อมูลรายละเอียด
            driver.get(link)
            time.sleep(5)  # รอให้หน้ากระทู้โหลดข้อมูลครบถ้วน
            topic_html = driver.page_source
            soup_topic = BeautifulSoup(topic_html, "html.parser")
            
            # ดึงข้อมูลวันที่และเวลา
            # ตัวอย่าง: ค้นหา <span> ที่มี attribute "title" ซึ่งบรรจุข้อมูลวันที่และเวลา
            date_part = "ไม่พบวันที่"
            time_part = "ไม่พบเวลา"
            datetime_span = soup_topic.find("span", title=True)
            if datetime_span:
                datetime_str = datetime_span.get("title")
                if "เวลา" in datetime_str:
                    parts = datetime_str.split("เวลา")
                    date_part = parts[0].strip()
                    time_part = parts[1].strip()
                else:
                    date_part = datetime_str
            
            # ดึงเนื้อหาของโพสต์ (ต้นฉบับและความคิดเห็น)
            original_content = ""
            original_div = soup_topic.find("div", class_="pt-topic-content")
            if original_div:
                original_content = original_div.get_text(separator=" ", strip=True)
            
            # ดึงความคิดเห็น (ตัวอย่างใช้ class "display-comment")
            comments = soup_topic.find_all("div", class_="display-comment")
            comments_content = "\n".join(comment.get_text(separator=" ", strip=True) for comment in comments)
            
            # รวมเนื้อหาต้นฉบับและความคิดเห็นเข้าด้วยกัน
            discussion_content = original_content + "\n" + comments_content
            
            # บันทึกข้อมูลลง CSV
            writer.writerow([title, date_part, time_part, discussion_content])
            
            print("วันที่:", date_part, "เวลา:", time_part)
            print("=" * 50)
            
            # หลังจากประมวลผลโพสต์แล้ว กลับไปที่หน้าเว็บหลัก tag "หุ้น"
            driver.get(main_url)
            time.sleep(5)
            # อัพเดต HTML จากหน้าเว็บหลัก และเลือก container ใหม่อีกครั้ง
            main_html = driver.page_source
            soup = BeautifulSoup(main_html, "html.parser")
            container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
            if container:
                posts = container.select("li.pt-list-item")
            else:
                print("ไม่พบ container หลังกลับไปที่หน้าเว็บหลัก")
                break

driver.quit()
