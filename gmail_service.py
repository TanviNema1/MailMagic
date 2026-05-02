import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_gmail_service():
    """
    WHY: Gmail API requires OAuth2 — you can't just use a password.
    This loads the saved token and auto-refreshes it when expired.
    """
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Auto-refresh if token is expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def build_html_email(name: str, body: str, cta: str, preview_text: str) -> str:
    """
    WHY HTML email: Plain text looks unprofessional.
    HTML lets us style the email with the MailMagic brand.
    """
    paragraphs = "".join(f"<p style='margin:0 0 16px;color:#374151;font-size:15px;line-height:1.7'>{p}</p>"
                         for p in body.split("\n\n") if p.strip())
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif">
      <!-- Preview text (hidden, shows in inbox) -->
      <span style="display:none;max-height:0;overflow:hidden">{preview_text}</span>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:40px 20px">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,0.08)">
            <!-- Header -->
            <tr><td style="background:linear-gradient(135deg,#0d0f18,#1a1f2e);
                           padding:28px 40px;text-align:center">
              <span style="font-size:24px;font-weight:800;color:#00f5c4">Mail</span>
              <span style="font-size:24px;font-weight:800;color:#7b61ff">Magic</span>
            </td></tr>
            <!-- Body -->
            <tr><td style="padding:36px 40px">
              {paragraphs}
              <!-- CTA Button -->
              <div style="text-align:center;margin-top:28px">
                <a href="#" style="background:linear-gradient(135deg,#00f5c4,#7b61ff);
                                   color:#0d0f18;font-weight:800;padding:14px 32px;
                                   border-radius:8px;text-decoration:none;
                                   font-size:15px;display:inline-block">
                  {cta} →
                </a>
              </div>
            </td></tr>
            <!-- Footer -->
            <tr><td style="background:#f9fafb;padding:20px 40px;
                           text-align:center;font-size:12px;color:#9ca3af">
              You received this because you're a MailMagic member.
              <a href="#" style="color:#7b61ff">Unsubscribe</a>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def send_email(to: str, subject: str, body: str,
               cta: str = "View Now", preview_text: str = "",
               name: str = "") -> dict:
    """
    Sends a branded HTML email via Gmail API.
    Returns a status dict so the API can log success/failure.
    """
    try:
        service = get_gmail_service()

        msg = MIMEMultipart("alternative")
        msg["to"]      = to
        msg["subject"] = subject

        # Plain text fallback (important for email clients that block HTML)
        plain = MIMEText(body.replace("\n\n", "\n"), "plain")

        # HTML version
        html_content = build_html_email(name, body, cta, preview_text)
        html = MIMEText(html_content, "html")

        msg.attach(plain)
        msg.attach(html)   # HTML last = preferred by email clients

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return {"success": True, "message_id": result.get("id")}

    except Exception as e:
        return {"success": False, "error": str(e)}