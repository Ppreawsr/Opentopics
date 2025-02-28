import csv
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def parse_relative_time(text: str):
    """
    แปลงข้อความเช่น "20 นาทีที่แล้ว", "3 ชั่วโมงที่แล้ว", "1 วันก่อน" -> datetime.now() - timedelta(...)
    ถ้า parse ไม่ได้ -> return None
    """
    text = text.strip()
    unit_map = {
        "นาที": "minutes",
        "ชั่วโมง": "hours",
        "วัน": "days"
    }
    pattern = r"(\d+)\s*(นาที|ชั่วโมง|วัน)(ที่แล้ว|ก่อน)?"
    m = re.search(pattern, text)
    if not m:
        return None
    number_str = m.group(1)
    unit_thai = m.group(2)

    try:
        amount = int(number_str)
    except:
        return None

    now = datetime.now()

    if unit_thai not in unit_map:
        return None

    if unit_map[unit_thai] == "minutes":
        real_time = now - timedelta(minutes=amount)
    elif unit_map[unit_thai] == "hours":
        real_time = now - timedelta(hours=amount)
    elif unit_map[unit_thai] == "days":
        real_time = now - timedelta(days=amount)
    else:
        return None

    return real_time


def format_datetime(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "N/A"


# -----------------------------------------------------------------------------
# ฟีเจอร์:
# 1) เก็บโพสต์ (type=post) + คอมเมนต์ (type=comment) คนละ row
# 2) ไม่จำกัดเวลารัน (pagination)
# 3) ใส่ emoji
# 4) parse เวลาจาก "xx นาทีที่แล้ว"
# 5) แก้ปัญหา str-capabilities ด้วย Service
# -----------------------------------------------------------------------------

MAX_POSTS = 20  # จำนวนโพสต์สูงสุด

# สร้าง WebDriver โดยใช้ Service object
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

try:
    page_url = "https://pantip.com/tag/หุ้น"
    total_scraped = 0
    all_posts = []

    while True:
        print(f"🔎 กำลังเข้า: {page_url}")
        driver.get(page_url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
        if not container:
            print("❌ ไม่พบ container ในหน้านี้, หยุดการทำงาน")
            break

        posts = container.select("li.pt-list-item")
        if not posts:
            print("❌ ไม่พบโพสต์ใด ๆ ในหน้านี้, หยุดการทำงาน")
            break

        for post in posts:
            if total_scraped >= MAX_POSTS:
                break

            title_tag = post.select_one("div.pt-list-item__title a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href")

            # ลอง parse วันเวลา จาก info span
            info_span = post.select_one("div.pt-list-item__info span")
            date_str = info_span.get("title") if info_span and info_span.has_attr("title") else ""
            dt_obj = parse_relative_time(date_str)

            all_posts.append((title, link, dt_obj))
            total_scraped += 1

        if total_scraped >= MAX_POSTS:
            break

        # หาปุ่มหน้าถัดไป
        next_btn = soup.select_one("a.pagination-next")
        if not next_btn:
            print("❌ ไม่มีหน้าถัดไปแล้ว, หยุดการทำงาน")
            break

        next_href = next_btn.get("href")
        if not next_href.startswith("http"):
            next_href = "https://pantip.com" + next_href

        page_url = next_href

    print(f"✨ รวมลิงก์ได้ {len(all_posts)} โพสต์, กำลังเก็บรายละเอียด...")

    # เปิดไฟล์ CSV
    with open("pantip_data_hun.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # คอลัมน์: [type, title, datetime, content]
        writer.writerow(["type", "title", "datetime", "content"])

        # วนลูปเข้าไปดูรายละเอียดแต่ละโพสต์ + เก็บคอมเมนต์
        for i, (title, link, dt_obj) in enumerate(all_posts, start=1):
            print(f"\n⚙️ [{i}/{len(all_posts)}] โพสต์: {title}")
            driver.get(link)
            time.sleep(3)

            post_soup = BeautifulSoup(driver.page_source, "html.parser")

            # (1) parse วันเวลาในโพสต์จริง
            post_dt_div = post_soup.select_one("div.display-post-status-leftside")
            dt_str2 = post_dt_div.get_text(strip=True) if post_dt_div else ""
            post_dt_obj = parse_relative_time(dt_str2)
            final_dt_str = format_datetime(post_dt_obj)

            # (2) เนื้อหาโพสต์
            post_content_div = post_soup.select_one("div.display-post-story")
            post_content = post_content_div.get_text(separator=" ", strip=True) if post_content_div else "ไม่พบเนื้อหาโพสต์"

            #  บันทึกโพสต์ (type=post)
            writer.writerow(["post", title, final_dt_str, post_content])

            # (3) เก็บคอมเมนต์
            comments = post_soup.select("div.display-post-wrapper.section-comment")
            print(f"💬 พบคอมเมนต์ {len(comments)} อัน")
            for c in comments:
                # parse เวลา comment
                c_dt_div = c.select_one("div.display-post-status-leftside")
                c_dt_str = c_dt_div.get_text(strip=True) if c_dt_div else ""
                c_dt_obj = parse_relative_time(c_dt_str)
                c_dt_final = format_datetime(c_dt_obj)

                # เนื้อหาคอมเมนต์
                c_content_div = c.select_one("div.display-post-story-wrapper.comment-wrapper div.display-post-story")
                c_content = c_content_div.get_text(separator=" ", strip=True) if c_content_div else "ไม่พบเนื้อหาคอมเมนต์"

                # บันทึก (type=comment)
                writer.writerow(["comment", title, c_dt_final, c_content])

    print("\n🎉 เสร็จสิ้น! ข้อมูลถูกบันทึกลงในไฟล์ 'pantip_data_hun.csv'")

finally:
    driver.quit()
    print("🚪 ปิดเบราว์เซอร์เรียบร้อย")
