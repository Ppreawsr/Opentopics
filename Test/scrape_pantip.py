import csv
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def parse_thai_date(date_str):
    """
    แปลงสตริงวันที่ภาษาไทยจาก attribute "title"
    ตัวอย่าง: "21 กุมภาพันธ์ 2568 เวลา 05:46 น." 
    คืนค่าเป็น (date, time) ในรูปแบบ datetime.date และ datetime.time
    """
    parts = date_str.split("เวลา")
    if len(parts) < 2:
        return None, None
    date_part = parts[0].strip()  # เช่น "21 กุมภาพันธ์ 2568"
    time_part = parts[1].strip()  # เช่น "05:46 น."
    
    # ลบ "น." ออก
    time_part = time_part.replace("น.", "").strip()
    
    tokens = date_part.split()
    if len(tokens) != 3:
        return None, None
    try:
        day = int(tokens[0])
    except:
        return None, None
    month_thai = tokens[1]
    try:
        year_thai = int(tokens[2])
    except:
        return None, None
    
    # แผนที่เดือนภาษาไทย
    thai_months = {
        "มกราคม": 1,
        "กุมภาพันธ์": 2,
        "มีนาคม": 3,
        "เมษายน": 4,
        "พฤษภาคม": 5,
        "มิถุนายน": 6,
        "กรกฎาคม": 7,
        "สิงหาคม": 8,
        "กันยายน": 9,
        "ตุลาคม": 10,
        "พฤศจิกายน": 11,
        "ธันวาคม": 12
    }
    month = thai_months.get(month_thai, 0)
    if month == 0:
        return None, None
    # แปลงปี พ.ศ. เป็น ค.ศ.
    year = year_thai - 543
    
    try:
        hour, minute = map(int, time_part.split(":"))
    except:
        hour, minute = 0, 0
    
    dt = datetime.datetime(year, month, day, hour, minute)
    return dt.date(), dt.time()

# ตั้งค่า Selenium WebDriver (ใช้ Chrome)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# เปิดหน้าเว็บ Pantip ที่มี tag "หุ้น"
main_url = "https://pantip.com/tag/หุ้น"
driver.get(main_url)
time.sleep(5)  # รอให้หน้าเว็บโหลดข้อมูลครบถ้วน

# ดึง HTML ที่ render แล้วจากหน้าเว็บหลัก
main_html = driver.page_source
soup = BeautifulSoup(main_html, "html.parser")

# เลือก container ที่ต้องการตาม selector ที่กำหนด
container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
if not container:
    print("ไม่พบ container ตาม CSS Selector ที่กำหนด")
    driver.quit()
    exit()

# ดึงโพสต์ภายใน container (โพสต์แต่ละอันอยู่ใน <li class="pt-list-item">)
posts = container.select("li.pt-list-item")
print("จำนวนโพสต์ใน container ที่เลือก:", len(posts))

# เตรียมไฟล์ CSV (ใช้ UTF-8 เพื่อรองรับภาษาไทย)
with open("pantip_data.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["ชื่อกระทู้", "วันที่", "เวลา", "เนื้อหาที่คุย"])
    
    # เก็บวันที่ปัจจุบัน (สำหรับเปรียบเทียบและกรณีโพสต์ relative)
    today = datetime.date.today()
    current_time = datetime.datetime.now().time()
    
    for post in posts:
        # ดึงข้อมูลวันที่-เวลา จาก <div class="pt-list-item__info"> <span>
        info_span = post.select_one("div.pt-list-item__info span")
        post_date = None
        post_time = None
        if info_span:
            if info_span.has_attr("title"):
                # หากมี attribute title ให้ใช้ parse_thai_date()
                date_str = info_span["title"]  # ควรได้แบบ "21 กุมภาพันธ์ 2568 เวลา 05:46 น."
                parsed_date, parsed_time = parse_thai_date(date_str)
                if parsed_date:
                    post_date = parsed_date
                    post_time = parsed_time
            else:
                # หากไม่มี attribute title แต่มีข้อความ relative เช่น "13 นาที" หรือ "1 ชั่วโมง"
                text = info_span.get_text(strip=True)
                if "นาที" in text or "ชั่วโมง" in text:
                    post_date = today
                    post_time = current_time
                else:
                    post_date = today
                    post_time = current_time
        if post_date is None:
            post_date = today
            post_time = current_time
        
        # ตรวจสอบว่าโพสต์นี้ไม่เกิน 5 วันย้อนหลัง
        delta_days = (today - post_date).days
        if delta_days > 1:
            print(f"โพสต์เก่าเกิน 5 วัน ({post_date} เป็น {delta_days} วันย้อนหลัง) หยุด scraping")
            break
        
        # ดึงหัวข้อและลิงก์จาก <div class="pt-list-item__title"> ภายใน <a>
        title_tag = post.select_one("div.pt-list-item__title a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")
        
        print("Processing:", title, link, post_date, post_time)
        
        # เข้าไปในโพสต์เพื่อดึงรายละเอียดเพิ่มเติม
        driver.get(link)
        time.sleep(5)
        topic_html = driver.page_source
        soup_topic = BeautifulSoup(topic_html, "html.parser")
        
        # ดึงเนื้อหาต้นฉบับจากโพสต์ (เช่น <div class="pt-topic-content">)
        original_div = soup_topic.find("div", class_="pt-topic-content")
        original_content = original_div.get_text(separator=" ", strip=True) if original_div else ""
        
        # ดึงความคิดเห็น (ลองหา element ที่มี class "display-comment")
        comments = soup_topic.find_all("div", class_="display-comment")
        comments_content = "\n".join(comment.get_text(separator=" ", strip=True) for comment in comments)
        
        discussion_content = original_content + "\n" + comments_content
        
        # บันทึกข้อมูลลง CSV โดยฟอร์แมตวันที่และเวลา
        writer.writerow([title, post_date.strftime("%d/%m/%Y"), post_time.strftime("%H:%M"), discussion_content])
        print("Scraped:", title)
        print("-" * 50)
        
        # หลังจาก scrape แล้ว กลับไปยังหน้าเว็บหลัก tag "หุ้น"
        driver.get(main_url)
        time.sleep(5)
        main_html = driver.page_source
        soup = BeautifulSoup(main_html, "html.parser")
        container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
        if container:
            posts = container.select("li.pt-list-item")
        else:
            print("ไม่พบ container หลังกลับไปที่หน้าเว็บหลัก")
            break

driver.quit()
