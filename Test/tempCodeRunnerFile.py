import csv
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --------------------------------------------------
# ฟังก์ชัน parse ไทย datetime (2 รูปแบบ)
# 1) relative time เช่น "20 นาทีที่แล้ว"
# 2) full thai datetime เช่น "21 กุมภาพันธ์ 2568 เวลา 05:46 น."
# --------------------------------------------------
def parse_thai_datetime(text: str):
    text = text.strip()
    dt = parse_relative_time(text)
    if dt:
        return dt
    dt = parse_full_thai_datetime(text)
    if dt:
        return dt
    return None

def parse_relative_time(text: str):
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
        if amount > 999999:
            return None
    except:
        return None

    now = datetime.now()
    if unit_thai not in unit_map:
        return None

    if unit_map[unit_thai] == "minutes":
        dt = now - timedelta(minutes=amount)
    elif unit_map[unit_thai] == "hours":
        dt = now - timedelta(hours=amount)
    elif unit_map[unit_thai] == "days":
        dt = now - timedelta(days=amount)
    else:
        return None
    return dt

def parse_full_thai_datetime(text: str):
    text = text.strip()
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
    pattern = r"(\d{1,2})\s+([ก-ฮ]+)\s+(\d{4})\s*เวลา\s*(\d{1,2}):(\d{1,2})\s*น\."
    m = re.search(pattern, text)
    if not m:
        return None
    day_str = m.group(1)
    month_thai = m.group(2)
    year_thai_str = m.group(3)
    hour_str = m.group(4)
    minute_str = m.group(5)
    try:
        day = int(day_str)
        year_thai = int(year_thai_str)
        hour = int(hour_str)
        minute = int(minute_str)
    except:
        return None

    if month_thai not in thai_months:
        return None

    month = thai_months[month_thai]
    year = year_thai - 543  # แปลง พ.ศ. -> ค.ศ.

    try:
        dt = datetime(year, month, day, hour, minute)
    except:
        return None
    return dt

def format_datetime(dt: datetime):
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------
# โค้ดหลัก: Infinite Scroll หน้า tag "หุ้น", จนได้ MAX_POSTS
# แยก (post/comment) ลง CSV, ใส่อิโมจิ
# --------------------------------------------------
MAX_POSTS = 80  # จำนวนโพสต์ที่ต้องการ 
## โควต้าจำกับจำนวนวัน
    
SCROLL_PAUSE = 3  # วินาทีที่รอหลัง scroll
MAX_SCROLL_NO_CHANGE = 5  # หาก scroll n ครั้งแล้วไม่มีโพสต์เพิ่ม -> หยุด

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

try:
    # 1) เข้าไปที่ tag "หุ้น"
    start_url = "https://pantip.com/tag/หุ้น"
    driver.get(start_url)
    time.sleep(5)

    all_post_links = []
    old_len = 0
    scroll_no_change = 0

    # 2) วน infinite scroll
    while True:
        print("🔎 Scroll หน้า tag 'หุ้น' ...")
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # หาโพสต์
        container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
        if not container:
            print("❌ ไม่พบ container")
            break

        posts = container.select("li.pt-list-item")
        for p in posts:
            link_tag = p.select_one("div.pt-list-item__title a")
            if link_tag:
                href = link_tag.get("href")
                if href not in all_post_links:
                    all_post_links.append(href)

        # เช็คว่าเก็บได้ครบตามต้องการหรือยัง
        if len(all_post_links) >= MAX_POSTS:
            break

        # scroll ลงสุด
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)

        # ถ้าเลื่อนแล้วจำนวน link ไม่เพิ่ม -> scroll_no_change++
        new_len = len(all_post_links)
        if new_len == old_len:
            scroll_no_change += 1
            print(f"✨ ไม่พบโพสต์ใหม่ (scroll_no_change={scroll_no_change})")
            if scroll_no_change >= MAX_SCROLL_NO_CHANGE:
                print("❌ หยุดเพราะ scroll หลายครั้งแล้วไม่มีโพสต์เพิ่ม")
                break
        else:
            scroll_no_change = 0
        old_len = new_len

    # ตัดให้เหลือตาม MAX_POSTS
    all_post_links = all_post_links[:MAX_POSTS]
    print(f"✨ รวมได้ {len(all_post_links)} โพสต์")

    # 3) เข้าไปดึงรายละเอียดในแต่ละลิงก์
    with open("pantip_data_hun.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "title", "datetime", "content"])

        for i, link in enumerate(all_post_links, start=1):
            full_url = link if link.startswith("http") else ("https://pantip.com" + link)
            print(f"\n⚙️ [{i}/{len(all_post_links)}] เข้าโพสต์: {full_url}")
            driver.get(full_url)
            time.sleep(3)

            post_soup = BeautifulSoup(driver.page_source, "html.parser")

            # ชื่อกระทู้
            title_tag = post_soup.select_one("title")
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            # วัน-เวลาโพสต์
            post_dt_div = post_soup.select_one("div.display-post-status-leftside")
            dt_str = post_dt_div.get_text(strip=True) if post_dt_div else ""
            post_dt_obj = parse_thai_datetime(dt_str)
            final_dt_str = format_datetime(post_dt_obj)

            # เนื้อหาโพสต์
            post_content_div = post_soup.select_one("div.display-post-story")
            post_content = post_content_div.get_text(separator=" ", strip=True) if post_content_div else "ไม่พบเนื้อหาโพสต์"

            # บันทึก row (type=post)
            writer.writerow(["post", title, final_dt_str, post_content])

            # 4) ดึงคอมเมนต์
            comments = post_soup.select("div.display-post-wrapper.section-comment")
            print(f"💬 พบคอมเมนต์ {len(comments)} อัน")
            for c in comments:
                c_dt_div = c.select_one("div.display-post-status-leftside")
                c_dt_str = c_dt_div.get_text(strip=True) if c_dt_div else ""
                c_dt_obj = parse_thai_datetime(c_dt_str)
                c_dt_final = format_datetime(c_dt_obj)

                c_content_div = c.select_one("div.display-post-story-wrapper.comment-wrapper div.display-post-story")
                c_content = c_content_div.get_text(separator=" ", strip=True) if c_content_div else "ไม่พบเนื้อหาคอมเมนต์"

                writer.writerow(["comment", title, c_dt_final, c_content])

    print("\n🎉 เสร็จสิ้น! ได้ทั้งหมด", len(all_post_links), "โพสต์, บันทึกลง 'pantip_data_hun.csv'")

finally:
    driver.quit()
    print("ปิดเบราว์เซอร์เรียบร้อย")
