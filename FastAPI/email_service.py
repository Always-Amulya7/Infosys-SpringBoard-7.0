# Email sending disabled for development/testing
# Previous SMTP code commented below

# from django.core.mail import send_mail
# from django.conf import settings
# def send_invite(
#    email,
#    token
# ):
#    invite_link = (
#        f"http://127.0.0.1:8000/"
#        f"accept-invite/{token}"
#    )
#    send_mail(
#        subject="FocusGuard Organization Invitation",
#
#        message=(
#            "You have been invited to join "
#            "a FocusGuard organization.\n\n"
#            f"Accept invitation using this token:\n"
#            f"{token}\n\n"
#            f"Invitation Link:\n"
#            f"{invite_link}"
#        ),
#        from_email=getattr(
#            settings,
#            "DEFAULT_FROM_EMAIL",
#            "noreply@focusguard.com"
#        ),
#        recipient_list=[
#            email
#        ],
#
#        fail_silently=False
#    )

# The above code is inactive at present as the connection is to be made till then token based invite manually

# Development mode invitation handler
# Prints token instead of sending email

def send_invite(email, token):
    print("\n========== FOCUSGUARD INVITATION ==========")
    print(f"Recipient Email : {email}")
    print(f"Invitation Token: {token}")
    print("============================================\n")
    return True

# SMTP Service for our web app, based on token verification