#!/usr/bin/env python3
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""SMTP Email Sender module"""

from email.mime.multipart import MIMEMultipart
import email
import email.mime.text
import smtplib
from .config import EmailSettings


class EmailSender:
    """Class to send email report using SMTP"""
    def __init__(self):
        self._settings = EmailSettings()

    def _smtp_connect(self):
        """Method to create a connection with SMTP server"""
        if self._settings.smtp_port == 465:
            smtp = smtplib.SMTP_SSL(self._settings.smtp_host,
                                    self._settings.smtp_port)
        else:
            smtp = smtplib.SMTP(self._settings.smtp_host,
                                self._settings.smtp_port)
            smtp.starttls()
        smtp.login(self._settings.email_sender,
                   self._settings.email_password)
        return smtp

    def _create_email(self, email_subject, email_content, email_recipient):
        """Method to create an email message from email subject, contect,
        sender, and receiver"""
        email_msg = MIMEMultipart()
        email_text = email.mime.text.MIMEText(email_content, "plain", "utf-8")
        email_text.replace_header('Content-Transfer-Encoding', 'quopri')
        email_text.set_payload(email_content, 'utf-8')
        email_msg.attach(email_text)
        email_msg['To'] = email_recipient
        email_msg['From'] = self._settings.email_sender
        email_msg['Subject'] = email_subject
        return email_msg

    def _send_email(self, email_msg):
        """Method to send an email message using SMTP"""
        smtp = self._smtp_connect()
        if smtp:
            smtp.send_message(email_msg)
            smtp.quit()

    def create_and_send_email(self, email_subject, email_content,
                              email_recipient):
        """Method to create and send email"""
        email_msg = self._create_email(
            email_subject, email_content, email_recipient
        )
        self._send_email(email_msg)
