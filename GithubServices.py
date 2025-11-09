import base64
from io import BytesIO
from PIL import Image
import requests
import os
from dotenv import load_dotenv
load_dotenv()

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
REPO_NAME = os.getenv("REPO_NAME")
ACCESS_TOKEN = os.getenv("GITHUB_PAT")  # ตั้งชื่อให้ชัดเจนว่าเป็น Personal Access Token
FILE_PATH = "gallery.html"  #สำหรับอัพโหลดไฟล์เดียว
COMMIT_MESSAGE = "Upload gallery.html to GitHub Pages"
DELETE_MESSAGE = f"Delete {FILE_PATH}"
BRANCH = "main"
UPLOAD_FOLDER = "chart"  #สำหรับอัพโหลดหลายๆไฟล์จากโฟลเดอร์เครื่องโลคอล
GITHUB_FOLDER = "chart"  #สำหรับโฟลเดอร์บน Github
ROOT_PATH = ""  #เว้นว่างหมายถึง root folder ของ repo

def combined_base64_images(base64_list, direction="vertical", output_path="combined_image.png"):
    """
    รวมหลาย base64 image เข้าด้วยกันเป็นภาพเดียว
    :param base64_list: ลิสต์ของ base64 string (เช่น [chart1, chart2, chart3])
    :param direction: 'vertical' (แนวตั้ง) หรือ 'horizontal' (แนวนอน)
    """
    try:
        # ✅ แปลง base64 แต่ละอันเป็น Image
        images = []
        for b64 in base64_list:
            if b64.startswith("data:image"):
                b64 = b64.split(",")[1]
            img = Image.open(BytesIO(base64.b64decode(b64)))
            images.append(img)

        # ✅ ตรวจสอบว่ามีภาพไหม
        if not images:
            print("❌ No images provided.")
            return None

        # ✅ คำนวณขนาดภาพรวม
        if direction == "vertical":
            total_width = max(img.width for img in images)
            total_height = sum(img.height for img in images)
            new_image = Image.new("RGB", (total_width, total_height), color=(255, 255, 255))

            y_offset = 0
            for img in images:
                new_image.paste(img, (0, y_offset))
                y_offset += img.height

        else:  # horizontal
            total_width = sum(img.width for img in images)
            total_height = max(img.height for img in images)
            new_image = Image.new("RGB", (total_width, total_height), color=(255, 255, 255))

            x_offset = 0
            for img in images:
                new_image.paste(img, (x_offset, 0))
                x_offset += img.width

        # ✅ แปลงเป็น bytes เพื่ออัปโหลด
        buffer = BytesIO()
        new_image.save(buffer, format="PNG")
        buffer.seek(0)
        new_image.save(output_path, format="PNG")
        print(f"✅ Combined image saved as: {output_path}")

    except Exception as e:
        print("❌ Error combining images:", e)
        return None

def upload_file_to_github(local_path, remote_folder=None):
    """อัปโหลดไฟล์เดียวไปยัง GitHub"""
    filename = os.path.basename(local_path)

    # ✅ ใช้เฉพาะชื่อไฟล์หรือ relative path เท่านั้น
    if remote_folder:
        remote_path = f"{remote_folder}/{filename}"
    else:
        remote_path = filename

    remote_path = remote_path.replace("\\", "/")
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{remote_path}"

    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # ตรวจสอบว่าไฟล์มีอยู่แล้วหรือไม่
    response = requests.get(
        url,
        headers={
            "Authorization": f"token {ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    sha = None
    if response.status_code == 200:
        sha = response.json().get("sha")
        print(f"ℹ️ พบไฟล์เดิม: {remote_path} (จะอัปเดต)")

    data = {
        "message": COMMIT_MESSAGE,
        "content": content,
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    upload_response = requests.put(
        url,
        headers={
            "Authorization": f"token {ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        },
        json=data
    )

    if upload_response.status_code in [200, 201]:
        print(f"✅ อัปโหลดสำเร็จ: {remote_path}")
    else:
        print(f"❌ ไม่สำเร็จ: {remote_path}")
        print(upload_response.status_code, upload_response.text)

def upload_multiple_files_to_github(folder_path):
    """อัปโหลดไฟล์ทั้งหมดในโฟลเดอร์และ subfolder"""
    for root, _, files in os.walk(folder_path):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, folder_path)
            upload_file_to_github(local_path, GITHUB_FOLDER)

def delete_a_file(file_path):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{file_path}"

    # ดึง SHA ของไฟล์ที่ต้องการลบ
    response = requests.get(
        url,
        headers={
            "Authorization": f"token {ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    if response.status_code != 200:
        print("❌ ไม่พบไฟล์หรือเข้าถึงไม่ได้:", response.status_code, response.text)
        exit()

    sha = response.json().get("sha")

    # เตรียม payload สำหรับการลบ
    data = {
        "message": DELETE_MESSAGE,
        "branch": BRANCH,
        "sha": sha
    }

    # ลบไฟล์
    delete_response = requests.delete(
        url,
        headers={
            "Authorization": f"token {ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        },
        json=data
    )

    if delete_response.status_code == 200:
        print(f"✅ ลบไฟล์สำเร็จ: {file_path}")
    else:
        print("❌ ลบไม่สำเร็จ:", delete_response.status_code, delete_response.text)

def delete_all_files_in_github(folder_path):
    headers = {
        "Authorization": f"token {ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # ดึงไฟล์ทั้งหมดในโฟลเดอร์
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{folder_path}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error listing folder: {response.status_code} - {response.text}")
        return

    items = response.json()
    if not items:
        print(f"⚠️ Folder '{folder_path}' is empty.")
        return

    # วนลบไฟล์ในโฟลเดอร์
    for item in items:
        if item["type"] == "file":
            delete_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{item['path']}"
            delete_payload = {
                "message": f"Delete {item['path']}",
                "sha": item["sha"]
            }
            del_res = requests.delete(delete_url, headers=headers, json=delete_payload)
            if del_res.status_code == 200:
                print(f"✅ Deleted: {item['path']}")
            else:
                print(f"❌ Error deleting {item['path']}: {del_res.status_code} - {del_res.text}")

        elif item["type"] == "dir":
            # 🔁 ลบไฟล์ภายในโฟลเดอร์ย่อยซ้ำ (recursive)
            delete_all_files_in_github(item["path"])

def create_folder():
    try:
        path = f"{GITHUB_FOLDER}/readme.txt"
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{path}"
        headers = {"Authorization": f"token {ACCESS_TOKEN}"}
        content = base64.b64encode(b"placeholder").decode("utf-8")
        data = {
            "message": f"Create folder {path}",
            "content": content,
            "branch": BRANCH
        }
        res = requests.put(url, headers=headers, json=data)
        print("🎉 สร้างโฟลเดอร์สำเร็จ!")
    except Exception as e:
        print("❌ Error create folder:", e)


def list_files(path=""):
    headers = {
        "Authorization": f"token {ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # === ดึงลิสต์ไฟล์ ===
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{path}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return []
    items = response.json()
    all_files = []

    for item in items:
        if item["type"] == "file":
            all_files.append({
                "name": item["name"],
                "path": item["path"],
                "html_url": item["html_url"]
            })
        elif item["type"] == "dir":
            # ✅ เรียกซ้ำโดยใช้ path ของโฟลเดอร์ย่อยจาก root ได้เลย
            print(f"🔍 Subdir found: {item['path']}")
            all_files.extend(list_files(item["path"]))  # ไม่ต้องต่อ path เดิม

    return all_files

def list_files2(path=""):
    headers = {
        "Authorization": f"token {ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # === ดึงลิสต์ไฟล์ ===
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{path}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return []
    items = response.json()
    all_files = []

    for item in items:
        all_files.append({
            "name": item["name"],
            "path": item["path"],
            "html_url": item["html_url"]
        })

    return all_files

if __name__ == "__main__":
    #print("🚀 เริ่มอัปโหลดหนึ่งไฟล์ไปยัง GitHub...")
    #upload_file_to_github(FILE_PATH, None)
    #print("🎉 อัปโหลดหนึ่งไฟล์เสร็จสิ้น!")

    #print("🚀 เริ่มอัปโหลดไฟล์ทั้งหมดไปยัง GitHub...")
    upload_multiple_files_to_github(UPLOAD_FOLDER)
    #print("🎉 อัปโหลดไฟล์ทั้งหมดเสร็จสิ้น!")

    #print("🚀 เริ่มลบหนึ่งไฟล์...")
    #delete_a_file("SKY_chart.png")
    #print("🎉 ลบหนึ่งไฟล์เสร็จสิ้น!")

    #print("🚀 เริ่มลบไฟล์ทั้งหมด...")
    #delete_all_files_in_github("chart")
    #print("🚀 ลบไฟล์ทั้งหมดเสร็จสิ้น...")

    #create_folder()
    files = list_files()
    for idx, f in enumerate(files, start=1):
        print(f"{idx}. {f['path']}")


