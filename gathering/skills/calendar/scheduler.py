"""
Calendar Skill for GatheRing.
Provides calendar operations for Google Calendar and Outlook.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class CalendarProvider(ABC):
    """Abstract base class for calendar providers."""

    @abstractmethod
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List available calendars."""
        pass

    @abstractmethod
    def list_events(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List events in a date range."""
        pass

    @abstractmethod
    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Get a specific event."""
        pass

    @abstractmethod
    def create_event(self, calendar_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event."""
        pass

    @abstractmethod
    def update_event(self, calendar_id: str, event_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing event."""
        pass

    @abstractmethod
    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete an event."""
        pass

    @abstractmethod
    def find_free_slots(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Find free time slots."""
        pass


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.credentials_path = config.get("credentials_path", os.getenv("GOOGLE_CALENDAR_CREDENTIALS"))
        self.token_path = config.get("token_path", os.getenv("GOOGLE_CALENDAR_TOKEN"))
        self._service = None

    def _get_service(self):
        """Get or create Google Calendar service."""
        if self._service is None:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/calendar"]

            creds = None
            if self.token_path and os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                if self.token_path:
                    with open(self.token_path, "w") as token:
                        token.write(creds.to_json())

            self._service = build("calendar", "v3", credentials=creds)

        return self._service

    def list_calendars(self) -> List[Dict[str, Any]]:
        service = self._get_service()
        result = service.calendarList().list().execute()

        return [
            {
                "id": cal["id"],
                "name": cal.get("summary", ""),
                "description": cal.get("description", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
            }
            for cal in result.get("items", [])
        ]

    def list_events(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        service = self._get_service()

        result = service.events().list(
            calendarId=calendar_id,
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        return [
            self._parse_event(event)
            for event in result.get("items", [])
        ]

    def _parse_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Google Calendar event to standard format."""
        start = event.get("start", {})
        end = event.get("end", {})

        return {
            "id": event["id"],
            "title": event.get("summary", ""),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "all_day": "date" in start,
            "status": event.get("status", ""),
            "attendees": [
                {"email": a.get("email"), "status": a.get("responseStatus")}
                for a in event.get("attendees", [])
            ],
            "organizer": event.get("organizer", {}).get("email"),
            "recurrence": event.get("recurrence"),
            "html_link": event.get("htmlLink"),
        }

    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        service = self._get_service()
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return self._parse_event(event)

    def create_event(self, calendar_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        service = self._get_service()

        google_event = {
            "summary": event["title"],
            "description": event.get("description", ""),
            "location": event.get("location", ""),
        }

        # Handle all-day vs timed events
        if event.get("all_day"):
            google_event["start"] = {"date": event["start"][:10]}
            google_event["end"] = {"date": event["end"][:10]}
        else:
            google_event["start"] = {"dateTime": event["start"], "timeZone": event.get("timezone", "UTC")}
            google_event["end"] = {"dateTime": event["end"], "timeZone": event.get("timezone", "UTC")}

        # Add attendees
        if event.get("attendees"):
            google_event["attendees"] = [{"email": a} for a in event["attendees"]]

        # Add recurrence
        if event.get("recurrence"):
            google_event["recurrence"] = event["recurrence"]

        result = service.events().insert(calendarId=calendar_id, body=google_event).execute()
        return self._parse_event(result)

    def update_event(self, calendar_id: str, event_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        service = self._get_service()

        # Get existing event
        existing = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update fields
        if "title" in event:
            existing["summary"] = event["title"]
        if "description" in event:
            existing["description"] = event["description"]
        if "location" in event:
            existing["location"] = event["location"]
        if "start" in event:
            if event.get("all_day"):
                existing["start"] = {"date": event["start"][:10]}
            else:
                existing["start"] = {"dateTime": event["start"]}
        if "end" in event:
            if event.get("all_day"):
                existing["end"] = {"date": event["end"][:10]}
            else:
                existing["end"] = {"dateTime": event["end"]}

        result = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=existing
        ).execute()
        return self._parse_event(result)

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        service = self._get_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True

    def find_free_slots(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        service = self._get_service()

        body = {
            "timeMin": start.isoformat() + "Z",
            "timeMax": end.isoformat() + "Z",
            "items": [{"id": calendar_id}],
        }

        result = service.freebusy().query(body=body).execute()
        busy_times = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])

        # Calculate free slots
        free_slots = []
        current = start

        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))

            if current < busy_start:
                slot_duration = (busy_start - current).total_seconds() / 60
                if slot_duration >= duration_minutes:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": busy_start.isoformat(),
                        "duration_minutes": int(slot_duration),
                    })
            current = max(current, busy_end)

        # Check remaining time
        if current < end:
            slot_duration = (end - current).total_seconds() / 60
            if slot_duration >= duration_minutes:
                free_slots.append({
                    "start": current.isoformat(),
                    "end": end.isoformat(),
                    "duration_minutes": int(slot_duration),
                })

        return free_slots


class OutlookCalendarProvider(CalendarProvider):
    """Microsoft Outlook/365 calendar provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get("client_id", os.getenv("OUTLOOK_CLIENT_ID"))
        self.client_secret = config.get("client_secret", os.getenv("OUTLOOK_CLIENT_SECRET"))
        self.tenant_id = config.get("tenant_id", os.getenv("OUTLOOK_TENANT_ID", "common"))
        self.token_path = config.get("token_path", os.getenv("OUTLOOK_TOKEN_PATH"))
        self._client = None

    def _get_client(self):
        """Get or create Microsoft Graph client."""
        if self._client is None:
            import msal
            import requests

            authority = f"https://login.microsoftonline.com/{self.tenant_id}"

            # Try to load cached token
            token = None
            if self.token_path and os.path.exists(self.token_path):
                with open(self.token_path, "r") as f:
                    token = json.load(f)

            if not token:
                app = msal.PublicClientApplication(
                    self.client_id,
                    authority=authority,
                )

                # Interactive login
                result = app.acquire_token_interactive(
                    scopes=["https://graph.microsoft.com/Calendars.ReadWrite"]
                )
                token = result

                if self.token_path:
                    with open(self.token_path, "w") as f:
                        json.dump(token, f)

            self._access_token = token.get("access_token")
            self._client = requests.Session()
            self._client.headers.update({
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            })

        return self._client

    def _graph_request(self, method: str, endpoint: str, data: Any = None) -> Dict[str, Any]:
        """Make a Microsoft Graph API request."""
        client = self._get_client()
        url = f"https://graph.microsoft.com/v1.0{endpoint}"

        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            response = client.post(url, json=data)
        elif method == "PATCH":
            response = client.patch(url, json=data)
        elif method == "DELETE":
            response = client.delete(url)
            return {"success": response.status_code == 204}

        response.raise_for_status()
        return response.json()

    def list_calendars(self) -> List[Dict[str, Any]]:
        result = self._graph_request("GET", "/me/calendars")

        return [
            {
                "id": cal["id"],
                "name": cal.get("name", ""),
                "color": cal.get("color", ""),
                "can_edit": cal.get("canEdit", False),
                "is_default": cal.get("isDefaultCalendar", False),
            }
            for cal in result.get("value", [])
        ]

    def list_events(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        endpoint = f"/me/calendars/{calendar_id}/calendarView"
        params = f"?startDateTime={start.isoformat()}Z&endDateTime={end.isoformat()}Z&$top={max_results}"

        result = self._graph_request("GET", endpoint + params)

        return [
            self._parse_event(event)
            for event in result.get("value", [])
        ]

    def _parse_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Outlook event to standard format."""
        start = event.get("start", {})
        end = event.get("end", {})

        return {
            "id": event["id"],
            "title": event.get("subject", ""),
            "description": event.get("bodyPreview", ""),
            "location": event.get("location", {}).get("displayName", ""),
            "start": start.get("dateTime"),
            "end": end.get("dateTime"),
            "all_day": event.get("isAllDay", False),
            "status": event.get("showAs", ""),
            "attendees": [
                {"email": a.get("emailAddress", {}).get("address"), "status": a.get("status", {}).get("response")}
                for a in event.get("attendees", [])
            ],
            "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address"),
            "web_link": event.get("webLink"),
        }

    def get_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        result = self._graph_request("GET", f"/me/calendars/{calendar_id}/events/{event_id}")
        return self._parse_event(result)

    def create_event(self, calendar_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        outlook_event = {
            "subject": event["title"],
            "body": {"contentType": "text", "content": event.get("description", "")},
            "start": {"dateTime": event["start"], "timeZone": event.get("timezone", "UTC")},
            "end": {"dateTime": event["end"], "timeZone": event.get("timezone", "UTC")},
            "isAllDay": event.get("all_day", False),
        }

        if event.get("location"):
            outlook_event["location"] = {"displayName": event["location"]}

        if event.get("attendees"):
            outlook_event["attendees"] = [
                {"emailAddress": {"address": a}, "type": "required"}
                for a in event["attendees"]
            ]

        result = self._graph_request("POST", f"/me/calendars/{calendar_id}/events", outlook_event)
        return self._parse_event(result)

    def update_event(self, calendar_id: str, event_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        updates = {}

        if "title" in event:
            updates["subject"] = event["title"]
        if "description" in event:
            updates["body"] = {"contentType": "text", "content": event["description"]}
        if "location" in event:
            updates["location"] = {"displayName": event["location"]}
        if "start" in event:
            updates["start"] = {"dateTime": event["start"], "timeZone": event.get("timezone", "UTC")}
        if "end" in event:
            updates["end"] = {"dateTime": event["end"], "timeZone": event.get("timezone", "UTC")}

        result = self._graph_request("PATCH", f"/me/calendars/{calendar_id}/events/{event_id}", updates)
        return self._parse_event(result)

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        result = self._graph_request("DELETE", f"/me/calendars/{calendar_id}/events/{event_id}")
        return result.get("success", False)

    def find_free_slots(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        body = {
            "schedules": [calendar_id],
            "startTime": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "endTime": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "availabilityViewInterval": duration_minutes,
        }

        result = self._graph_request("POST", "/me/calendar/getSchedule", body)

        # Parse availability view
        free_slots = []
        schedule = result.get("value", [{}])[0]
        availability = schedule.get("availabilityView", "")

        current_time = start
        slot_duration = timedelta(minutes=duration_minutes)

        for char in availability:
            if char == "0":  # Free
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": (current_time + slot_duration).isoformat(),
                    "duration_minutes": duration_minutes,
                })
            current_time += slot_duration

        return free_slots


class CalendarSkill(BaseSkill):
    """
    Multi-provider calendar operations skill.

    Features:
    - Google Calendar integration
    - Outlook/Microsoft 365 integration
    - Event CRUD operations
    - Free/busy lookup
    - Meeting scheduling

    Security:
    - OAuth2 authentication
    - Scoped calendar access
    """

    name = "calendar"
    description = "Calendar operations (Google Calendar, Outlook)"
    version = "1.0.0"
    required_permissions = [SkillPermission.NETWORK]

    PROVIDERS = {
        "google": GoogleCalendarProvider,
        "outlook": OutlookCalendarProvider,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._providers: Dict[str, CalendarProvider] = {}
        self.default_provider = self.config.get("default_provider", "google") if self.config else "google"

    def _get_provider(self, provider_name: str) -> CalendarProvider:
        """Get or create provider instance."""
        if provider_name not in self._providers:
            if provider_name not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {provider_name}. Available: {list(self.PROVIDERS.keys())}")

            provider_config = self.config.get(provider_name, {}) if self.config else {}
            self._providers[provider_name] = self.PROVIDERS[provider_name](provider_config)

        return self._providers[provider_name]

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "calendar_list",
                "description": "List available calendars",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Calendar provider",
                            "enum": ["google", "outlook"]
                        }
                    }
                }
            },
            {
                "name": "calendar_events",
                "description": "List calendar events",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (use 'primary' for default)"
                        },
                        "start": {
                            "type": "string",
                            "description": "Start date/time (ISO format or 'today', 'tomorrow', 'this_week')"
                        },
                        "end": {
                            "type": "string",
                            "description": "End date/time (ISO format)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days from start (alternative to end)",
                            "default": 7
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum events to return",
                            "default": 50
                        }
                    }
                }
            },
            {
                "name": "calendar_get_event",
                "description": "Get a specific event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID"
                        }
                    },
                    "required": ["event_id"]
                }
            },
            {
                "name": "calendar_create_event",
                "description": "Create a new calendar event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        },
                        "title": {
                            "type": "string",
                            "description": "Event title"
                        },
                        "start": {
                            "type": "string",
                            "description": "Start date/time (ISO format)"
                        },
                        "end": {
                            "type": "string",
                            "description": "End date/time (ISO format)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description"
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Attendee email addresses"
                        },
                        "all_day": {
                            "type": "boolean",
                            "description": "All-day event",
                            "default": False
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone",
                            "default": "UTC"
                        }
                    },
                    "required": ["title", "start", "end"]
                }
            },
            {
                "name": "calendar_update_event",
                "description": "Update an existing event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to update"
                        },
                        "title": {
                            "type": "string"
                        },
                        "start": {
                            "type": "string"
                        },
                        "end": {
                            "type": "string"
                        },
                        "description": {
                            "type": "string"
                        },
                        "location": {
                            "type": "string"
                        }
                    },
                    "required": ["event_id"]
                }
            },
            {
                "name": "calendar_delete_event",
                "description": "Delete a calendar event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to delete"
                        }
                    },
                    "required": ["event_id"]
                }
            },
            {
                "name": "calendar_free_slots",
                "description": "Find free time slots",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        },
                        "start": {
                            "type": "string",
                            "description": "Start date/time"
                        },
                        "end": {
                            "type": "string",
                            "description": "End date/time"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Minimum slot duration",
                            "default": 30
                        }
                    },
                    "required": ["start", "end"]
                }
            },
            {
                "name": "calendar_today",
                "description": "Get today's events",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["google", "outlook"]
                        },
                        "calendar_id": {
                            "type": "string"
                        }
                    }
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute calendar tool."""
        try:
            provider_name = tool_input.get("provider", self.default_provider)
            provider = self._get_provider(provider_name)
            calendar_id = tool_input.get("calendar_id", "primary")

            if tool_name == "calendar_list":
                calendars = provider.list_calendars()
                return SkillResponse(
                    success=True,
                    message=f"Found {len(calendars)} calendar(s)",
                    data={"calendars": calendars, "provider": provider_name}
                )

            elif tool_name == "calendar_events":
                start, end = self._parse_date_range(tool_input)
                max_results = tool_input.get("max_results", 50)

                events = provider.list_events(calendar_id, start, end, max_results)
                return SkillResponse(
                    success=True,
                    message=f"Found {len(events)} event(s)",
                    data={
                        "events": events,
                        "calendar_id": calendar_id,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    }
                )

            elif tool_name == "calendar_get_event":
                event = provider.get_event(calendar_id, tool_input["event_id"])
                return SkillResponse(
                    success=True,
                    message="Event retrieved",
                    data={"event": event}
                )

            elif tool_name == "calendar_create_event":
                event_data = {
                    "title": tool_input["title"],
                    "start": tool_input["start"],
                    "end": tool_input["end"],
                    "description": tool_input.get("description", ""),
                    "location": tool_input.get("location", ""),
                    "attendees": tool_input.get("attendees", []),
                    "all_day": tool_input.get("all_day", False),
                    "timezone": tool_input.get("timezone", "UTC"),
                }

                event = provider.create_event(calendar_id, event_data)
                return SkillResponse(
                    success=True,
                    message=f"Event '{tool_input['title']}' created",
                    data={"event": event}
                )

            elif tool_name == "calendar_update_event":
                updates = {k: v for k, v in tool_input.items() if k not in ["provider", "calendar_id", "event_id"]}

                event = provider.update_event(calendar_id, tool_input["event_id"], updates)
                return SkillResponse(
                    success=True,
                    message="Event updated",
                    data={"event": event}
                )

            elif tool_name == "calendar_delete_event":
                provider.delete_event(calendar_id, tool_input["event_id"])
                return SkillResponse(
                    success=True,
                    message="Event deleted",
                    data={"event_id": tool_input["event_id"]}
                )

            elif tool_name == "calendar_free_slots":
                start = datetime.fromisoformat(tool_input["start"])
                end = datetime.fromisoformat(tool_input["end"])
                duration = tool_input.get("duration_minutes", 30)

                slots = provider.find_free_slots(calendar_id, start, end, duration)
                return SkillResponse(
                    success=True,
                    message=f"Found {len(slots)} free slot(s)",
                    data={"free_slots": slots, "duration_minutes": duration}
                )

            elif tool_name == "calendar_today":
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)

                events = provider.list_events(calendar_id, today, tomorrow)
                return SkillResponse(
                    success=True,
                    message=f"Found {len(events)} event(s) today",
                    data={"events": events, "date": today.date().isoformat()}
                )

            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )

        except ImportError as e:
            return SkillResponse(
                success=False,
                message=f"Calendar SDK not installed: {e}. Install: pip install google-api-python-client google-auth-oauthlib msal",
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Calendar tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Calendar operation failed: {str(e)}",
                error=str(e)
            )

    def _parse_date_range(self, params: Dict[str, Any]) -> tuple:
        """Parse start/end date range from params."""
        now = datetime.now()

        # Parse start
        start_str = params.get("start", "today")
        if start_str == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif start_str == "tomorrow":
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif start_str == "this_week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.fromisoformat(start_str)

        # Parse end
        if "end" in params:
            end = datetime.fromisoformat(params["end"])
        else:
            days = params.get("days", 7)
            end = start + timedelta(days=days)

        return start, end
