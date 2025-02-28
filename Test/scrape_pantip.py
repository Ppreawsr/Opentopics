import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# จำนวนโพสต์สูงสุดที่ต้องการ scrape จากหน้าแท็ก "หุ้น"
MAX_POSTS = 5

# ตั้งค่า Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# เปิดหน้าเว็บหลักที่มี tag "หุ้น"
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

# ดึงโพสต์จาก container
posts = container.select("li.pt-list-item")[:MAX_POSTS]
print(f"🔎 พบโพสต์ทั้งหมด {len(posts)} โพสต์ในหน้าแรกของ tag 'หุ้น'")

# เตรียมไฟล์ CSV
with open("pantip_data_hun.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["ลำดับ", "ชื่อกระทู้", "วันที่", "เวลา", "เนื้อหากระทู้", "คอมเมนต์ทั้งหมด"])

    for idx, post in enumerate(posts, start=1):
        # ดึงหัวข้อและลิงก์ของแต่ละโพสต์
        title_tag = post.select_one("div.pt-list-item__title a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href")

        print(f"\n✨ กำลังดึงข้อมูลโพสต์ที่ {idx}/{len(posts)}: {title}")

        # เข้าไปยังลิงก์แต่ละกระทู้
        driver.get(link)
        time.sleep(5)  # รอให้กระทู้โหลดข้อมูล

        post_html = driver.page_source
        soup_post = BeautifulSoup(post_html, "html.parser")

        # ✅ ดึงเนื้อหาของโพสต์หลัก
        post_content_tag = soup_post.select_one("div.display-post-story")
        post_content = post_content_tag.get_text(separator=" ", strip=True) if post_content_tag else "ไม่พบเนื้อหากระทู้"

        # ✅ ดึงความคิดเห็น (คอมเมนต์)
        comments_section = soup_post.select("div.display-post-wrapper.section-comment")
        all_comments = "\n".join(comment.get_text(separator=" ", strip=True) for comment in comments_section)

        # ✅ ดึงวันที่และเวลา
        date_time_tag = soup_post.select_one("div.display-post-status-leftside")
        if date_time_tag:
            date_time_text = date_time_tag.get_text(strip=True)
            # ตัวอย่างรูปแบบที่เจอ เช่น "ความคิดเห็นที่ 10 19 ชั่วโมงที่แล้ว" 
            # อาจต้องปรับปรุง logic ตามโครงสร้างจริง
            date_time_parts = date_time_text.split()
            if len(date_time_parts) >= 2:
                post_date = " ".join(date_time_parts[:-2])
                post_time = date_time_parts[-2]
            else:
                post_date = date_time_text
                post_time = "ไม่พบเวลา"
        else:
            post_date = "ไม่พบวันที่"
            post_time = "ไม่พบเวลา"

        # บันทึกลง CSV
        writer.writerow([idx, title, post_date, post_time, post_content, all_comments])

        # พิมพ์ผลแบบเต็ม (ไม่จำกัดความยาว)
        # ถ้าอยากตัดบางส่วน ก็สามารถใส่ post_content[:100] เป็นต้น
        print(f"📝 ชื่อกระทู้: {title}")
        print(f"📅 วันที่: {post_date}")
        print(f"⏰ เวลา: {post_time}")
        print("📰 เนื้อหากระทู้:")
        print(post_content)
        print("💬 คอมเมนต์ทั้งหมด:")
        print(all_comments)
        print("--------------------------------------------------------------------------------")

# ปิดเบราว์เซอร์เมื่อเสร็จงาน
driver.quit()
print("\n🎉 เสร็จสิ้นการ scrape ข้อมูลจากหน้า tag 'หุ้น' แล้ว!")
