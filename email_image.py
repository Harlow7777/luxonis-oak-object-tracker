import smtplib
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# Configuration
WATCH_DIR = Path(__file__).parent.resolve()
SENDER_EMAIL = "hsfan123@gmail.com"
RECEIVER_EMAIL = "harlow_jacob@outlook.com"
EMAIL_PASSWORD = "skoc rmbi teho gfah"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Use 587 if using TLS
BATCH_SIZE = 5

def send_email(image_paths):
    timestamp = image_paths[0].stem.split("_")[-1]

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"Birds detected - batch of {len(image_paths)} images at {timestamp}"

    msg.attach(MIMEText(f"{len(image_paths)} birds detected. Images attached.", "plain"))

    for image_path in image_paths:
        with image_path.open("rb") as f:
            img = MIMEImage(f.read(), _subtype="png")
            img.add_header("Content-Disposition", "attachment", filename=image_path.name)
            msg.attach(img)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] Sent batch of {len(image_paths)} images.")
        for img_path in image_paths:
            img_path.unlink()  # Delete images after successful send
    except Exception as e:
        print(f"[ERROR] Failed to send batch: {e}")

def main():
    print("[WATCHER] Monitoring for new images in:", WATCH_DIR.resolve())
    sent_files = set()
    
    while True:
        image_paths = sorted([
            img for img in WATCH_DIR.glob("bird_detected_*.png")
            if img not in sent_files
        ])

        if len(image_paths) >= BATCH_SIZE:
            batch = image_paths[:BATCH_SIZE]
            send_email(batch)
            sent_files.update(batch)

        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    WATCH_DIR.mkdir(exist_ok=True)
    main()
