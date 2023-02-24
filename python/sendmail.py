import smtplib
import socket

from email.mime.text import MIMEText

msg = MIMEText("This is a simple email test!\n\nDid you receive it?")
msg['From'] = "B.U.V.I.S. <daemon@cold.buvis.net>"
msg['To'] = "tomas@buvis.net"
msg['Subject'] = "Test message from " + socket.gethostname()

server = smtplib.SMTP('10.7.0.1', 25)
server.sendmail(msg['From'], msg['To'], msg.as_string())
server.quit()
