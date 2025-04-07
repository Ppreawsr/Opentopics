import csv
import re
import time
from datetime import datetime, timedelta

# --- Selenium ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- BeautifulSoup ---
from bs4 import BeautifulSoup

# --- Progress bar ---
from tqdm import tqdm

## ประมวลผลวัน-เวลาของ Pantip

def parse_relative_time(text: str):
    """
    เช่น "3 ชั่วโมงที่แล้ว", "15 นาทีที่แล้ว", "2 วันก่อน"
    คืน datetime.now() - timedelta(...) ได้เลย
    ถ้า parse ไม่ได้ ให้ return None
    """
    text = text.replace("\xa0", " ").replace("\r", "").strip()

    unit_map = {
        "นาที": "minutes", "นาทีที่แล้ว": "minutes",
        "ชม.": "hours", "ชั่วโมง": "hours",
        "วัน": "days",
        "วินาที": "seconds", "วินาทีที่แล้ว": "seconds"
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
      - "6 เม.ย. 2566", "6 เม.ย. 66"
      - ออปชัน "เวลา 12:30 น."
    ถ้าทำไม่ได้ return None
    """
    text = text.replace("\xa0"," ").replace("\r","").strip()

    # normalize ชื่อเดือน
    def normalize_month(m_str: str):
        alias = {
            "เมย": "เม.ย.",
            "เมย.": "เม.ย.",
            "เม.ย": "เม.ย.",
            "เม.ย.": "เม.ย."
        }
        return alias.get(m_str, m_str)

    # dict แปลงชื่อเดือนไทย -> ตัวเลข
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

    # รูปแบบมีปี
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

    # รูปแบบไม่มีปี => "5 เม.ย."
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
    รวมการ parse ทั้ง relative time และ full Thai datetime
    """
    if not text:
        return None

    # ลองแบบ relative ก่อน
    dt_rel = parse_relative_time(text)
    if dt_rel:
        return dt_rel

    # ถ้าไม่ match, ลอง parse เต็ม
    dt_full = parse_full_thai_datetime(text)
    if dt_full:
        return dt_full

    return None


def format_datetime(dt: datetime):
    """แปลง datetime เป็น string"""
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


############################################################################
# ฟังก์ชัน scroll ภายในกระทู้
############################################################################

def scroll_in_post(driver, scroll_times=10, wait_sec=1.5):
    """
    เลื่อนในหน้ากระทู้ Pantip เพื่อโหลดคอมเมนต์ให้ครบ
    """
    last_h = driver.execute_script("return document.body.scrollHeight")
    for _ in range(scroll_times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            # เลื่อนแล้วไม่ขยับ แสดงว่าไม่มีโหลดเพิ่ม
            break
        last_h = new_h


############################################################################
# MAIN SCRIPT
############################################################################

def main():
    # --- CONFIG ---
    TAG_URL = "https://pantip.com/tag/%E0%B8%AB%E0%B8%B8%E0%B9%89%E0%B8%99"
    MAX_SCROLLS = 10      # scroll หน้า tag สูงสุด
    SCROLL_WAIT = 2.5
    MAX_DATA = 8000       # เก็บ (post + comment) ให้ได้สัก 6000

    POST_SCROLL_TIMES = 10
    POST_SCROLL_WAIT = 1.5

    OUTPUT_CSV = "pantip_data_8000.csv"

    # ตั้งค่า Selenium
    chrome_options = Options()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--log-level=3')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # เข้าแท็ก "หุ้น"
        driver.get(TAG_URL)
        time.sleep(3)

        print(f"เริ่มเลื่อนหน้า (scroll) สูงสุด {MAX_SCROLLS} ครั้งเพื่อหาโพสต์...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        all_post_links = []

        # --- Scroll หน้า Tag ---
        while scroll_count < MAX_SCROLLS:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_WAIT)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1

            # parse
            soup = BeautifulSoup(driver.page_source, "html.parser")
            container = soup.select_one("div.container div.col-lg-8")
            if container:
                posts = container.select("li.pt-list-item")
                for p in posts:
                    link_tag = p.select_one("div.pt-list-item__title a")
                    if link_tag:
                        href = link_tag.get("href")
                        full_url = href if href.startswith("http") else "https://pantip.com" + href
                        if full_url not in all_post_links:
                            all_post_links.append(full_url)

        print(f"เจอลิงก์กระทู้ทั้งหมด: {len(all_post_links)}")

        if not all_post_links:
            print("ไม่มีลิงก์กระทู้ใด ๆ เลย")
            return

        # เปิดไฟล์ CSV
        # ใช้ quoting=csv.QUOTE_ALL เพื่อลดโอกาส CSV column เพี้ยน
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            # เขียน header
            writer.writerow(["post_id","type","day","datetime","title","content","author","raw_date"])
            f.flush()

            from tqdm import tqdm
            pbar = tqdm(total=MAX_DATA, desc="Scraping", unit="records")

            total_rows = 0
            try:
                # ไล่เปิดแต่ละโพสต์
                for link in all_post_links:
                    if total_rows >= MAX_DATA:
                        break

                    # เปิดโพสต์
                    driver.get(link)
                    time.sleep(2)

                    # scroll เพื่อโหลดคอมเมนต์
                    scroll_in_post(driver, scroll_times=POST_SCROLL_TIMES, wait_sec=POST_SCROLL_WAIT)

                    soup_post = BeautifulSoup(driver.page_source, "html.parser")

                    # --- โพสต์หลัก ---
                    title_tag = soup_post.select_one("title")
                    title = title_tag.get_text(strip=True) if title_tag else "N/A"

                    # ดึงวัน-เวลา และคนโพสต์
                    post_dt_div = soup_post.select_one("div.display-post-status-leftside")
                    dt_str_raw = post_dt_div.get_text(strip=True) if post_dt_div else ""
                    dt_obj = parse_thai_datetime(dt_str_raw)
                    day_str = dt_obj.strftime("%Y-%m-%d") if dt_obj else "N/A"
                    final_dt_str = format_datetime(dt_obj)

                    author_tag = soup_post.select_one(".display-post-name")
                    author = author_tag.get_text(strip=True) if author_tag else "Unknown"

                    # เขียนลง CSV
                    writer.writerow([
                        link,        # post_id
                        "post",      # type
                        day_str,     # day (YYYY-MM-DD)
                        final_dt_str,# datetime
                        title,       # title
                        "โพสต์หลัก", # content
                        author,      # author
                        dt_str_raw   # raw_date เก็บต้นฉบับไว้
                    ])
                    f.flush()  # flush ทันที
                    total_rows += 1
                    pbar.update(1)

                    if total_rows >= MAX_DATA:
                        break

                    # --- คอมเมนต์ ---
                    comment_blocks = soup_post.select("div[id^='comment-']")
                    for c in comment_blocks:
                        if total_rows >= MAX_DATA:
                            break

                        # เวลา
                        time_div = c.select_one("div.display-post-status-leftside")
                        comment_raw_date = time_div.get_text(strip=True) if time_div else ""
                        c_dt_obj = parse_thai_datetime(comment_raw_date)
                        c_day_str = c_dt_obj.strftime("%Y-%m-%d") if c_dt_obj else "N/A"
                        c_final_dt_str = format_datetime(c_dt_obj)

                        # เนื้อหา
                        content_div = c.select_one("div.display-post-message")
                        comment_text = content_div.get_text(" ", strip=True) if content_div else "N/A"

                        # คนโพสต์
                        c_author_tag = c.select_one(".display-post-name")
                        c_author = c_author_tag.get_text(strip=True) if c_author_tag else "Unknown"

                        writer.writerow([
                            link,           # post_id
                            "comment",      # type
                            c_day_str,      # day
                            c_final_dt_str, # datetime
                            title,          # title (ใส่ชื่อกระทู้เหมือนโพสต์หลัก)
                            comment_text,   # content
                            c_author,       # author
                            comment_raw_date # raw_date
                        ])
                        f.flush()
                        total_rows += 1
                        pbar.update(1)

                        if total_rows >= MAX_DATA:
                            break

            except KeyboardInterrupt:
                print("\n🛑 หยุดการทำงาน (KeyboardInterrupt)! บันทึกข้อมูลที่มีแล้ว")
            finally:
                pbar.close()

            print(f"\n🎉 ได้ข้อมูลรวม {total_rows} แถว เขียนลงไฟล์ '{OUTPUT_CSV}' เรียบร้อย")

    finally:
        driver.quit()
        print("ปิดเบราว์เซอร์เรียบร้อย")


if __name__ == "__main__":
    main()