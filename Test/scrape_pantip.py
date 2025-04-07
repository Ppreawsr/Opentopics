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
# ฟังก์ชัน parse วัน-เวลา
# ------------------------------
def parse_relative_time(text: str):
    """
    เช่น "3 ชั่วโมงที่แล้ว", "15 นาทีที่แล้ว"
    คืน datetime.now() - timedelta(...) ได้เลย
    """
    text = text.replace("\xa0", " ").replace("\r", "").strip()

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

    try:
        amount = int(m.group(1))
        if amount > 999999:
            return None
    except:
        return None

    now = datetime.now()
    unit_thai = m.group(2)
    time_unit = unit_map.get(unit_thai)
    if not time_unit:
        return None

    return now - timedelta(**{time_unit: amount})

def parse_full_thai_datetime(text: str):
    """
    รองรับ:
      - "5 เม.ย." / "5 เมย" / "6 เม.ย" 
      - "6 เม.ย. 2566", "6 เม.ย. 66 (ปี 2 หลัก)"
      - optional เวลา "เวลา 12:30 น."
    """
    text = text.replace("\xa0"," ").replace("\r","").strip()

    # 1) normalize month
    def normalize_month(m_str: str):
        # ช่วย fix เคสเช่น "เมย", "เม.ย", "เม.ย." 
        # ให้กลายเป็น "เม.ย." เพื่อแมป dict
        m_str = m_str.strip()
        alias = {
            "เมย": "เม.ย.",
            "เมย.": "เม.ย.",
            "เม.ย": "เม.ย.",
            "เม.ย.": "เม.ย."  # สุดท้ายให้เหลือ "เม.ย."
        }
        return alias.get(m_str, m_str)

    # dict ไทย -> month
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

    # รูปแบบมีปี => ex. "6 เม.ย. 2566" หรือ "6 เม.ย. 66"
    pattern_full = r"(\d{1,2})\s+([ก-ฮ.]+)\s+(\d{2,4})\s*(?:เวลา\s*(\d{1,2}):(\d{1,2})\s*น\.)?"
    m = re.search(pattern_full, text)
    if m:
        try:
            day_str = m.group(1)
            raw_month = normalize_month(m.group(2))
            year_str = m.group(3)
            hour_str = m.group(4)
            minute_str = m.group(5)

            day = int(day_str)

            # แปลงเดือน
            month = thai_months.get(raw_month)
            if not month:
                return None

            # ถ้า len(year_str)=2 => บวก 2500
            if len(year_str) == 2:
                year_thai = 2500 + int(year_str)
            else:
                year_thai = int(year_str)

            year = year_thai - 543
            hour = int(hour_str) if hour_str else 0
            minute = int(minute_str) if minute_str else 0
            return datetime(year, month, day, hour, minute)
        except:
            return None

    # รูปแบบไม่มีปี => "6 เม.ย.", "6 เมย", "6 เม.ย"
    pattern_no_year = r"(\d{1,2})\s+([ก-ฮ.]+)"
    m = re.search(pattern_no_year, text)
    if m:
        try:
            day_str = m.group(1)
            raw_month = normalize_month(m.group(2))
            month = thai_months.get(raw_month)
            if not month:
                return None
            now = datetime.now()
            # สมมติเป็นปีปัจจุบัน
            year = now.year
            hour = now.hour
            minute = now.minute
            return datetime(year, month, int(day_str), hour, minute)
        except:
            return None

    return None

def parse_thai_datetime(text: str):
    """
    รวม parse_relative_time กับ parse_full_thai_datetime
    """
    dt = parse_relative_time(text)
    if dt:
        return dt
    dt = parse_full_thai_datetime(text)
    return dt

def format_datetime(dt: datetime):
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def is_within_days(dt, max_days=5):
    if not dt:
        return False
    return (datetime.now() - dt).days <= max_days

# ---------------------------
# พารามิเตอร์ควบคุม
# ---------------------------
MAX_DAYS = 5
SCROLL_STEP_PX = 300
WAIT_SCROLL = 2.5  
MAX_SCROLLS = 15   # scroll หน้า tag
MAX_SCROLLS_POST = 10 # scroll ในกระทู้

chrome_options = Options()
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_argument('--log-level=3')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 1) เข้า TAG 'หุ้น'
    driver.get("https://pantip.com/tag/%E0%B8%AB%E0%B8%B8%E0%B9%89%E0%B8%99")
    time.sleep(3)

    print(f"🔽 Scroll page up to {MAX_SCROLLS} times ...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < MAX_SCROLLS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(WAIT_SCROLL)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1

    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one("div.container div.col-lg-8")
    all_post_links = []
    if container:
        posts = container.select("li.pt-list-item")
        print(f"🔎 พบ {len(posts)} posts (ยังไม่กรองวัน)")
        for p in posts:
            link_tag = p.select_one("div.pt-list-item__title a")
            date_tag = p.select_one("div.pt-list-item__info > span")
            if link_tag and date_tag:
                href = link_tag.get("href")
                date_str = date_tag.get_text(strip=True)
                dt_obj = parse_thai_datetime(date_str)

                # Debug
                print(f"🕓 date_str='{date_str}' => {dt_obj}")

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
            writer.writerow(["post_id","type","day","datetime","title","content","author","raw_date"])

            # 2) เข้าแต่ละโพสต์ => scroll ภายใน => ดึงข้อมูล
            for link in all_post_links:
                driver.get(link)
                time.sleep(2)

                # scroll ในกระทู้
                post_scroll_count = 0
                last_h = driver.execute_script("return document.body.scrollHeight")
                while post_scroll_count < MAX_SCROLLS_POST:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)
                    new_h = driver.execute_script("return document.body.scrollHeight")
                    if new_h == last_h:
                        break
                    last_h = new_h
                    post_scroll_count += 1

                post_soup = BeautifulSoup(driver.page_source, "html.parser")

                # ---- โพสต์หลัก ----
                title_tag = post_soup.select_one("title")
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                post_dt_div = post_soup.select_one("div.display-post-status-leftside")
                dt_str = post_dt_div.get_text(strip=True) if post_dt_div else ""
                post_dt_obj = parse_thai_datetime(dt_str)
                day_str = post_dt_obj.strftime('%Y-%m-%d') if post_dt_obj else "N/A"
                final_dt_str = format_datetime(post_dt_obj)

                author_tag = post_soup.select_one(".display-post-name")
                author = author_tag.get_text(strip=True) if author_tag else "Unknown"

                writer.writerow([link, "post", day_str, final_dt_str, title, "โพสต์หลัก", author, dt_str])

                # ---- ดึง comment ----
                comment_blocks = post_soup.select("div[id^='comment-']")
                print(f"🗨️ {link} => คอมเมนต์ {len(comment_blocks)} อัน")
                for c in comment_blocks:
                    # เวลา
                    time_div = c.select_one("div.display-post-status-leftside")
                    comment_time_str = time_div.get_text(strip=True) if time_div else ""
                    c_dt_obj = parse_thai_datetime(comment_time_str)
                    c_day = c_dt_obj.strftime('%Y-%m-%d') if c_dt_obj else "N/A"
                    c_final_dt = format_datetime(c_dt_obj)

                    content_div = c.select_one("div.display-post-message")
                    comment_text = content_div.get_text(strip=True) if content_div else "N/A"

                    c_author_tag = c.select_one(".display-post-name")
                    c_author = c_author_tag.get_text(strip=True) if c_author_tag else "Unknown"

                    writer.writerow([link, "comment", c_day, c_final_dt, title, comment_text, c_author, comment_time_str])

        print("\n🎉 เสร็จสิ้น! บันทึกข้อมูลลงไฟล์ 'pantip_data_5days.csv'")

finally:
    driver.quit()
    print("ปิดเบราว์เซอร์เรียบร้อย")
