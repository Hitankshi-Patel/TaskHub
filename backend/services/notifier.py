import resend
from config import Config

resend.api_key = Config.RESEND_API_KEY or ""


def send_email(to_email: str, subject: str, html_content: str) -> dict:
    if not Config.RESEND_API_KEY:
        print(f"[EMAIL] No RESEND_API_KEY — skipping '{subject}' to {to_email}")
        return {"status": "skipped"}

    try:
        response = resend.Emails.send({
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
        print(f"[EMAIL] Sent '{subject}' to {to_email} — id: {response.get('id')}")
        return response
    except Exception as e:
        print(f"[EMAIL] Failed '{subject}' to {to_email}: {e}")
        return {"status": "error", "error": str(e)}


def notify_task_assigned(user_email, user_name, task_title, task_id, task_description, product_image_url):
    subject = f"New Task Assigned: {task_title}"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #1A202C, #2D3748); color: #fff; padding: 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .content {{ padding: 30px; line-height: 1.6; }}
    .task-card {{ background: #F7FAFC; border-left: 4px solid #4A5568; padding: 20px; border-radius: 4px; margin: 20px 0; }}
    .task-title {{ font-size: 17px; font-weight: 700; color: #2D3748; margin: 0 0 8px; }}
    .task-desc {{ font-size: 14px; color: #4A5568; margin: 0; }}
    .btn-wrap {{ text-align: center; margin: 28px 0 10px; }}
    .btn {{ display: inline-block; background: #1A202C; color: #fff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; }}
    .footer {{ background: #F7FAFC; padding: 18px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>TaskHub Studio</h1></div>
    <div class="content">
      <p style="font-size:17px;font-weight:600;margin-bottom:12px;">Hi {user_name},</p>
      <p>A new product photography task has been assigned to you. Generate 8 AI image variations for the product below.</p>
      <div class="task-card">
        <div class="task-title">{task_title}</div>
        <div class="task-desc">{task_description or 'No description provided.'}</div>
      </div>
      <div class="btn-wrap"><a href="http://localhost:3000/tasks/{task_id}" class="btn">Open Task</a></div>
    </div>
    <div class="footer"><p>Automated notification from TaskHub. Do not reply to this email.</p></div>
  </div>
</body>
</html>"""
    return send_email(user_email, subject, html)


def notify_task_submitted(admin_email, admin_name, task_title, task_id, user_name):
    subject = f"Task Submitted for Review: {task_title}"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #1A202C, #2D3748); color: #fff; padding: 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .content {{ padding: 30px; line-height: 1.6; }}
    .info-card {{ background: #F7FAFC; border-left: 4px solid #319795; padding: 20px; border-radius: 4px; margin: 20px 0; font-size: 14px; line-height: 1.8; }}
    .btn-wrap {{ text-align: center; margin: 28px 0 10px; }}
    .btn {{ display: inline-block; background: #319795; color: #fff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; }}
    .footer {{ background: #F7FAFC; padding: 18px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>Submission Ready for Review</h1></div>
    <div class="content">
      <p style="font-size:17px;font-weight:600;margin-bottom:12px;">Hi {admin_name},</p>
      <p><strong>{user_name}</strong> has completed all 8 image variations. The task is pending your review.</p>
      <div class="info-card">
        <strong>Task:</strong> {task_title}<br>
        <strong>Submitted by:</strong> {user_name}
      </div>
      <div class="btn-wrap"><a href="http://localhost:3000/admin" class="btn">Review Submission</a></div>
    </div>
    <div class="footer"><p>Automated notification from TaskHub. Do not reply to this email.</p></div>
  </div>
</body>
</html>"""
    return send_email(admin_email, subject, html)


def notify_task_accepted(user_email, user_name, task_title, feedback):
    subject = f"Task Accepted: {task_title}"
    feedback_block = f"""
      <div style="background:#F7FAFC;border:1px solid #E2E8F0;padding:18px;border-radius:6px;margin:18px 0;font-size:14px;color:#4A5568;font-style:italic;">
        "{feedback}"
      </div>""" if feedback else ""
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #2F855A, #48BB78); color: #fff; padding: 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .content {{ padding: 30px; line-height: 1.6; }}
    .badge {{ display: inline-block; background: #C6F6D5; color: #22543D; font-size: 13px; font-weight: 700; padding: 5px 14px; border-radius: 9999px; margin-bottom: 18px; }}
    .footer {{ background: #F7FAFC; padding: 18px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>Task Approved</h1></div>
    <div class="content">
      <p style="font-size:17px;font-weight:600;margin-bottom:12px;">Hi {user_name},</p>
      <div class="badge">ACCEPTED</div>
      <p>Your product photography for <strong>"{task_title}"</strong> has been accepted. The generated assets are now marked as final.</p>
      {feedback_block}
    </div>
    <div class="footer"><p>Automated notification from TaskHub. Do not reply to this email.</p></div>
  </div>
</body>
</html>"""
    return send_email(user_email, subject, html)


def notify_revision_requested(user_email, user_name, task_title, task_id, feedback):
    subject = f"Revision Requested: {task_title}"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #DD6B20, #ED8936); color: #fff; padding: 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .content {{ padding: 30px; line-height: 1.6; }}
    .badge {{ display: inline-block; background: #FEEBC8; color: #744210; font-size: 13px; font-weight: 700; padding: 5px 14px; border-radius: 9999px; margin-bottom: 18px; }}
    .feedback-card {{ background: #FFFAF0; border-left: 4px solid #DD6B20; padding: 18px; border-radius: 4px; margin: 18px 0; font-size: 14px; color: #744210; font-style: italic; }}
    .btn-wrap {{ text-align: center; margin: 28px 0 10px; }}
    .btn {{ display: inline-block; background: #DD6B20; color: #fff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; }}
    .footer {{ background: #F7FAFC; padding: 18px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>Revision Requested</h1></div>
    <div class="content">
      <p style="font-size:17px;font-weight:600;margin-bottom:12px;">Hi {user_name},</p>
      <div class="badge">REVISION REQUESTED</div>
      <p>The admin has reviewed your images for <strong>"{task_title}"</strong> and requested changes.</p>
      <div class="feedback-card">"{feedback or 'Please review the product alignment and prompt variations.'}"</div>
      <div class="btn-wrap"><a href="http://localhost:3000/tasks/{task_id}" class="btn">Update Generations</a></div>
    </div>
    <div class="footer"><p>Automated notification from TaskHub. Do not reply to this email.</p></div>
  </div>
</body>
</html>"""
    return send_email(user_email, subject, html)
