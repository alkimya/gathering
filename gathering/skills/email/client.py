"""
Email Skill for GatheRing.
Provides SMTP sending and IMAP reading capabilities.
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import re
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class EmailSkill(BaseSkill):
    """
    Skill for email operations.

    Features:
    - Send emails via SMTP (with attachments)
    - Read emails via IMAP
    - Search and filter emails
    - Manage folders
    - Parse email content

    Security:
    - Credentials from environment or config
    - TLS/SSL required by default
    - Rate limiting support
    """

    name = "email"
    description = "SMTP/IMAP email operations"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK]

    # Common SMTP/IMAP servers
    KNOWN_PROVIDERS = {
        "gmail": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
        },
        "outlook": {
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
        },
        "yahoo": {
            "smtp_host": "smtp.mail.yahoo.com",
            "smtp_port": 587,
            "imap_host": "imap.mail.yahoo.com",
            "imap_port": 993,
        },
        "protonmail": {
            "smtp_host": "smtp.protonmail.ch",
            "smtp_port": 587,
            "imap_host": "imap.protonmail.ch",
            "imap_port": 993,
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.smtp_connection = None
        self.imap_connection = None

        # Load config from environment or config dict
        self.smtp_host = self._get_config("smtp_host", os.getenv("SMTP_HOST"))
        self.smtp_port = int(self._get_config("smtp_port", os.getenv("SMTP_PORT", "587")))
        self.imap_host = self._get_config("imap_host", os.getenv("IMAP_HOST"))
        self.imap_port = int(self._get_config("imap_port", os.getenv("IMAP_PORT", "993")))
        self.email_user = self._get_config("email_user", os.getenv("EMAIL_USER"))
        self.email_password = self._get_config("email_password", os.getenv("EMAIL_PASSWORD"))
        self.default_from = self._get_config("default_from", os.getenv("EMAIL_FROM"))

        # Apply provider presets if specified
        provider = self._get_config("provider")
        if provider and provider in self.KNOWN_PROVIDERS:
            preset = self.KNOWN_PROVIDERS[provider]
            self.smtp_host = self.smtp_host or preset["smtp_host"]
            self.smtp_port = self.smtp_port or preset["smtp_port"]
            self.imap_host = self.imap_host or preset["imap_host"]
            self.imap_port = self.imap_port or preset["imap_port"]

    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get config value with fallback."""
        if self.config and key in self.config:
            return self.config[key]
        return default

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "email_send",
                "description": "Send an email via SMTP",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body (plain text or HTML)"
                        },
                        "html": {
                            "type": "boolean",
                            "description": "Whether body is HTML",
                            "default": False
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CC recipients"
                        },
                        "bcc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "BCC recipients"
                        },
                        "attachments": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File paths to attach"
                        },
                        "from_address": {
                            "type": "string",
                            "description": "From address (uses default if not specified)"
                        },
                        "reply_to": {
                            "type": "string",
                            "description": "Reply-To address"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            {
                "name": "email_read",
                "description": "Read emails from IMAP server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "description": "Folder to read from",
                            "default": "INBOX"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of emails to fetch",
                            "default": 10
                        },
                        "unread_only": {
                            "type": "boolean",
                            "description": "Only fetch unread emails",
                            "default": False
                        },
                        "since_days": {
                            "type": "integer",
                            "description": "Only fetch emails from last N days"
                        },
                        "include_body": {
                            "type": "boolean",
                            "description": "Include email body in results",
                            "default": True
                        }
                    }
                }
            },
            {
                "name": "email_search",
                "description": "Search emails with criteria",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "description": "Folder to search in",
                            "default": "INBOX"
                        },
                        "from_address": {
                            "type": "string",
                            "description": "Filter by sender"
                        },
                        "to_address": {
                            "type": "string",
                            "description": "Filter by recipient"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Filter by subject (partial match)"
                        },
                        "body_contains": {
                            "type": "string",
                            "description": "Filter by body content"
                        },
                        "since": {
                            "type": "string",
                            "description": "Since date (YYYY-MM-DD)"
                        },
                        "before": {
                            "type": "string",
                            "description": "Before date (YYYY-MM-DD)"
                        },
                        "flagged": {
                            "type": "boolean",
                            "description": "Filter flagged/starred emails"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 20
                        }
                    }
                }
            },
            {
                "name": "email_get",
                "description": "Get a specific email by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID/UID"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Folder containing the email",
                            "default": "INBOX"
                        },
                        "mark_read": {
                            "type": "boolean",
                            "description": "Mark as read after fetching",
                            "default": False
                        }
                    },
                    "required": ["email_id"]
                }
            },
            {
                "name": "email_folders",
                "description": "List email folders",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "email_move",
                "description": "Move email to another folder",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to move"
                        },
                        "source_folder": {
                            "type": "string",
                            "description": "Source folder",
                            "default": "INBOX"
                        },
                        "dest_folder": {
                            "type": "string",
                            "description": "Destination folder"
                        }
                    },
                    "required": ["email_id", "dest_folder"]
                }
            },
            {
                "name": "email_delete",
                "description": "Delete an email (move to trash)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to delete"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Folder containing the email",
                            "default": "INBOX"
                        },
                        "permanent": {
                            "type": "boolean",
                            "description": "Permanently delete (skip trash)",
                            "default": False
                        }
                    },
                    "required": ["email_id"]
                }
            },
            {
                "name": "email_mark",
                "description": "Mark email as read/unread/flagged",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Folder containing the email",
                            "default": "INBOX"
                        },
                        "read": {
                            "type": "boolean",
                            "description": "Mark as read (True) or unread (False)"
                        },
                        "flagged": {
                            "type": "boolean",
                            "description": "Mark as flagged/starred"
                        }
                    },
                    "required": ["email_id"]
                }
            },
            {
                "name": "email_reply",
                "description": "Reply to an email",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to reply to"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Folder containing the email",
                            "default": "INBOX"
                        },
                        "body": {
                            "type": "string",
                            "description": "Reply body"
                        },
                        "reply_all": {
                            "type": "boolean",
                            "description": "Reply to all recipients",
                            "default": False
                        },
                        "include_original": {
                            "type": "boolean",
                            "description": "Include original message",
                            "default": True
                        }
                    },
                    "required": ["email_id", "body"]
                }
            },
            {
                "name": "email_draft",
                "description": "Save email as draft",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recipients"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject"
                        },
                        "body": {
                            "type": "string",
                            "description": "Body"
                        },
                        "html": {
                            "type": "boolean",
                            "description": "HTML body",
                            "default": False
                        }
                    },
                    "required": ["subject", "body"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute email tool."""
        try:
            if tool_name == "email_send":
                return self._send_email(tool_input)
            elif tool_name == "email_read":
                return self._read_emails(tool_input)
            elif tool_name == "email_search":
                return self._search_emails(tool_input)
            elif tool_name == "email_get":
                return self._get_email(tool_input)
            elif tool_name == "email_folders":
                return self._list_folders()
            elif tool_name == "email_move":
                return self._move_email(tool_input)
            elif tool_name == "email_delete":
                return self._delete_email(tool_input)
            elif tool_name == "email_mark":
                return self._mark_email(tool_input)
            elif tool_name == "email_reply":
                return self._reply_email(tool_input)
            elif tool_name == "email_draft":
                return self._save_draft(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )
        except Exception as e:
            logger.exception(f"Email tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Email operation failed: {str(e)}",
                error=str(e)
            )

    def _get_smtp_connection(self) -> smtplib.SMTP:
        """Get or create SMTP connection."""
        if not self.smtp_host or not self.email_user or not self.email_password:
            raise ValueError(
                "SMTP not configured. Set SMTP_HOST, EMAIL_USER, EMAIL_PASSWORD "
                "environment variables or provide in config."
            )

        smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
        smtp.starttls()
        smtp.login(self.email_user, self.email_password)
        return smtp

    def _get_imap_connection(self) -> imaplib.IMAP4_SSL:
        """Get or create IMAP connection."""
        if not self.imap_host or not self.email_user or not self.email_password:
            raise ValueError(
                "IMAP not configured. Set IMAP_HOST, EMAIL_USER, EMAIL_PASSWORD "
                "environment variables or provide in config."
            )

        imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        imap.login(self.email_user, self.email_password)
        return imap

    def _parse_email(self, msg: email.message.Message, include_body: bool = True) -> Dict[str, Any]:
        """Parse email message into dict."""
        # Decode subject
        subject = ""
        if msg["Subject"]:
            decoded = decode_header(msg["Subject"])
            subject = "".join(
                part.decode(encoding or "utf-8") if isinstance(part, bytes) else part
                for part, encoding in decoded
            )

        # Parse addresses
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")
        cc_addr = msg.get("Cc", "")

        # Parse date
        date_str = msg.get("Date", "")

        result = {
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "cc": cc_addr,
            "date": date_str,
            "message_id": msg.get("Message-ID", ""),
            "in_reply_to": msg.get("In-Reply-To", ""),
        }

        if include_body:
            body = ""
            html_body = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "size": len(part.get_payload(decode=True) or b"")
                        })
                    elif content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                    elif content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            result["body"] = body
            result["html_body"] = html_body
            result["attachments"] = attachments

        return result

    def _send_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Send an email."""
        to = params["to"]
        subject = params["subject"]
        body = params["body"]
        is_html = params.get("html", False)
        cc = params.get("cc", [])
        bcc = params.get("bcc", [])
        attachments = params.get("attachments", [])
        from_address = params.get("from_address", self.default_from or self.email_user)
        reply_to = params.get("reply_to")

        # Create message
        if attachments:
            msg = MIMEMultipart()
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Add attachments
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(filepath)}"
                    )
                    msg.attach(part)
        else:
            if is_html:
                msg = MIMEText(body, "html")
            else:
                msg = MIMEText(body, "plain")

        msg["Subject"] = subject
        msg["From"] = from_address
        msg["To"] = ", ".join(to)

        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        # All recipients
        all_recipients = to + cc + bcc

        # Send
        smtp = self._get_smtp_connection()
        try:
            smtp.sendmail(from_address, all_recipients, msg.as_string())
        finally:
            smtp.quit()

        return SkillResponse(
            success=True,
            message=f"Email sent to {len(all_recipients)} recipient(s)",
            data={
                "to": to,
                "cc": cc,
                "subject": subject,
                "attachments_count": len(attachments)
            }
        )

    def _read_emails(self, params: Dict[str, Any]) -> SkillResponse:
        """Read emails from folder."""
        folder = params.get("folder", "INBOX")
        limit = params.get("limit", 10)
        unread_only = params.get("unread_only", False)
        since_days = params.get("since_days")
        include_body = params.get("include_body", True)

        imap = self._get_imap_connection()
        try:
            imap.select(folder)

            # Build search criteria
            criteria = []
            if unread_only:
                criteria.append("UNSEEN")
            if since_days:
                since_date = datetime.now() - timedelta(days=since_days)
                criteria.append(f'SINCE {since_date.strftime("%d-%b-%Y")}')

            search_criteria = " ".join(criteria) if criteria else "ALL"

            _, message_numbers = imap.search(None, search_criteria)
            email_ids = message_numbers[0].split()

            # Get latest N emails
            email_ids = email_ids[-limit:] if limit else email_ids
            email_ids = email_ids[::-1]  # Newest first

            emails = []
            for eid in email_ids:
                _, msg_data = imap.fetch(eid, "(RFC822)")
                if msg_data[0]:
                    msg = email.message_from_bytes(msg_data[0][1])
                    parsed = self._parse_email(msg, include_body)
                    parsed["id"] = eid.decode()
                    emails.append(parsed)

            return SkillResponse(
                success=True,
                message=f"Fetched {len(emails)} email(s) from {folder}",
                data={"emails": emails, "folder": folder, "total_matched": len(message_numbers[0].split())}
            )
        finally:
            imap.logout()

    def _search_emails(self, params: Dict[str, Any]) -> SkillResponse:
        """Search emails with criteria."""
        folder = params.get("folder", "INBOX")
        limit = params.get("limit", 20)

        imap = self._get_imap_connection()
        try:
            imap.select(folder)

            # Build IMAP search criteria
            criteria = []

            if params.get("from_address"):
                criteria.append(f'FROM "{params["from_address"]}"')
            if params.get("to_address"):
                criteria.append(f'TO "{params["to_address"]}"')
            if params.get("subject"):
                criteria.append(f'SUBJECT "{params["subject"]}"')
            if params.get("body_contains"):
                criteria.append(f'BODY "{params["body_contains"]}"')
            if params.get("since"):
                criteria.append(f'SINCE {params["since"]}')
            if params.get("before"):
                criteria.append(f'BEFORE {params["before"]}')
            if params.get("flagged") is True:
                criteria.append("FLAGGED")
            elif params.get("flagged") is False:
                criteria.append("UNFLAGGED")

            search_criteria = " ".join(criteria) if criteria else "ALL"

            _, message_numbers = imap.search(None, search_criteria)
            email_ids = message_numbers[0].split()[-limit:]

            emails = []
            for eid in reversed(email_ids):
                _, msg_data = imap.fetch(eid, "(RFC822)")
                if msg_data[0]:
                    msg = email.message_from_bytes(msg_data[0][1])
                    parsed = self._parse_email(msg, include_body=False)
                    parsed["id"] = eid.decode()
                    emails.append(parsed)

            return SkillResponse(
                success=True,
                message=f"Found {len(emails)} email(s)",
                data={"emails": emails, "criteria": search_criteria}
            )
        finally:
            imap.logout()

    def _get_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Get specific email by ID."""
        email_id = params["email_id"]
        folder = params.get("folder", "INBOX")
        mark_read = params.get("mark_read", False)

        imap = self._get_imap_connection()
        try:
            imap.select(folder)

            _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
            if not msg_data[0]:
                return SkillResponse(
                    success=False,
                    message=f"Email {email_id} not found",
                    error="not_found"
                )

            msg = email.message_from_bytes(msg_data[0][1])
            parsed = self._parse_email(msg, include_body=True)
            parsed["id"] = email_id

            if mark_read:
                imap.store(email_id.encode(), "+FLAGS", "\\Seen")

            return SkillResponse(
                success=True,
                message="Email retrieved",
                data={"email": parsed}
            )
        finally:
            imap.logout()

    def _list_folders(self) -> SkillResponse:
        """List email folders."""
        imap = self._get_imap_connection()
        try:
            _, folders = imap.list()

            folder_list = []
            for folder in folders:
                # Parse folder response
                match = re.search(r'\(.*?\) ".*?" "?([^"]+)"?$', folder.decode())
                if match:
                    folder_list.append(match.group(1))

            return SkillResponse(
                success=True,
                message=f"Found {len(folder_list)} folder(s)",
                data={"folders": folder_list}
            )
        finally:
            imap.logout()

    def _move_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Move email to another folder."""
        email_id = params["email_id"]
        source_folder = params.get("source_folder", "INBOX")
        dest_folder = params["dest_folder"]

        imap = self._get_imap_connection()
        try:
            imap.select(source_folder)

            # Copy to destination
            imap.copy(email_id.encode(), dest_folder)

            # Delete from source
            imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
            imap.expunge()

            return SkillResponse(
                success=True,
                message=f"Email moved to {dest_folder}",
                data={"email_id": email_id, "dest_folder": dest_folder}
            )
        finally:
            imap.logout()

    def _delete_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Delete email."""
        email_id = params["email_id"]
        folder = params.get("folder", "INBOX")
        permanent = params.get("permanent", False)

        imap = self._get_imap_connection()
        try:
            imap.select(folder)

            if permanent:
                imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
                imap.expunge()
            else:
                # Move to Trash
                imap.copy(email_id.encode(), "[Gmail]/Trash")
                imap.store(email_id.encode(), "+FLAGS", "\\Deleted")
                imap.expunge()

            return SkillResponse(
                success=True,
                message=f"Email deleted {'permanently' if permanent else '(moved to trash)'}",
                data={"email_id": email_id, "permanent": permanent}
            )
        finally:
            imap.logout()

    def _mark_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Mark email as read/unread/flagged."""
        email_id = params["email_id"]
        folder = params.get("folder", "INBOX")

        imap = self._get_imap_connection()
        try:
            imap.select(folder)

            actions = []

            if "read" in params:
                if params["read"]:
                    imap.store(email_id.encode(), "+FLAGS", "\\Seen")
                    actions.append("marked as read")
                else:
                    imap.store(email_id.encode(), "-FLAGS", "\\Seen")
                    actions.append("marked as unread")

            if "flagged" in params:
                if params["flagged"]:
                    imap.store(email_id.encode(), "+FLAGS", "\\Flagged")
                    actions.append("flagged")
                else:
                    imap.store(email_id.encode(), "-FLAGS", "\\Flagged")
                    actions.append("unflagged")

            return SkillResponse(
                success=True,
                message=f"Email {', '.join(actions)}",
                data={"email_id": email_id, "actions": actions}
            )
        finally:
            imap.logout()

    def _reply_email(self, params: Dict[str, Any]) -> SkillResponse:
        """Reply to an email."""
        email_id = params["email_id"]
        folder = params.get("folder", "INBOX")
        body = params["body"]
        reply_all = params.get("reply_all", False)
        include_original = params.get("include_original", True)

        # First get the original email
        imap = self._get_imap_connection()
        try:
            imap.select(folder)
            _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
            if not msg_data[0]:
                return SkillResponse(
                    success=False,
                    message=f"Email {email_id} not found",
                    error="not_found"
                )

            original = email.message_from_bytes(msg_data[0][1])
            original_parsed = self._parse_email(original, include_body=True)
        finally:
            imap.logout()

        # Build reply
        to = [original_parsed["from"]]
        if reply_all:
            # Add original recipients (except self)
            orig_to = original_parsed.get("to", "").split(",")
            orig_cc = original_parsed.get("cc", "").split(",")
            for addr in orig_to + orig_cc:
                addr = addr.strip()
                if addr and self.email_user not in addr:
                    to.append(addr)

        # Subject with Re:
        subject = original_parsed["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Body with original
        if include_original:
            original_body = original_parsed.get("body", "")
            quoted = "\n".join(f"> {line}" for line in original_body.split("\n"))
            full_body = f"{body}\n\n--- Original Message ---\n{quoted}"
        else:
            full_body = body

        # Send reply
        return self._send_email({
            "to": to,
            "subject": subject,
            "body": full_body,
            "html": False
        })

    def _save_draft(self, params: Dict[str, Any]) -> SkillResponse:
        """Save email as draft."""
        to = params.get("to", [])
        subject = params["subject"]
        body = params["body"]
        is_html = params.get("html", False)

        # Create message
        if is_html:
            msg = MIMEText(body, "html")
        else:
            msg = MIMEText(body, "plain")

        msg["Subject"] = subject
        msg["From"] = self.default_from or self.email_user
        if to:
            msg["To"] = ", ".join(to)

        # Save to Drafts
        imap = self._get_imap_connection()
        try:
            # Try common draft folder names
            for folder in ["Drafts", "[Gmail]/Drafts", "INBOX.Drafts"]:
                try:
                    imap.append(folder, "", None, msg.as_bytes())
                    return SkillResponse(
                        success=True,
                        message=f"Draft saved to {folder}",
                        data={"folder": folder, "subject": subject}
                    )
                except imaplib.IMAP4.error:
                    continue

            return SkillResponse(
                success=False,
                message="Could not find Drafts folder",
                error="drafts_folder_not_found"
            )
        finally:
            imap.logout()
