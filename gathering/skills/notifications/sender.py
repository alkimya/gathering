"""
Notifications Skill for GatheRing.
Provides webhooks, push notifications, and multi-channel messaging.
"""

import os
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.parse

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class NotificationsSkill(BaseSkill):
    """
    Skill for sending notifications across multiple channels.

    Features:
    - Webhooks (generic, Slack, Discord, Teams)
    - Push notifications (Firebase, OneSignal)
    - SMS (Twilio)
    - Desktop notifications

    Security:
    - Webhook signature verification
    - Rate limiting support
    - Credential management via env vars
    """

    name = "notifications"
    description = "Webhooks, push notifications, and messaging"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Webhook configurations
        self.slack_webhook = self.config.get("slack_webhook", os.getenv("SLACK_WEBHOOK_URL")) if self.config else os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook = self.config.get("discord_webhook", os.getenv("DISCORD_WEBHOOK_URL")) if self.config else os.getenv("DISCORD_WEBHOOK_URL")
        self.teams_webhook = self.config.get("teams_webhook", os.getenv("TEAMS_WEBHOOK_URL")) if self.config else os.getenv("TEAMS_WEBHOOK_URL")

        # Push notification configs
        self.firebase_key = self.config.get("firebase_key", os.getenv("FIREBASE_SERVER_KEY")) if self.config else os.getenv("FIREBASE_SERVER_KEY")
        self.onesignal_app_id = self.config.get("onesignal_app_id", os.getenv("ONESIGNAL_APP_ID")) if self.config else os.getenv("ONESIGNAL_APP_ID")
        self.onesignal_api_key = self.config.get("onesignal_api_key", os.getenv("ONESIGNAL_API_KEY")) if self.config else os.getenv("ONESIGNAL_API_KEY")

        # SMS config
        self.twilio_sid = self.config.get("twilio_sid", os.getenv("TWILIO_ACCOUNT_SID")) if self.config else os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = self.config.get("twilio_token", os.getenv("TWILIO_AUTH_TOKEN")) if self.config else os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = self.config.get("twilio_from", os.getenv("TWILIO_FROM_NUMBER")) if self.config else os.getenv("TWILIO_FROM_NUMBER")

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "notify_webhook",
                "description": "Send a generic webhook POST request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Webhook URL"
                        },
                        "payload": {
                            "type": "object",
                            "description": "JSON payload to send"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Additional headers"
                        },
                        "secret": {
                            "type": "string",
                            "description": "Secret for HMAC signature (optional)"
                        },
                        "signature_header": {
                            "type": "string",
                            "description": "Header name for signature",
                            "default": "X-Webhook-Signature"
                        }
                    },
                    "required": ["url", "payload"]
                }
            },
            {
                "name": "notify_slack",
                "description": "Send a Slack notification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "channel": {
                            "type": "string",
                            "description": "Channel override (if webhook supports)"
                        },
                        "username": {
                            "type": "string",
                            "description": "Bot username override"
                        },
                        "icon_emoji": {
                            "type": "string",
                            "description": "Bot icon emoji (e.g., ':robot:')"
                        },
                        "attachments": {
                            "type": "array",
                            "description": "Rich message attachments",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "text": {"type": "string"},
                                    "color": {"type": "string"},
                                    "fields": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "title": {"type": "string"},
                                                "value": {"type": "string"},
                                                "short": {"type": "boolean"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Slack Block Kit blocks"
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Custom webhook URL (overrides default)"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "notify_discord",
                "description": "Send a Discord notification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "username": {
                            "type": "string",
                            "description": "Bot username override"
                        },
                        "avatar_url": {
                            "type": "string",
                            "description": "Bot avatar URL"
                        },
                        "embeds": {
                            "type": "array",
                            "description": "Rich embeds",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "color": {"type": "integer"},
                                    "url": {"type": "string"},
                                    "fields": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "value": {"type": "string"},
                                                "inline": {"type": "boolean"}
                                            }
                                        }
                                    },
                                    "footer": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Custom webhook URL"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "notify_teams",
                "description": "Send a Microsoft Teams notification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Card title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "theme_color": {
                            "type": "string",
                            "description": "Card accent color (hex without #)"
                        },
                        "sections": {
                            "type": "array",
                            "description": "Card sections",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "facts": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "value": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "actions": {
                            "type": "array",
                            "description": "Action buttons",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "url": {"type": "string"}
                                }
                            }
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Custom webhook URL"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "notify_push_firebase",
                "description": "Send push notification via Firebase Cloud Messaging",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Device FCM token"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Topic to send to (alternative to token)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Notification title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Notification body"
                        },
                        "data": {
                            "type": "object",
                            "description": "Custom data payload"
                        },
                        "icon": {
                            "type": "string",
                            "description": "Notification icon URL"
                        },
                        "click_action": {
                            "type": "string",
                            "description": "Action on click"
                        }
                    },
                    "required": ["title", "body"]
                }
            },
            {
                "name": "notify_push_onesignal",
                "description": "Send push notification via OneSignal",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "player_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific player IDs"
                        },
                        "segments": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "User segments (e.g., ['All'])"
                        },
                        "title": {
                            "type": "string",
                            "description": "Notification title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Notification message"
                        },
                        "data": {
                            "type": "object",
                            "description": "Custom data"
                        },
                        "url": {
                            "type": "string",
                            "description": "Launch URL"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "notify_sms",
                "description": "Send SMS via Twilio",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient phone number (E.164 format)"
                        },
                        "message": {
                            "type": "string",
                            "description": "SMS message (max 1600 chars)"
                        },
                        "from_number": {
                            "type": "string",
                            "description": "Sender number (overrides default)"
                        }
                    },
                    "required": ["to", "message"]
                }
            },
            {
                "name": "notify_desktop",
                "description": "Send desktop notification (local)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Notification title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Notification message"
                        },
                        "icon": {
                            "type": "string",
                            "description": "Icon path"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Display timeout in seconds",
                            "default": 10
                        }
                    },
                    "required": ["title", "message"]
                }
            },
            {
                "name": "notify_batch",
                "description": "Send notifications to multiple channels at once",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channels": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["slack", "discord", "teams", "desktop"]
                            },
                            "description": "Channels to send to"
                        },
                        "title": {
                            "type": "string",
                            "description": "Notification title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Notification message"
                        }
                    },
                    "required": ["channels", "message"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute notification tool."""
        try:
            if tool_name == "notify_webhook":
                return self._send_webhook(tool_input)
            elif tool_name == "notify_slack":
                return self._send_slack(tool_input)
            elif tool_name == "notify_discord":
                return self._send_discord(tool_input)
            elif tool_name == "notify_teams":
                return self._send_teams(tool_input)
            elif tool_name == "notify_push_firebase":
                return self._send_firebase(tool_input)
            elif tool_name == "notify_push_onesignal":
                return self._send_onesignal(tool_input)
            elif tool_name == "notify_sms":
                return self._send_sms(tool_input)
            elif tool_name == "notify_desktop":
                return self._send_desktop(tool_input)
            elif tool_name == "notify_batch":
                return self._send_batch(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )
        except Exception as e:
            logger.exception(f"Notification tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Notification failed: {str(e)}",
                error=str(e)
            )

    def _http_post(self, url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send HTTP POST request."""
        data = json.dumps(payload).encode("utf-8")

        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, data=data, headers=req_headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                body = response.read().decode("utf-8")
                return {"status": status, "body": body}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "body": e.read().decode("utf-8"), "error": str(e)}

    def _send_webhook(self, params: Dict[str, Any]) -> SkillResponse:
        """Send generic webhook."""
        url = params["url"]
        payload = params["payload"]
        headers = params.get("headers", {})
        secret = params.get("secret")
        sig_header = params.get("signature_header", "X-Webhook-Signature")

        # Add signature if secret provided
        if secret:
            payload_str = json.dumps(payload)
            signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers[sig_header] = f"sha256={signature}"

        result = self._http_post(url, payload, headers)

        if result.get("error") or result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message=f"Webhook failed: HTTP {result.get('status')}",
                error=result.get("body"),
                data=result
            )

        return SkillResponse(
            success=True,
            message="Webhook sent successfully",
            data={"url": url, "status": result.get("status")}
        )

    def _send_slack(self, params: Dict[str, Any]) -> SkillResponse:
        """Send Slack notification."""
        webhook_url = params.get("webhook_url", self.slack_webhook)

        if not webhook_url:
            return SkillResponse(
                success=False,
                message="Slack webhook URL not configured",
                error="missing_config"
            )

        payload = {"text": params["message"]}

        if params.get("channel"):
            payload["channel"] = params["channel"]
        if params.get("username"):
            payload["username"] = params["username"]
        if params.get("icon_emoji"):
            payload["icon_emoji"] = params["icon_emoji"]
        if params.get("attachments"):
            payload["attachments"] = params["attachments"]
        if params.get("blocks"):
            payload["blocks"] = params["blocks"]

        result = self._http_post(webhook_url, payload)

        if result.get("body") != "ok" and result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message="Slack notification failed",
                error=result.get("body")
            )

        return SkillResponse(
            success=True,
            message="Slack notification sent",
            data={"channel": params.get("channel")}
        )

    def _send_discord(self, params: Dict[str, Any]) -> SkillResponse:
        """Send Discord notification."""
        webhook_url = params.get("webhook_url", self.discord_webhook)

        if not webhook_url:
            return SkillResponse(
                success=False,
                message="Discord webhook URL not configured",
                error="missing_config"
            )

        payload = {"content": params["message"]}

        if params.get("username"):
            payload["username"] = params["username"]
        if params.get("avatar_url"):
            payload["avatar_url"] = params["avatar_url"]
        if params.get("embeds"):
            payload["embeds"] = params["embeds"]

        result = self._http_post(webhook_url, payload)

        if result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message="Discord notification failed",
                error=result.get("body")
            )

        return SkillResponse(
            success=True,
            message="Discord notification sent",
            data={}
        )

    def _send_teams(self, params: Dict[str, Any]) -> SkillResponse:
        """Send Microsoft Teams notification."""
        webhook_url = params.get("webhook_url", self.teams_webhook)

        if not webhook_url:
            return SkillResponse(
                success=False,
                message="Teams webhook URL not configured",
                error="missing_config"
            )

        # Build MessageCard format
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": params["message"],
            "text": params["message"],
        }

        if params.get("title"):
            payload["title"] = params["title"]
        if params.get("theme_color"):
            payload["themeColor"] = params["theme_color"]
        if params.get("sections"):
            payload["sections"] = params["sections"]
        if params.get("actions"):
            payload["potentialAction"] = [
                {"@type": "OpenUri", "name": a["name"], "targets": [{"os": "default", "uri": a["url"]}]}
                for a in params["actions"]
            ]

        result = self._http_post(webhook_url, payload)

        if result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message="Teams notification failed",
                error=result.get("body")
            )

        return SkillResponse(
            success=True,
            message="Teams notification sent",
            data={}
        )

    def _send_firebase(self, params: Dict[str, Any]) -> SkillResponse:
        """Send Firebase Cloud Messaging notification."""
        if not self.firebase_key:
            return SkillResponse(
                success=False,
                message="Firebase server key not configured",
                error="missing_config"
            )

        payload = {
            "notification": {
                "title": params["title"],
                "body": params["body"],
            }
        }

        if params.get("token"):
            payload["to"] = params["token"]
        elif params.get("topic"):
            payload["to"] = f"/topics/{params['topic']}"
        else:
            return SkillResponse(
                success=False,
                message="Either token or topic is required",
                error="missing_parameter"
            )

        if params.get("data"):
            payload["data"] = params["data"]
        if params.get("icon"):
            payload["notification"]["icon"] = params["icon"]
        if params.get("click_action"):
            payload["notification"]["click_action"] = params["click_action"]

        result = self._http_post(
            "https://fcm.googleapis.com/fcm/send",
            payload,
            {"Authorization": f"key={self.firebase_key}"}
        )

        if result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message="Firebase notification failed",
                error=result.get("body")
            )

        return SkillResponse(
            success=True,
            message="Firebase notification sent",
            data={"response": result.get("body")}
        )

    def _send_onesignal(self, params: Dict[str, Any]) -> SkillResponse:
        """Send OneSignal push notification."""
        if not self.onesignal_app_id or not self.onesignal_api_key:
            return SkillResponse(
                success=False,
                message="OneSignal credentials not configured",
                error="missing_config"
            )

        payload = {
            "app_id": self.onesignal_app_id,
            "contents": {"en": params["message"]},
        }

        if params.get("title"):
            payload["headings"] = {"en": params["title"]}
        if params.get("player_ids"):
            payload["include_player_ids"] = params["player_ids"]
        elif params.get("segments"):
            payload["included_segments"] = params["segments"]
        else:
            payload["included_segments"] = ["All"]

        if params.get("data"):
            payload["data"] = params["data"]
        if params.get("url"):
            payload["url"] = params["url"]

        result = self._http_post(
            "https://onesignal.com/api/v1/notifications",
            payload,
            {"Authorization": f"Basic {self.onesignal_api_key}"}
        )

        if result.get("status", 0) >= 400:
            return SkillResponse(
                success=False,
                message="OneSignal notification failed",
                error=result.get("body")
            )

        return SkillResponse(
            success=True,
            message="OneSignal notification sent",
            data={"response": result.get("body")}
        )

    def _send_sms(self, params: Dict[str, Any]) -> SkillResponse:
        """Send SMS via Twilio."""
        if not self.twilio_sid or not self.twilio_token:
            return SkillResponse(
                success=False,
                message="Twilio credentials not configured",
                error="missing_config"
            )

        from_number = params.get("from_number", self.twilio_from)
        if not from_number:
            return SkillResponse(
                success=False,
                message="Twilio from number not configured",
                error="missing_config"
            )

        # Twilio requires form-urlencoded data
        data = urllib.parse.urlencode({
            "To": params["to"],
            "From": from_number,
            "Body": params["message"][:1600],  # SMS limit
        }).encode()

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"

        # Basic auth
        import base64
        auth = base64.b64encode(f"{self.twilio_sid}:{self.twilio_token}".encode()).decode()

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                return SkillResponse(
                    success=True,
                    message=f"SMS sent to {params['to']}",
                    data={"sid": body.get("sid"), "status": body.get("status")}
                )
        except urllib.error.HTTPError as e:
            return SkillResponse(
                success=False,
                message="SMS sending failed",
                error=e.read().decode("utf-8")
            )

    def _send_desktop(self, params: Dict[str, Any]) -> SkillResponse:
        """Send desktop notification."""
        title = params["title"]
        message = params["message"]
        icon = params.get("icon")
        timeout = params.get("timeout", 10)

        try:
            # Try different notification methods based on platform
            import platform
            system = platform.system()

            if system == "Darwin":  # macOS
                import subprocess
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=True)

            elif system == "Linux":
                import subprocess
                cmd = ["notify-send", title, message]
                if icon:
                    cmd.extend(["-i", icon])
                cmd.extend(["-t", str(timeout * 1000)])
                subprocess.run(cmd, check=True)

            elif system == "Windows":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, icon_path=icon, duration=timeout)
                except ImportError:
                    # Fallback to plyer
                    from plyer import notification
                    notification.notify(title=title, message=message, timeout=timeout)

            else:
                # Try plyer as fallback
                from plyer import notification
                notification.notify(title=title, message=message, timeout=timeout)

            return SkillResponse(
                success=True,
                message="Desktop notification sent",
                data={"title": title, "platform": system}
            )

        except ImportError as e:
            return SkillResponse(
                success=False,
                message=f"Desktop notification library not available: {e}",
                error=str(e)
            )
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Desktop notification failed: {e}",
                error=str(e)
            )

    def _send_batch(self, params: Dict[str, Any]) -> SkillResponse:
        """Send to multiple channels."""
        channels = params["channels"]
        title = params.get("title", "")
        message = params["message"]

        results = {}
        success_count = 0

        for channel in channels:
            try:
                if channel == "slack":
                    result = self._send_slack({"message": f"*{title}*\n{message}" if title else message})
                elif channel == "discord":
                    result = self._send_discord({"message": f"**{title}**\n{message}" if title else message})
                elif channel == "teams":
                    result = self._send_teams({"title": title, "message": message})
                elif channel == "desktop":
                    result = self._send_desktop({"title": title or "Notification", "message": message})
                else:
                    result = SkillResponse(success=False, message=f"Unknown channel: {channel}")

                results[channel] = {"success": result.success, "message": result.message}
                if result.success:
                    success_count += 1

            except Exception as e:
                results[channel] = {"success": False, "message": str(e)}

        return SkillResponse(
            success=success_count > 0,
            message=f"Sent to {success_count}/{len(channels)} channel(s)",
            data={"results": results}
        )
