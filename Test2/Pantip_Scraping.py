import csv, re, time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- ฟังก์ชันแปลงวัน/เวลา ----------------
def parse_thai_datetime(text):
    text = text.replace("\xa0", " ").strip()
    m = re.search(r"(\d+)\s*(นาที|ชม\.|ชั่วโมง|วัน|วินาที)", text)
    if m:
        amount = int(m[1])
        unit_map = {"นาที": "minutes", "ชม.": "hours", "ชั่วโมง": "hours",
                    "วัน": "days", "วินาที": "seconds"}
        return datetime.now() - timedelta(**{unit_map[m[2]]: amount})
    return None

# ---------------- ค่าคงที่ ----------------
TAG_URL = "https://pantip.com/tag/หุ้น"
LIMIT_ROWS = 10000
WAIT = 1.5

# ---------------- Selenium ----------------
opt = Options()
opt.add_experimental_option('excludeSwitches', ['enable-logging'])
opt.add_argument('--log-level=3')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)

# ---------------- เตรียมเก็บผลลัพธ์ ----------------
seen_texts = set()
saved_rows = 0
csvfile = open("pantip_data.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csvfile)
writer.writerow(["type", "data", "date"])

def save(type_, text, date_str):
    global saved_rows
    text = text.strip()
    if not text or text in seen_texts or saved_rows >= LIMIT_ROWS:
        return
    writer.writerow([type_, text, date_str])
    seen_texts.add(text)
    saved_rows += 1

# ---------------- MAIN ----------------
try:
    driver.get(TAG_URL)
    time.sleep(3)

    SCROLL_TIMES = 30
    SCROLL_DELAY = 2.5

    for i in range(SCROLL_TIMES):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(SCROLL_DELAY)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    
    block = soup.select_one("#pt-topic-left > div:nth-child(2)")
    if not block:
        raise Exception("❌ ไม่เจอ block หลักกระทู้")

    items = block.select("ul > li")
    
    print(f"📌 พบกระทู้ {len(items)} รายการใน block")

    for idx, li in enumerate(items, start=1):
        if saved_rows >= LIMIT_ROWS:
            break

        title_tag = li.select_one("div.pt-list-item__title")
        time_tag = li.select_one("div.pt-list-item__info > span")
        link_tag = li.select_one("a[href*='/topic']")
        if not (title_tag and time_tag and link_tag):
            continue

        title_text = title_tag.get_text(" ", strip=True)
        time_obj = parse_thai_datetime(time_tag.text)
        url = "https://pantip.com" + link_tag["href"] if not link_tag["href"].startswith("http") else link_tag["href"]
        topic_id_match = re.findall(r'/topic/(\d+)', url)
        topic_id = topic_id_match[0] if topic_id_match else None
        if not topic_id:
            continue

        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"#topic-{topic_id}"))
            )
        except:
            print(f"⚠️ timeout: ไม่เจอโพสต์ใน {url}")
            continue

        psoup = BeautifulSoup(driver.page_source, "html.parser")

        # --- แยก topic และ post ออกจากกัน ---

        # ➊ เก็บ topic (หัวข้อกระทู้)
        save("topic", title_text, time_obj.strftime("%Y-%m-%d %H:%M:%S") if time_obj else "N/A")

        # ➋ พยายามหา post (เนื้อหาโพสต์หลัก)
        post_sel = f"#topic-{topic_id} > div > div:nth-child(4) > div.display-post-story-wrapper > div"
        post_node = psoup.select_one(post_sel)
        post_txt = post_node.get_text(" ", strip=True) if post_node else ""

        # ➌ ถ้ามีเนื้อหา ก็เก็บแยกเป็น post
        if post_txt:
            save("post", post_txt, time_obj.strftime("%Y-%m-%d %H:%M:%S") if time_obj else "N/A")
        else:
            print(f"⚠️ ไม่เจอเนื้อหาโพสต์ใน: {url}")


        # --- คอมเมนต์ (ลองหลาย layout) ---
        comments = psoup.select("#comments-jsrender div[id^='comment-']")
        for c in comments:
            if saved_rows >= LIMIT_ROWS: break
            msg = c.select_one("div.display-post-story-wrapper.comment-wrapper") \
               or c.select_one("div[data-role='comment-body']") \
               or c.select_one("div.post-message")
            time_ = c.select_one("span[data-role='timestamp']") \
                 or c.select_one("div.display-post-avatar > div > span")
            c_text = msg.get_text(" ", strip=True) if msg else ""
            c_date = parse_thai_datetime(time_.text) if time_ else None
            save("comment", c_text, c_date.strftime("%Y-%m-%d %H:%M:%S") if c_date else "N/A")

        print(f"✅ [{idx}/{len(items)}] {title_text[:60]} — saved: {saved_rows}/10000")

finally:
    csvfile.close()
    driver.quit()
    print(f"\n🎉 เสร็จแล้ว! บันทึก {saved_rows} แถว → pantip_data.csv")
