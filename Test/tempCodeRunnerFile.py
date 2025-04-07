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
# ฟังก์ชัน parse_full_thai_datetime (ของเดิม)
# ------------------------------
def parse_full_thai_datetime(text: str):
    text = text.replace("\xa0"," ").replace("\r","").strip()

    def normalize_month(m_str: str):
        alias = {
            "เมย": "เม.ย.",
            "เมย.": "เม.ย.",
            "เม.ย": "เม.ย.",
            "เม.ย.": "เม.ย."
        }
        return alias.get(m_str, m_str)

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
            month = thai_months.get(raw_month)
            if not month:
                return None

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

    # รูปแบบไม่มีปี
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
            year = now.year
            hour = now.hour
            minute = now.minute
            return datetime(year, month, int(day_str), hour, minute)
        except:
            return None

    return None


def parse_thai_datetime(text: str):
    """
    เลิกใช้ parse_relative_time (แบบนับเป็นนาที ชั่วโมง วัน) 
    แล้วใช้เฉพาะ parse_full_thai_datetime แทน 
    เพื่อให้ยังมีการเก็บ datetime บางส่วนได้ 
    (หรือจะตัดทิ้งเลยก็ได้)
    """
    dt = parse_full_thai_datetime(text)
    return dt

def format_datetime(dt: datetime):
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


#################### MAIN SCRIPT ####################

MAX_SCROLLS = 10       # จำนวนรอบการ scroll สูงสุด (ปรับตามต้องการ)
SCROLL_STEP_PX = 300
WAIT_SCROLL = 2.5

# กำหนดจำนวนข้อมูลรวม (post + comment) ที่ต้องการ (อย่างน้อย) ให้ครบ 6000
MAX_DATA = 6000

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
    all_post_links = []

    while scroll_count < MAX_SCROLLS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(WAIT_SCROLL)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # หากเลื่อนแล้วไม่ขยับ แสดงว่าอาจไม่มีโพสต์เพิ่มเติม
            break
        last_height = new_height
        scroll_count += 1

        # หลังจาก scroll แต่ละครั้ง ให้ดึงลิงก์โพสต์ใหม่ที่อาจโหลดเพิ่มมา
        soup = BeautifulSoup(driver.page_source, "html.parser")
        container = soup.select_one("div.container div.col-lg-8")
        if container:
            posts = container.select("li.pt-list-item")
            for p in posts:
                link_tag = p.select_one("div.pt-list-item__title a")
                if link_tag:
                    href = link_tag.get("href")
                    # ทำให้เป็น full url
                    full_url = href if href.startswith("http") else ("https://pantip.com" + href)
                    if full_url not in all_post_links:
                        all_post_links.append(full_url)

        # หากจำนวนลิงก์กระทู้มากพอ อาจ break ได้ (แต่ส่วนใหญ่ก็จะเอาไว้เยอะๆ)
        # if len(all_post_links) > บางตัวเลข: break

    print(f"✅ ได้โพสต์ทั้งหมด {len(all_post_links)} ลิงก์ (ยังไม่การันตีว่าจะมีคอมเมนต์ 6000)")

    if not all_post_links:
        print("❌ ไม่พบบทความในหน้าแท็กหุ้น หรือดึงลิงก์ไม่สำเร็จ")
    else:
        # 2) เข้ากระทู้แต่ละโพสต์ > ดึงข้อมูล โพสต์หลัก + คอมเมนต์
        total_rows = 0
        with open("pantip_data_6000.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["post_id","type","day","datetime","title","content","author","raw_date"])

            for link in all_post_links:
                if total_rows >= MAX_DATA:
                    # ครบตามที่ต้องการแล้ว
                    break

                # เปิดกระทู้
                driver.get(link)
                time.sleep(2)

                # scroll ภายในกระทู้เพิ่ม เพื่อโหลดคอมเมนต์ทั้งหมด
                post_scroll_count = 0
                last_h = driver.execute_script("return document.body.scrollHeight")
                while post_scroll_count < 10:
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
                total_rows += 1
                if total_rows >= MAX_DATA:
                    break

                # ---- ดึง comment ----
                comment_blocks = post_soup.select("div[id^='comment-']")
                # print(f"🗨️ {link} => คอมเมนต์ {len(comment_blocks)} อัน")
                for c in comment_blocks:
                    if total_rows >= MAX_DATA:
                        break

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
                    total_rows += 1

        print(f"\n🎉 เสร็จสิ้น! บันทึกข้อมูลลงไฟล์ 'pantip_data_6000.csv' ทั้งหมด {total_rows} แถว")
finally:
    driver.quit()
    print("ปิดเบราว์เซอร์เรียบร้อย")
