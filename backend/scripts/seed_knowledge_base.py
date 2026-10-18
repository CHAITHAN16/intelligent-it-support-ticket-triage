"""Insert or update the prototype curated knowledge-base articles safely."""

from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal
from models import KnowledgeBaseArticle


ARTICLES = [
    ("Office Wi-Fi connection troubleshooting", "Troubleshoot an office laptop that cannot join Wi-Fi or keeps disconnecting.", "Network", "1. Confirm Wi-Fi is enabled and airplane mode is off.\n2. Forget the office network, reconnect, and sign in using your organization credentials.\n3. Restart the laptop and check whether nearby colleagues are affected.\n4. If it still fails, contact the assigned IT team with your location, device name, and the time the issue began.", "wifi wireless office network disconnect reconnect"),
    ("VPN connection troubleshooting", "Resolve common VPN sign-in, connection, or tunnel failures for remote access.", "Network", "1. Confirm your internet connection works without the VPN.\n2. Reopen the approved VPN client and sign in again; check that the device clock is correct.\n3. Restart the client and device, then retry once.\n4. Do not share passwords or bypass security controls. If the connection still fails, contact the assigned IT team with the error text and time.", "vpn remote access tunnel connection client login"),
    ("Email synchronization troubleshooting", "Restore email that is delayed or not synchronizing across devices.", "Software", "1. Check network access and the email service status available to your organization.\n2. Refresh the inbox and confirm sync is enabled and the device has free storage.\n3. Restart the mail app; if safe, remove and re-add the account using the approved sign-in flow.\n4. Contact the assigned IT team if messages remain missing, including affected devices and when sync last worked.", "email mail inbox synchronization sync outlook messages"),
    ("Application or software crash troubleshooting", "Troubleshoot a desktop or business application that closes, freezes, or crashes.", "Software", "1. Record the app name, error text, and the action that triggers the crash.\n2. Save work where possible, close and reopen the app, then restart the device.\n3. Check for approved application updates and adequate disk space; avoid downloading repair tools from untrusted sites.\n4. Contact the assigned IT team if it repeats, with the error, time, and steps to reproduce.", "application software crash crashing freeze frozen error app"),
    ("Password and account access troubleshooting", "Restore access when a password is rejected or an account appears locked.", "Access", "1. Check the username and keyboard layout, then retry carefully once.\n2. Use only your organization's approved password reset or account recovery process.\n3. Never share a password or one-time code with anyone.\n4. Contact the assigned IT team if recovery fails or the account remains locked; identity verification may be required.", "password account access login locked sign-in reset credentials"),
    ("Suspicious login or security incident response", "Respond safely to an unexpected login alert, suspicious sign-in, or suspected account compromise.", "Security", "1. Do not approve an unexpected sign-in prompt or click links in suspicious messages.\n2. From a trusted device, use the organization's approved security reporting channel immediately.\n3. If instructed by your official policy, change the password through the trusted sign-in page and revoke unknown sessions.\n4. Preserve the alert details and time. Do not investigate or delete evidence; contact the security/IT team urgently.", "security suspicious login unauthorized account compromise phishing breach alert"),
    ("Printer troubleshooting", "Resolve common printer connection, queue, and output problems.", "Hardware", "1. Check printer power, paper, display alerts, and that your device is on the expected network.\n2. Confirm the correct printer is selected and clear only your own stuck print job.\n3. Restart the printer if permitted and retry with a small test page.\n4. Contact the assigned IT team with the printer name/location and any displayed error if it remains unavailable.", "printer printing print queue paper offline connection"),
    ("Laptop hardware troubleshooting", "Initial checks for laptop power, battery, keyboard, display, or other hardware problems.", "Hardware", "1. Check the charger and outlet, and disconnect nonessential peripherals.\n2. Restart once if safe; note any unusual sound, heat, damage, or error lights.\n3. Stop using the device and unplug it if it is unusually hot, swollen, wet, or physically damaged.\n4. Contact the assigned IT team for inspection. Do not open the case or attempt repairs yourself.", "laptop hardware battery power keyboard screen display charger overheating"),
]


def seed(db) -> int:
    changed = 0
    now = datetime.now(timezone.utc)
    for title, summary, category, steps, keywords in ARTICLES:
        article = db.scalar(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.title == title))
        if article is None:
            db.add(KnowledgeBaseArticle(title=title, summary=summary, category=category, resolution_steps=steps, keywords=keywords, active=True))
        else:
            article.summary = summary
            article.category = category
            article.resolution_steps = steps
            article.keywords = keywords
            article.active = True
            article.updated_at = now
        changed += 1
    db.commit()
    return changed


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Seeded or updated {seed(session)} prototype knowledge-base articles.")
