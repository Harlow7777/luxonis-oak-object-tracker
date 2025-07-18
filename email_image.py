import smtplib
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# Configuration
WATCH_DIR = Path(__file__).parent.resolve()
SENDER_EMAIL = "<SENDER>@gmail.com"
RECEIVER_EMAIL = "<RECEIVER>"
EMAIL_PASSWORD = "<app-password>"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Use 587 if using TLS

def send_email(image_path: Path):
    timestamp = image_path.stem.split("_")[-1]
    mime_type = "png"

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"Bird detected - {timestamp}"

    msg.attach(MIMEText("Bird detected. Image attached.", "plain"))

    with image_path.open("rb") as f:
        img = MIMEImage(f.read(), _subtype=mime_type)
        img.add_header("Content-Disposition", "attachment", filename=image_path.name)
        msg.attach(img)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] Sent: {image_path.name}")
        image_path.unlink()  # Delete image after successful send
    except Exception as e:
        print(f"[ERROR] Failed to send {image_path.name}: {e}")

def main():
    print("[WATCHER] Monitoring for new images in:", WATCH_DIR.resolve())
    while True:
        for img_path in WATCH_DIR.glob("bird_detected_*.png"):
            print("Sending email for " + str(img_path))
            send_email(img_path)
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    WATCH_DIR.mkdir(exist_ok=True)
    main()
