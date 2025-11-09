import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
import requests
import base64
from io import BytesIO
from PIL import Image

#Dropbox Services
APP_KEY = "8uhy0qj88o39ose"
APP_SECRET = "1nj30wdqcf9lj21"
#request_refresh_token: https://www.dropbox.com/oauth2/authorize?client_id=8uhy0qj88o39ose&token_access_type=offline&response_type=code
AUTH_CODE = "PwoAjjEqu6AAAAAAAAABD8r5sEizHQK0HHTqRkwIquI"
REFRESH_TOKEN = "BdH_qEyTY0YAAAAAAAAAAbWZSauHlz7gF2dcyQqXlrNuzjCbVYXwUl4NA3te-vlt"

FOLDER_PATH = "/chart"       # โฟลเดอร์ที่เก็บภาพ
HTML_FILENAME = "gallery.html"   # ไฟล์ HTML ที่จะสร้าง

dbx = dropbox.Dropbox(
    oauth2_refresh_token=REFRESH_TOKEN,
    app_key=APP_KEY,
    app_secret=APP_SECRET
)

def get_refresh_token():
    res = requests.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "code": AUTH_CODE,
            "grant_type": "authorization_code",
        },
        auth=(APP_KEY, APP_SECRET)
    )
    print(res.json())

def testAccessToken():
    dbx = dropbox.Dropbox(ACCESS_TOKEN)
    print(f'Test Access: {dbx.users_get_current_account()}')
    print("✅ Connected to:", dbx.users_get_current_account().name.display_name)

def testRefreshToken():
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=REFRESH_TOKEN,
        app_key=APP_KEY,
        app_secret=APP_SECRET
    )
    # ทดสอบ
    print("✅ Connected to:", dbx.users_get_current_account().name.display_name)

# 1️⃣ ดึงไฟล์ภาพและสร้าง direct link
def list_image_urls(folder_path):
    try:
        files = dbx.files_list_folder(folder_path).entries
    except Exception as e:
        print(f"Error listing folder: {e}")
        return []

    urls = []
    for f in files:
        if isinstance(f, dropbox.files.FileMetadata) and f.name.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                link = dbx.sharing_create_shared_link_with_settings(f.path_lower)
            except dropbox.exceptions.ApiError:
                # ถ้ามี link อยู่แล้ว
                link = dbx.sharing_list_shared_links(f.path_lower).links[0]
            direct_url = link.url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
            urls.append(direct_url)
    return urls

# 2️⃣ สร้าง HTML gallery
def generate_html(image_urls):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Gallery</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #1a1a1a;
                color: white;
                overflow-x: hidden;
            }}
            h1 {{
                text-align: center;
                color: #fff;
                margin: 30px 0;
                font-size: 2.5em;
                text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            }}
            .gallery {{
                display: flex;
                flex-direction: column;
                gap: 40px;
                padding: 30px;
                max-width: 1400px;
                margin: 0 auto;
                align-items: center;
            }}
            .gallery-item {{
                position: relative;
                overflow: hidden;
                border-radius: 12px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                transition: all 0.3s ease;
                background: #2a2a2a;
                width: 100%;
                max-width: 1200px;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 30px;
            }}
            .gallery-item:hover {{
                transform: translateY(-8px) scale(1.01);
                box-shadow: 0 15px 35px rgba(255,255,255,0.1);
                background: #333;
            }}
            .gallery img {{
                width: 1000px;
                height: 2000px;
                object-fit: cover;
                cursor: zoom-in;
                transition: transform 0.3s ease;
                border-radius: 8px;
            }}
            .gallery img:hover {{
            transform: scale(1.05);
            }}
            .gallery-item:hover .gallery-img {{
                transform: scale(1.05);
            }}
            .gallery-item:hover .gallery-img {{
                transform: scale(1.05);
            }}
            .image-overlay {{
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                background: linear-gradient(transparent, rgba(0,0,0,0.8));
                padding: 25px 20px 15px;
                opacity: 0;
                transition: opacity 0.3s ease;
            }}
            .gallery-item:hover .image-overlay {{
                opacity: 1;
            }}
            .image-info {{
                color: white;
                font-size: 16px;
                text-align: center;
                font-weight: bold;
            }}

            /* Modal Styles */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.98);
                backdrop-filter: blur(10px);
            }}
            .modal-content {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(1);
                max-width: 95%;
                max-height: 95%;
                transition: transform 0.3s ease;
            }}
            .modal-image {{
                width: 100%;
                height: 100%;
                object-fit: contain;
                border-radius: 12px;
                box-shadow: 0 20px 50px rgba(0,0,0,0.8);
            }}
            .close {{
                position: absolute;
                top: 25px;
                right: 35px;
                font-size: 45px;
                color: white;
                cursor: pointer;
                z-index: 1001;
                background: rgba(255,0,0,0.7);
                width: 60px;
                height: 60px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                border: 2px solid white;
            }}
            .close:hover {{
                background: rgba(255,0,0,0.9);
                transform: rotate(90deg);
            }}
            .controls {{
                position: absolute;
                bottom: 30px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 15px;
                z-index: 1001;
            }}
            .control-btn {{
                background: rgba(255,255,255,0.15);
                color: white;
                border: 2px solid rgba(255,255,255,0.3);
                padding: 12px 20px;
                border-radius: 8px;
                cursor: pointer;
                backdrop-filter: blur(15px);
                transition: all 0.3s ease;
                font-size: 16px;
                font-weight: bold;
            }}
            .control-btn:hover {{
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.6);
                transform: translateY(-2px);
            }}
            .zoom-info {{
                position: absolute;
                top: 30px;
                left: 30px;
                background: rgba(0,0,0,0.6);
                color: white;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }}
            .nav-btn {{
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(255,255,255,0.15);
                color: white;
                border: none;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                font-size: 24px;
                cursor: pointer;
                backdrop-filter: blur(15px);
                transition: all 0.3s ease;
                z-index: 1001;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .nav-btn:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-50%) scale(1.1);
            }}
            .prev-btn {{ left: 30px; }}
            .next-btn {{ right: 30px; }}

            /* Responsive */
            @media (max-width: 768px) {{
                .gallery {{
                    gap: 25px;
                    padding: 20px;
                }}
                .gallery-item {{
                    padding: 20px;
                    max-width: 95%;
                }}
                .gallery-img {{
                    max-height: 500px;
                }}
                .close {{
                    top: 15px;
                    right: 20px;
                    width: 50px;
                    height: 50px;
                    font-size: 35px;
                }}
                .controls {{
                    bottom: 20px;
                    flex-wrap: wrap;
                    justify-content: center;
                }}
                .control-btn {{
                    padding: 10px 15px;
                    font-size: 14px;
                }}
                .nav-btn {{
                    width: 50px;
                    height: 50px;
                    font-size: 20px;
                }}
                .prev-btn {{ left: 15px; }}
                .next-btn {{ right: 15px; }}
            }}

            @media (max-width: 480px) {{
                .gallery {{
                    gap: 20px;
                    padding: 15px;
                }}
                .gallery-item {{
                    padding: 15px;
                    max-width: 100%;
                }}
                .gallery-img {{
                    max-height: 400px;
                }}
                .image-overlay {{
                    padding: 20px 15px 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>📸 Trading Charts Gallery</h1>
        <div class="gallery">
    """

    for url in image_urls:
        html_content += f'<img src="{url}" alt="Chart Image" onclick="openModal(this.src)">\n'

    html_content += """
        </div>

        <div id="imageModal" class="modal">
            <span class="close" onclick="closeModal()">&times;</span>
            <div class="zoom-info" id="zoomInfo">100%</div>
            <div class="modal-content" id="modalContent">
                <img class="modal-image" id="modalImage" src="">
            </div>
            <div class="controls">
                <button class="control-btn" onclick="zoomOut()">Zoom Out (-)</button>
                <button class="control-btn" onclick="resetZoom()">Reset</button>
                <button class="control-btn" onclick="zoomIn()">Zoom In (+)</button>
            </div>
        </div>

        <script>
            let currentScale = 1;
            const minScale = 0.1;
            const maxScale = 5;
            const scaleStep = 0.2;
            let isDragging = false;
            let startX, startY, initialX, initialY;
            let currentX = 0, currentY = 0;

            const modal = document.getElementById('imageModal');
            const modalImage = document.getElementById('modalImage');
            const modalContent = document.getElementById('modalContent');
            const zoomInfo = document.getElementById('zoomInfo');

            function openModal(src) {
                modal.style.display = 'block';
                modalImage.src = src;
                resetZoomAndPosition();
            }

            function closeModal() {
                modal.style.display = 'none';
            }

            function resetZoomAndPosition() {
                currentScale = 1;
                currentX = 0;
                currentY = 0;
                updateTransform();
                updateZoomInfo();
            }

            function resetZoom() {
                currentScale = 1;
                currentX = 0;
                currentY = 0;
                updateTransform();
                updateZoomInfo();
            }

            function zoomIn() {
                if (currentScale < maxScale) {
                    currentScale += scaleStep;
                    updateTransform();
                    updateZoomInfo();
                }
            }

            function zoomOut() {
                if (currentScale > minScale) {
                    currentScale -= scaleStep;
                    updateTransform();
                    updateZoomInfo();
                }
            }

            function updateTransform() {
                modalContent.style.transform = `translate(${currentX}px, ${currentY}px) scale(${currentScale})`;
            }

            function updateZoomInfo() {
                zoomInfo.textContent = Math.round(currentScale * 100) + '%';
            }

            // Mouse events for zoom and drag
            modalContent.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -scaleStep : scaleStep;
                const newScale = Math.min(maxScale, Math.max(minScale, currentScale + delta));
                
                if (newScale !== currentScale) {
                    // Calculate mouse position relative to image
                    const rect = modalContent.getBoundingClientRect();
                    const mouseX = e.clientX - rect.left;
                    const mouseY = e.clientY - rect.top;
                    
                    // Calculate the position change to keep the mouse point fixed
                    const scaleChange = newScale / currentScale;
                    currentX = mouseX - (mouseX - currentX) * scaleChange;
                    currentY = mouseY - (mouseY - currentY) * scaleChange;
                    
                    currentScale = newScale;
                    updateTransform();
                    updateZoomInfo();
                }
            });

            // Mouse events for dragging
            modalContent.addEventListener('mousedown', (e) => {
                if (currentScale > 1) {
                    isDragging = true;
                    startX = e.clientX - currentX;
                    startY = e.clientY - currentY;
                    modalContent.style.cursor = 'grabbing';
                }
            });

            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                
                e.preventDefault();
                currentX = e.clientX - startX;
                currentY = e.clientY - startY;
                updateTransform();
            });

            document.addEventListener('mouseup', () => {
                isDragging = false;
                modalContent.style.cursor = 'grab';
            });

            // Touch events for mobile
            modalContent.addEventListener('touchstart', (e) => {
                if (e.touches.length === 1 && currentScale > 1) {
                    isDragging = true;
                    startX = e.touches[0].clientX - currentX;
                    startY = e.touches[0].clientY - currentY;
                }
            });

            document.addEventListener('touchmove', (e) => {
                if (!isDragging || e.touches.length !== 1) return;
                
                e.preventDefault();
                currentX = e.touches[0].clientX - startX;
                currentY = e.touches[0].clientY - startY;
                updateTransform();
            });

            document.addEventListener('touchend', () => {
                isDragging = false;
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                if (modal.style.display === 'block') {
                    switch(e.key) {
                        case 'Escape':
                            closeModal();
                            break;
                        case '+':
                        case '=':
                            zoomIn();
                            break;
                        case '-':
                            zoomOut();
                            break;
                        case '0':
                            resetZoom();
                            break;
                    }
                }
            });

            // Close modal when clicking outside image
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeModal();
                }
            });

            // Initialize cursor style
            modalContent.style.cursor = 'grab';
        </script>
    </body>
    </html>
    """
    return html_content

# 3️⃣ อัปโหลด HTML กลับ Dropbox
def upload_html(html_content, filename):
    try:
        dbx.files_upload(html_content.encode('utf-8'), f"/{filename}", mode=dropbox.files.WriteMode.overwrite)
        try:
            link = dbx.sharing_create_shared_link_with_settings(f"/{filename}")
        except dropbox.exceptions.ApiError:
            link = dbx.sharing_list_shared_links(f"/{filename}").links[0]
        direct_url = link.url.replace("?dl=0", "?raw=1")
        return direct_url
    except Exception as e:
        print("Error uploading HTML:", e)
        return None

def upload_base64_image(base64_string, dropbox_path):
    try:
        # ตัด prefix เช่น "data:image/png;base64," ถ้ามี
        if base64_string.startswith("data:image"):
            base64_string = base64_string.split(",")[1]
        image_data = base64.b64decode(base64_string)
        dbx.files_upload(image_data, dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        print(f"✅ Uploaded from base64: {dropbox_path}")
        return create_direct_link(dropbox_path)
    except Exception as e:
        print("❌ Error uploading base64 image:", e)

def upload_combined_base64_images(base64_list, dropbox_path, direction="vertical"):
    """
    รวมหลาย base64 image เข้าด้วยกันเป็นภาพเดียว แล้วอัปโหลดขึ้น Dropbox
    :param base64_list: ลิสต์ของ base64 string (เช่น [chart1, chart2, chart3])
    :param dropbox_path: พาธไฟล์บน Dropbox ที่จะอัปโหลด
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

        # ✅ อัปโหลดขึ้น Dropbox
        dbx.files_upload(buffer.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        print(f"✅ Uploaded combined image to: {dropbox_path}")

        # ✅ สร้างลิงก์ดาวน์โหลดตรง
        return create_direct_link(dropbox_path)

    except Exception as e:
        print("❌ Error combining/uploading images:", e)
        return None

def create_direct_link(dropbox_path):
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    except dropbox.exceptions.ApiError:
        link = dbx.sharing_list_shared_links(dropbox_path).links[0]

    # เปลี่ยน link ให้เป็น direct view (โหลดภาพตรง ๆ)
    direct_url = link.url.replace("?dl=0", "?raw=1")
    print("🌐 Direct link:", direct_url)
    return direct_url

def clear_dropbox_folder(folder_path):
    """ลบไฟล์ทั้งหมดในโฟลเดอร์ Dropbox"""
    try:
        result = dbx.files_list_folder(folder_path)
        for entry in result.entries:
            dbx.files_delete_v2(entry.path_lower)
            print(f"🗑️ Deleted: {entry.path_lower}")
        print(f"✅ Cleared all files in folder: {folder_path}")
    except dropbox.exceptions.ApiError as e:
        if isinstance(e.error, dropbox.files.ListFolderError) and e.error.is_path() and e.error.get_path().is_not_found():
            print(f"⚠️ Folder not found: {folder_path} (skip clearing)")
        else:
            print("❌ Error clearing folder:", e)

def build_gallery_page():
    # ====== Run Upload Html ======
    image_urls = list_image_urls(FOLDER_PATH)
    if not image_urls:
        print("No images found in folder:", FOLDER_PATH)
    else:
        print(image_urls)
        html_content = generate_html(image_urls)
        with open('gallery.html', 'w', encoding='utf-8') as file:
            file.write(html_content)
        direct_link = upload_html(html_content, HTML_FILENAME)
        if direct_link:
            print("✅ Gallery HTML uploaded successfully!")
            print("Direct URL:", direct_link)

if __name__ == "__main__":
    #testRefreshToken()
    #clear_dropbox_folder(FOLDER_PATH)
    build_gallery_page()
