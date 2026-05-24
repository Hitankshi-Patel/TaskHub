import os
import resend
from config import Config

# Initialize Resend
if Config.RESEND_API_KEY:
    resend.api_key = Config.RESEND_API_KEY

def send_email(to_email, subject, html_content):
    """
    Sends an email using Resend, or falls back to logging if the Resend API key is missing.
    """
    if not Config.RESEND_API_KEY:
        print("\n" + "="*80)
        print(f"MOCK EMAIL SENT:")
        print(f"TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print("-" * 80)
        print(html_content)
        print("="*80 + "\n")
        
        # Log mock email to a file for development debugging
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "mock_emails.log"), "a", encoding="utf-8") as f:
                f.write(f"--- {subject} to {to_email} ---\n{html_content}\n\n")
        except Exception as e:
            print(f"Failed to write mock email to log file: {str(e)}")
            
        return {"id": "mock-email-id", "status": "logged"}

    try:
        params = {
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        response = resend.Emails.send(params)
        return response
    except Exception as e:
        print(f"Resend email error: {str(e)}")
        return {"error": str(e)}

def notify_task_assigned(user_email, user_name, task_title, task_id, task_description, product_image_url):
    subject = f"New Task Assigned: {task_title}"
    
    # Elegant, modern responsive HTML template
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Task Assigned</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #1A202C, #2D3748); color: #ffffff; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em; }}
            .content {{ padding: 30px; line-height: 1.6; }}
            .greeting {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #1A202C; }}
            .task-card {{ background-color: #F7FAFC; border-left: 4px solid #4A5568; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .task-title {{ font-size: 18px; font-weight: 700; color: #2D3748; margin-top: 0; }}
            .task-desc {{ font-size: 14px; color: #4A5568; margin-bottom: 0; }}
            .product-preview {{ text-align: center; margin: 20px 0; }}
            .product-image {{ max-width: 100%; max-height: 250px; border-radius: 6px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); border: 1px solid #EDF2F7; }}
            .button-container {{ text-align: center; margin: 30px 0 10px; }}
            .btn {{ display: inline-block; background-color: #1A202C; color: #ffffff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; transition: background-color 0.2s; }}
            .footer {{ background-color: #F7FAFC; padding: 20px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TaskHub Studio</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {user_name},</div>
                <p>A new product photography task has been assigned to you. You are required to generate 8 AI variations for this product while maintaining strict design consistency.</p>
                
                <div class="task-card">
                    <div class="task-title">{task_title}</div>
                    <div class="task-desc">{task_description or 'No description provided.'}</div>
                </div>

                <div class="product-preview">
                    <p style="font-size: 13px; font-weight: 600; color: #718096; text-transform: uppercase; margin-bottom: 8px;">Product Image Preview</p>
                    <img class="product-image" src="{product_image_url}" alt="Product Preview">
                </div>

                <div class="button-container">
                    <a href="http://localhost:3000/tasks/{task_id}" class="btn">Open AI Studio</a>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated notification from TaskHub. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(user_email, subject, html)

def notify_task_submitted(admin_email, admin_name, task_title, task_id, user_name):
    subject = f"Task Completed: {task_title} by {user_name}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Task Submitted</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #1A202C, #2D3748); color: #ffffff; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
            .content {{ padding: 30px; line-height: 1.6; }}
            .greeting {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #1A202C; }}
            .info-card {{ background-color: #F7FAFC; border-left: 4px solid #319795; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .button-container {{ text-align: center; margin: 30px 0 10px; }}
            .btn {{ display: inline-block; background-color: #319795; color: #ffffff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; }}
            .footer {{ background-color: #F7FAFC; padding: 20px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Task Submitted for Review</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {admin_name},</div>
                <p>The user <strong>{user_name}</strong> has completed the assigned product photography task and generated all 8 variations. The task is now pending your review and approval.</p>
                
                <div class="info-card">
                    <strong>Task Title:</strong> {task_title}<br>
                    <strong>Submitted By:</strong> {user_name}<br>
                    <strong>Status:</strong> Submitted (Pending Review)
                </div>

                <div class="button-container">
                    <a href="http://localhost:3000/admin" class="btn">Review Submissions</a>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated notification from TaskHub. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(admin_email, subject, html)

def notify_task_accepted(user_email, user_name, task_title, feedback):
    subject = f"Task Accepted: {task_title}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Task Accepted</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #2F855A, #48BB78); color: #ffffff; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
            .content {{ padding: 30px; line-height: 1.6; }}
            .greeting {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #2D3748; }}
            .status-badge {{ display: inline-block; background-color: #C6F6D5; color: #22543D; font-size: 14px; font-weight: 700; padding: 6px 16px; border-radius: 9999px; margin-bottom: 20px; }}
            .feedback-card {{ background-color: #F7FAFC; border: 1px solid #E2E8F0; padding: 20px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ background-color: #F7FAFC; padding: 20px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Task Approved</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {user_name},</div>
                <div class="status-badge">ACCEPTED</div>
                <p>Congratulations! Your submitted AI product photography for the task <strong>"{task_title}"</strong> has been accepted by the admin.</p>
                
                {f'''
                <div class="feedback-card">
                    <strong style="display:block; margin-bottom: 8px; color: #2F855A;">Admin Feedback:</strong>
                    <span style="font-size: 14px; color: #4A5568; font-style: italic;">"{feedback}"</span>
                </div>
                ''' if feedback else ''}
                
                <p>The generated assets are now marked as final and exported to the platform library. Thank you for your work!</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from TaskHub. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(user_email, subject, html)

def notify_revision_requested(user_email, user_name, task_title, task_id, feedback):
    subject = f"Revision Requested: {task_title}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Revision Requested</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f9f9fa; color: #2D3748; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #DD6B20, #ED8936); color: #ffffff; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
            .content {{ padding: 30px; line-height: 1.6; }}
            .greeting {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #2D3748; }}
            .status-badge {{ display: inline-block; background-color: #FEEBC8; color: #744210; font-size: 14px; font-weight: 700; padding: 6px 16px; border-radius: 9999px; margin-bottom: 20px; }}
            .feedback-card {{ background-color: #FFFAF0; border: 1px solid #FEEBC8; border-left: 4px solid #DD6B20; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .button-container {{ text-align: center; margin: 30px 0 10px; }}
            .btn {{ display: inline-block; background-color: #DD6B20; color: #ffffff !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 15px; }}
            .footer {{ background-color: #F7FAFC; padding: 20px; text-align: center; font-size: 12px; color: #718096; border-top: 1px solid #EDF2F7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Revision Requested</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {user_name},</div>
                <div class="status-badge">REVISION REQUESTED</div>
                <p>The administrator has reviewed your generated product images for <strong>"{task_title}"</strong> and requested revisions before approval.</p>
                
                <div class="feedback-card">
                    <strong style="display:block; margin-bottom: 8px; color: #DD6B20;">Required Adjustments:</strong>
                    <span style="font-size: 14px; color: #744210; font-style: italic;">"{feedback or 'Please check product alignment or prompt variations.'}"</span>
                </div>

                <p>Please click below to go back into the AI Studio, adjust your inputs or prompts, and regenerate the requested images.</p>

                <div class="button-container">
                    <a href="http://localhost:3000/tasks/{task_id}" class="btn">Update Generations</a>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated notification from TaskHub. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(user_email, subject, html)
