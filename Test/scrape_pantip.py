import csv
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ------------------------
# ฟังก์ชันช่วยคำนวณ datetime จากข้อความเช่น "20 นาทีที่แล้ว", "3 ชั่วโมงที่แล้ว", "1 วันก่อน" ฯลฯ
# ถ้า parse ไม่ได้ จะ return None
# ------------------------
def parse_relative_time(text: str):
    """
    ตัวอย่างข้อความที่ Pantip อาจแสดง:
    - "20 นาทีที่แล้ว"
    - "3 ชั่วโมงที่แล้ว"
    - "1 วันก่อน"
    - "19 ชั่วโมงที่แล้ว"
    """
    # ลบช่องว่างและเว้นวรรคเกิน
    text = text.strip()

    # เตรียม mapping ภาษาไทย -> timedelta
    unit_map = {
        "นาที": "minutes",
        "ชั่วโมง": "hours",
        "วัน": "days"
    }

    # ใช้ regex เพื่อจับ (ตัวเลข) + (หน่วย) + "ที่แล้ว" หรือ "ก่อน"
    # ตัวอย่าง: "(\d+)\s*(นาที|ชั่วโมง|วัน).*"  => group(1)=จำนวน, group(2)=หน่วย
    pattern = r"(\d+)\s*(นาที|ชั่วโมง|วัน)(ที่แล้ว|ก่อน)?"
    match = re.search(pattern, text)
    if not match:
        return None  # parse ไม่ได้

    number_str = match.group(1)
    unit_thai = match.group(2)

    # แปลงเป็น int
    try:
        amount = int(number_str)
    except:
        return None

    # ดูว่าเป็นหน่วยไหน
    if unit_thai not in unit_map:
        return None

    now = datetime.now()
    if unit_map[unit_thai] == "minutes":
        real_time = now - timedelta(minutes=amount)
    elif unit_map[unit_thai] == "hours":
        real_time = now - timedelta(hours=amount)
    elif unit_map[unit_thai] == "days":
        real_time = now - timedelta(days=amount)
    else:
        return None

    return real_time

# ------------------------
# ฟังก์ชันแปลง datetime -> string สวย ๆ
# ------------------------
def format_datetime(dt: datetime):
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# ------------------------
# เริ่มโค้ดหลัก
# ------------------------
# จำนวนโพสต์สูงสุดที่ต้องการดึงจากหน้าแท็ก "หุ้น"
MAX_POSTS = 20

# ตั้งค่า Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # 1) เปิดหน้าเว็บหลักที่มี tag "หุ้น"
    main_url = "https://pantip.com/tag/หุ้น"
    driver.get(main_url)
    time.sleep(5)  # รอให้หน้าเว็บโหลดข้อมูล

    # ดึง HTML ของหน้าเว็บหลัก
    main_html = driver.page_source
    soup = BeautifulSoup(main_html, "html.parser")

    # หา container หลักที่เก็บรายการโพสต์
    container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
    if not container:
        print("❌ ไม่พบ container ในหน้า tag 'หุ้น'")
        driver.quit()
        exit()

    # 2) ดึงโพสต์จาก container
    posts = container.select("li.pt-list-item")[:MAX_POSTS]
    print(f"🔎 พบโพสต์ทั้งหมด {len(posts)} โพสต์แรกในหน้า tag 'หุ้น'")

    # เตรียมไฟล์ CSV
    with open("pantip_data_hun.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # คอลัมน์ตัวอย่าง: [ประเภท, ชื่อกระทู้, วัน-เวลาจริง, เนื้อหา]
        # type = "post" หรือ "comment"
        # ในกรณี post, "ชื่อกระทู้" คือชื่อ
        # ในกรณี comment, "ชื่อกระทู้" เราอาจใส่ "-" หรือใส่ชื่อเดิมก็ได้
        writer.writerow(["type", "title", "datetime", "content"])

        # 3) วนลูปแต่ละโพสต์
        for idx, post in enumerate(posts, start=1):
            # ดึงหัวข้อและลิงก์ของแต่ละโพสต์
            title_tag = post.select_one("div.pt-list-item__title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href")

            print(f"\n✨ ดึงข้อมูลโพสต์ที่ {idx}/{len(posts)}: {title}")
            driver.get(link)
            time.sleep(5)  # รอให้กระทู้โหลด

            post_html = driver.page_source
            soup_post = BeautifulSoup(post_html, "html.parser")

            # === (A) ดึง "วันที่/เวลา" ของโพสต์หลัก (ถ้าเป็น "19 ชั่วโมงที่แล้ว" จะ parse)
            date_tag = soup_post.select_one("div.display-post-status-leftside")
            dt_string = date_tag.get_text(strip=True) if date_tag else ""
            real_dt = parse_relative_time(dt_string)  # ถ้าสำเร็จจะได้ datetime, ไม่งั้น None
            real_dt_str = format_datetime(real_dt)

            # === (B) ดึงเนื้อหาของโพสต์หลัก
            post_content_tag = soup_post.select_one("div.display-post-story")
            post_content = post_content_tag.get_text(separator=" ", strip=True) if post_content_tag else "ไม่พบเนื้อหากระทู้"

            # 4) บันทึก row ประเภท "post"
            writer.writerow(["post", title, real_dt_str, post_content])

            # === (C) ดึงคอมเมนต์ทั้งหมด
            comments_wrappers = soup_post.select("div.display-post-wrapper.section-comment")
            # วนลูปแต่ละคอมเมนต์
            for comment in comments_wrappers:
                # 4.1 ดึงเนื้อหา comment
                # อยู่ใน div.display-post-story-wrapper.comment-wrapper > div.display-post-story
                c_story_tag = comment.select_one("div.display-post-story")
                c_content = c_story_tag.get_text(separator=" ", strip=True) if c_story_tag else "ไม่พบเนื้อหาคอมเมนต์"

                # 4.2 ดึงวันที่/เวลา comment (ถ้ามี)
                # ส่วนใหญ่อยู่ใน "div.display-post-status-leftside" เช่นเดียวกับตัวโพสต์
                c_dt_tag = comment.select_one("div.display-post-status-leftside")
                c_dt_string = c_dt_tag.get_text(strip=True) if c_dt_tag else ""
                c_real_dt = parse_relative_time(c_dt_string)
                c_real_dt_str = format_datetime(c_real_dt)

                # 4.3 บันทึกลง CSV: type=comment
                writer.writerow(["comment", title, c_real_dt_str, c_content])

            print(f"📝 ชื่อกระทู้: {title}")
            print(f"🕒 วัน-เวลาโพสต์: {real_dt_str}")
            print(f"📖 เนื้อหากระทู้ (สั้นๆ): {post_content[:80]}...")
            print(f"💬 จำนวนคอมเมนต์: {len(comments_wrappers)}")

finally:
    driver.quit()
    print("\n🎉 เสร็จสิ้นแล้ว! ข้อมูลถูกบันทึกในไฟล์ 'pantip_data_hun.csv'")

