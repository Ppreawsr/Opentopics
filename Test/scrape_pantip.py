import csv
import re
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ------------------------------
#  ฟังก์ชัน parse วัน-เวลา
# ------------------------------
def parse_relative_time(text: str):
    text = text.strip()
    unit_map = {
        "นาที": "minutes", "นาทีที่แล้ว": "minutes",
        "ชม.": "hours", "ชั่วโมง": "hours",
        "วัน": "days", "วินาที": "seconds",
        "วินาทีที่แล้ว": "seconds"
    }
    pattern = r"(\d+)\s*(นาที|ชม\.|ชั่วโมง|วัน|วินาที)(ที่แล้ว|ก่อน)?"
    m = re.search(pattern, text)
    if not m:
        return None

    amount_str = m.group(1)
    unit_thai = m.group(2)
    try:
        amount = int(amount_str)
        if amount > 999999:
            return None
    except:
        return None

    now = datetime.now()
    if unit_thai not in unit_map:
        return None
    time_unit = unit_map[unit_thai]

    if time_unit == "minutes":
        dt = now - timedelta(minutes=amount)
    elif time_unit == "hours":
        dt = now - timedelta(hours=amount)
    elif time_unit == "days":
        dt = now - timedelta(days=amount)
    elif time_unit == "seconds":
        dt = now - timedelta(seconds=amount)
    else:
        return None
    return dt

def parse_full_thai_datetime(text: str):
    text = text.strip()
    thai_months = {
        "มกราคม": 1, "ม.ค.": 1,
        "กุมภาพันธ์": 2, "ก.พ.": 2,
        "มีนาคม": 3, "มี.ค.": 3,
        "เมษายน": 4, "เม.ย.": 4,
        "พฤษภาคม": 5, "พ.ค.": 5,
        "มิถุนายน": 6, "มิ.ย.": 6,
        "กรกฎาคม": 7, "ก.ค.": 7,
        "สิงหาคม": 8, "ส.ค.": 8,
        "กันยายน": 9, "ก.ย.": 9,
        "ตุลาคม": 10, "ต.ค.": 10,
        "พฤศจิกายน": 11, "พ.ย.": 11,
        "ธันวาคม": 12, "ธ.ค.": 12
    }
    pattern = r"(\d{1,2})\s+([ก-ฮ.]+)\s+(\d{4})\s*(?:เวลา\s*(\d{1,2}):(\d{1,2})\s*น\.)?"
    m = re.search(pattern, text)
    if not m:
        return None

    day_str = m.group(1)
    month_thai = m.group(2)
    year_thai_str = m.group(3)
    hour_str = m.group(4)
    minute_str = m.group(5)

    if not hour_str:
        hour_str = "0"
    if not minute_str:
        minute_str = "0"

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
    year = year_thai - 543  # พ.ศ. -> ค.ศ.

    try:
        dt = datetime(year, month, day, hour, minute)
    except:
        return None
    return dt

def parse_thai_datetime(text: str):
    dt = parse_relative_time(text)
    if dt:
        return dt
    dt = parse_full_thai_datetime(text)
    if dt:
        return dt
    return None

def format_datetime(dt: datetime):
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def is_within_days(dt, max_days=5):
    if not dt:
        return False
    now = datetime.now()
    return (now - dt).days < max_days

# ---------------------------
# พารามิเตอร์ควบคุม
# ---------------------------
MAX_DAYS = 5
SCROLL_TIMES = 100  # เพิ่มรอบการเลื่อน
SCROLL_STEP_PX = 300
WAIT_SCROLL = 1.5

# ปิด log เกะกะ
chrome_options = Options()
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_argument('--log-level=3')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    driver.get("https://pantip.com/tag/หุ้น")
    time.sleep(3)

    print(f"🔽 Scroll by {SCROLL_STEP_PX}px, for {SCROLL_TIMES} times ...")
    for i in range(SCROLL_TIMES):
        driver.execute_script(f"window.scrollBy(0, {SCROLL_STEP_PX});")
        time.sleep(WAIT_SCROLL)

    # ดึงข้อมูลโพสต์
    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one("#__next > div > div > div > div.container > div:nth-child(6) > div.col-lg-8")
    all_post_links = []
    if container:
        posts = container.select("li.pt-list-item")
        print(f"🔎 พบ {len(posts)} posts ทั้งหมด (ยังไม่กรองตามวัน)")
        for p in posts:
            link_tag = p.select_one("div.pt-list-item__title a")
            date_tag = p.select_one("div.pt-list-item__info")
            if link_tag and date_tag:
                href = link_tag.get("href")
                date_str = date_tag.get_text(strip=True)
                dt_obj = parse_thai_datetime(date_str)
                if dt_obj and is_within_days(dt_obj, MAX_DAYS):
                    full_url = href if href.startswith("http") else ("https://pantip.com" + href)
                    all_post_links.append(full_url)
    else:
        print("❌ ไม่เจอ container หลักในหน้า")

    print(f"✅ ได้โพสต์ภายใน {MAX_DAYS} วัน: {len(all_post_links)} ลิงก์")

    if not all_post_links:
        print("ไม่มีโพสต์ในช่วงเวลาที่ต้องการ")
    else:
        with open("pantip_data_5days.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["post_id", "type", "day", "datetime", "title", "content", "author"])

            for i, link in enumerate(all_post_links, start=1):
                driver.get(link)
                time.sleep(2)
                post_soup = BeautifulSoup(driver.page_source, "html.parser")

                title_tag = post_soup.select_one("title")
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                post_dt_div = post_soup.select_one("div.display-post-status-leftside")
                dt_str = post_dt_div.get_text(strip=True) if post_dt_div else ""
                post_dt_obj = parse_thai_datetime(dt_str)
                day_str = dt_obj.strftime('%Y-%m-%d') if dt_obj else "N/A"
                final_dt_str = format_datetime(dt_obj)

                author_tag = post_soup.select_one(".display-post-name")
                author = author_tag.get_text(strip=True) if author_tag else "Unknown"

                writer.writerow([link, "post", day_str, final_dt_str, title, "โพสต์หลัก", author])

        print("\n🎉 เสร็จสิ้น! บันทึกข้อมูลลงไฟล์ 'pantip_data_5days.csv'")

finally:
    driver.quit()
    print("ปิดเบราว์เซอร์เรียบร้อย")
