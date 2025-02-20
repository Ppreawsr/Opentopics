import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# กำหนดข้อมูลล็อกอินและ URL ของ Facebook Group
FACEBOOK_EMAIL = 'siriprapha.pp@gmail.com'     # ใส่อีเมลหรือชื่อผู้ใช้ Facebook ของคุณ
FACEBOOK_PASSWORD = 'poopreaw2547'             # ใส่รหัสผ่านของคุณ
FACEBOOK_GROUP_URL = 'https://www.facebook.com/groups/Tiphoon'  # ใส่ URL ของกลุ่ม Facebook ที่ต้องการดึงข้อมูล

def main():
    # ตั้งค่า Selenium WebDriver โดยใช้ Service object และระบุ path ของ ChromeDriver
    service = Service(executable_path=r'C:\\Users\\ppreawsr\\Downloads\\chromedriver-win64\\chromedriver.exe')
    driver = webdriver.Chrome(service=service)
    
    # ใช้ WebDriverWait เพื่อรอการโหลด element (เพิ่ม timeout เป็น 30 วินาที)
    wait = WebDriverWait(driver, 45)
    
    # เปิดหน้า Facebook Login
    driver.get("https://www.facebook.com/login")
    
    # รอจนกว่าฟอร์มล็อกอินปรากฏ แล้วป้อนข้อมูลล็อกอิน
    email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
    password_input = driver.find_element(By.ID, "pass")
    
    email_input.send_keys(FACEBOOK_EMAIL)
    password_input.send_keys(FACEBOOK_PASSWORD)
    
    # ค้นหาและคลิกปุ่ม Login
    login_button = driver.find_element(By.NAME, "login")
    login_button.click()
    
    # รอจนกว่าการล็อกอินสำเร็จโดยดูจาก URL หรือ element บนหน้า feed
    try:
        wait.until(EC.url_contains("facebook.com"))
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed']")))
    except Exception as e:
        print("การล็อกอินล้มเหลวหรือใช้เวลานานเกินไป:", e)
        driver.quit()
        return

    # เพิ่มขั้นตอนรอให้ผู้ใช้ดำเนินการยืนยันตัวตน (แก้ Captcha, Mobile Verification) ด้วยตนเอง
    print("โปรดดำเนินการยืนยันตัวตน (กรอก Captcha และ Mobile Verification) ให้เสร็จเรียบร้อย")
    input("เมื่อเสร็จแล้ว กด Enter เพื่อดำเนินการต่อ...")
    
    # หลังจากยืนยันตัวตนแล้ว เข้าสู่หน้า Facebook Group
    driver.get(FACEBOOK_GROUP_URL)
    time.sleep(30)  # รอให้หน้า Group โหลดข้อมูลครบถ้วน
    
    # เลื่อนหน้าจอเพื่อโหลดโพสต์เพิ่มเติม
    SCROLL_PAUSE_TIME = 30  # เวลารอหลังเลื่อนแต่ละครั้ง (30 วินาที)
    NUM_SCROLLS = 10        # จำนวนครั้งของการเลื่อน (ปรับเพิ่มได้ตามต้องการ)
    for i in range(NUM_SCROLLS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"เลื่อนหน้าจอครั้งที่ {i+1}/{NUM_SCROLLS}")
        time.sleep(SCROLL_PAUSE_TIME)
    
    # พยายามดึงโพสต์ โดยใช้ XPath ที่เลือก element ที่มี role เป็น article
    posts = driver.find_elements(By.XPATH, "//div[@role='article']")
    print("จำนวนโพสต์ที่พบ:", len(posts))
    
    # ดึงข้อความโพสต์และเก็บไว้ใน list (กรองโพสต์ที่มีข้อความจริง)
    posts_text = []
    for post in posts:
        text = post.text.strip()
        if text:
            posts_text.append(text)
    print("จำนวนโพสต์ที่ดึงได้ (มีข้อความ):", len(posts_text))
    
    # บันทึกข้อมูลโพสต์ลงไฟล์ CSV เพื่อใช้งานต่อในการทำ ML
    csv_filename = "C:\\Users\\ppreawsr\\Downloads\\post_data\\facebook_group_posts.csv"
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["post_index", "post_text"])  # เขียน header
        for idx, post_text in enumerate(posts_text, start=1):
            writer.writerow([idx, post_text])
    
    print(f"ข้อมูลถูกบันทึกลงไฟล์ {csv_filename}")
    
    # รอไว้ท้ายสุด (ตัวอย่างรอ 10 นาที) เพื่อให้หน้าจออยู่ได้นานสำหรับการตรวจสอบผลลัพธ์
    time.sleep(600)
    driver.quit()

if __name__ == "__main__":
    main()
