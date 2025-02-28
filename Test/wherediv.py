import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ตั้งค่า Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# URL ของกระทู้ตัวอย่าง (เปลี่ยนเป็น URL จริงของกระทู้ที่ต้องการ)
test_url = "https://pantip.com/topic/43283523"  # 🔄 เปลี่ยนเป็นลิงก์จริงของกระทู้
driver.get(test_url)
time.sleep(5)  # รอให้หน้าโหลด

# ดึง HTML ของโพสต์ที่ render แล้ว
post_html = driver.page_source
soup_post = BeautifulSoup(post_html, "html.parser")

# ✅ ดึงเนื้อหาของโพสต์ (เฉพาะโพสต์หลัก)
post_content_tag = soup_post.select_one("div.display-post-story")
post_content = post_content_tag.get_text(separator=" ", strip=True) if post_content_tag else "ไม่พบเนื้อหากระทู้"

# ✅ ดึงคอมเมนต์ (ความคิดเห็นทั้งหมด)
comments_section = soup_post.select("div.display-post-wrapper.section-comment")
comments_text = "\n".join(comment.get_text(separator=" ", strip=True) for comment in comments_section)

# แสดงผลที่ scrape ได้
print("\n✅ เนื้อหากระทู้:\n", post_content)
print("\n✅ คอมเมนต์ทั้งหมด:\n", comments_text)

# ปิดเบราว์เซอร์
driver.quit()
