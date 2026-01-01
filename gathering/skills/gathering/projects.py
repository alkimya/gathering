"""
ProjectsSkill - Skill for managing projects and their context.

Allows agents to:
- List and get project details
- Update project conventions, notes, commands
- Switch between projects
"""

from typing import Any, Dict, List
from gathering.skills.base import BaseSkill, SkillResponse


class ProjectsSkill(BaseSkill):
    """Skill for managing GatheRing projects."""

    name = "projects"
    description = "Manage projects and their context (conventions, notes, commands)"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._db = None

    def _get_db(self):
        """Lazy load database connection."""
        if self._db is None:
            from pycopg import Database
            self._db = Database.from_env()
        return self._db

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_list",
                "description": "List all projects",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status (active, archived, all)",
                            "enum": ["active", "archived", "all"],
                            "default": "active"
                        }
                    }
                }
            },
            {
                "name": "project_get",
                "description": "Get full project details including context, conventions, and notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "project_name": {"type": "string", "description": "Project name (alternative to ID)"}
                    }
                }
            },
            {
                "name": "project_context",
                "description": "Get the formatted context prompt for a project (what agents receive)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "project_name": {"type": "string", "description": "Project name (alternative to ID)"}
                    }
                }
            },
            {
                "name": "project_add_note",
                "description": "Add an important note to a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "note": {"type": "string", "description": "Note to add"}
                    },
                    "required": ["project_id", "note"]
                }
            },
            {
                "name": "project_remove_note",
                "description": "Remove a note from a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "note_index": {"type": "integer", "description": "Index of the note to remove (0-based)"}
                    },
                    "required": ["project_id", "note_index"]
                }
            },
            {
                "name": "project_add_convention",
                "description": "Add or update a convention for a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "key": {"type": "string", "description": "Convention key (e.g., 'imports', 'naming')"},
                        "value": {"type": "string", "description": "Convention value"}
                    },
                    "required": ["project_id", "key", "value"]
                }
            },
            {
                "name": "project_add_command",
                "description": "Add or update a frequent command for a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "name": {"type": "string", "description": "Command name (e.g., 'test', 'build')"},
                        "command": {"type": "string", "description": "The command to run"}
                    },
                    "required": ["project_id", "name", "command"]
                }
            },
            {
                "name": "project_add_key_file",
                "description": "Add or update an important file/directory reference",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "name": {"type": "string", "description": "Reference name (e.g., 'models', 'config')"},
                        "path": {"type": "string", "description": "File or directory path"}
                    },
                    "required": ["project_id", "name", "path"]
                }
            },
            {
                "name": "project_update",
                "description": "Update project metadata",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "Project ID"},
                        "display_name": {"type": "string", "description": "Display name"},
                        "description": {"type": "string", "description": "Project description"},
                        "python_version": {"type": "string", "description": "Python version"},
                        "venv_path": {"type": "string", "description": "Virtual environment path"}
                    },
                    "required": ["project_id"]
                }
            }
        ]

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> SkillResponse:
        handlers = {
            "project_list": self._project_list,
            "project_get": self._project_get,
            "project_context": self._project_context,
            "project_add_note": self._project_add_note,
            "project_remove_note": self._project_remove_note,
            "project_add_convention": self._project_add_convention,
            "project_add_command": self._project_add_command,
            "project_add_key_file": self._project_add_key_file,
            "project_update": self._project_update,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return SkillResponse(success=False, message="Unknown tool", error=f"Unknown tool: {tool_name}")

        try:
            return handler(arguments)
        except Exception as e:
            return SkillResponse(success=False, message="Error", error=str(e))

    def _project_list(self, args: Dict[str, Any]) -> SkillResponse:
        """List all projects."""
        db = self._get_db()
        status = args.get("status", "active")

        if status == "all":
            where_clause = ""
        elif status == "archived":
            where_clause = "WHERE status = 'archived'"
        else:
            where_clause = "WHERE status != 'archived' OR status IS NULL"

        rows = db.execute(f"""
            SELECT id, name, display_name, description, local_path,
                   branch, status, python_version
            FROM project.projects
            {where_clause}
            ORDER BY name
        """)

        return SkillResponse(
            success=True,
            message=f"Found {len(rows)} projects",
            data={"projects": rows, "count": len(rows)}
        )

    def _project_get(self, args: Dict[str, Any]) -> SkillResponse:
        """Get full project details."""
        db = self._get_db()
        project_id = args.get("project_id")
        project_name = args.get("project_name")

        if project_id:
            row = db.fetch_one(
                "SELECT * FROM project.projects WHERE id = %s",
                [project_id]
            )
        elif project_name:
            row = db.fetch_one(
                "SELECT * FROM project.projects WHERE name = %s",
                [project_name]
            )
        else:
            return SkillResponse(success=False, message="Missing parameter", error="project_id or project_name required")

        if not row:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(success=True, message=f"Project: {row['name']}", data=dict(row))

    def _project_context(self, args: Dict[str, Any]) -> SkillResponse:
        """Get formatted context prompt for a project."""
        from gathering.agents.project_context import load_project_from_db

        project_id = args.get("project_id")
        project_name = args.get("project_name")

        context = load_project_from_db(project_id=project_id, project_name=project_name)
        if not context:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message=f"Context for {context.name}",
            data={"context_prompt": context.to_prompt()}
        )

    def _project_add_note(self, args: Dict[str, Any]) -> SkillResponse:
        """Add a note to a project."""
        db = self._get_db()
        project_id = args["project_id"]
        note = args["note"]

        result = db.execute("""
            UPDATE project.projects
            SET notes = array_append(COALESCE(notes, ARRAY[]::text[]), %s),
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, notes
        """, [note, project_id])

        if not result:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message=f"Note added to project",
            data={"notes": result[0]["notes"]}
        )

    def _project_remove_note(self, args: Dict[str, Any]) -> SkillResponse:
        """Remove a note from a project."""
        db = self._get_db()
        project_id = args["project_id"]
        note_index = args["note_index"]

        # Get current notes
        row = db.fetch_one(
            "SELECT notes FROM project.projects WHERE id = %s",
            [project_id]
        )
        if not row:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        notes = row["notes"] or []
        if note_index < 0 or note_index >= len(notes):
            return SkillResponse(success=False, message="Invalid index", error=f"Invalid note index: {note_index}")

        notes.pop(note_index)

        db.execute("""
            UPDATE project.projects
            SET notes = %s, updated_at = NOW()
            WHERE id = %s
        """, [notes, project_id])

        return SkillResponse(
            success=True,
            message="Note removed",
            data={"notes": notes}
        )

    def _project_add_convention(self, args: Dict[str, Any]) -> SkillResponse:
        """Add or update a convention."""
        db = self._get_db()
        project_id = args["project_id"]
        key = args["key"]
        value = args["value"]

        result = db.execute("""
            UPDATE project.projects
            SET conventions = COALESCE(conventions, '{}'::jsonb) || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, conventions
        """, [f'{{"{key}": "{value}"}}', project_id])

        if not result:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message=f"Convention '{key}' updated",
            data={"conventions": result[0]["conventions"]}
        )

    def _project_add_command(self, args: Dict[str, Any]) -> SkillResponse:
        """Add or update a command."""
        db = self._get_db()
        project_id = args["project_id"]
        name = args["name"]
        command = args["command"]

        result = db.execute("""
            UPDATE project.projects
            SET commands = COALESCE(commands, '{}'::jsonb) || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, commands
        """, [f'{{"{name}": "{command}"}}', project_id])

        if not result:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message=f"Command '{name}' updated",
            data={"commands": result[0]["commands"]}
        )

    def _project_add_key_file(self, args: Dict[str, Any]) -> SkillResponse:
        """Add or update a key file reference."""
        db = self._get_db()
        project_id = args["project_id"]
        name = args["name"]
        path = args["path"]

        result = db.execute("""
            UPDATE project.projects
            SET key_files = COALESCE(key_files, '{}'::jsonb) || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, key_files
        """, [f'{{"{name}": "{path}"}}', project_id])

        if not result:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message=f"Key file '{name}' updated",
            data={"key_files": result[0]["key_files"]}
        )

    def _project_update(self, args: Dict[str, Any]) -> SkillResponse:
        """Update project metadata."""
        db = self._get_db()
        project_id = args["project_id"]

        updates = []
        values = []

        for field in ["display_name", "description", "python_version", "venv_path"]:
            if field in args:
                updates.append(f"{field} = %s")
                values.append(args[field])

        if not updates:
            return SkillResponse(success=False, message="Nothing to update", error="No fields to update")

        updates.append("updated_at = NOW()")
        values.append(project_id)

        result = db.execute(f"""
            UPDATE project.projects
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, display_name
        """, values)

        if not result:
            return SkillResponse(success=False, message="Not found", error="Project not found")

        return SkillResponse(
            success=True,
            message="Project updated",
            data=result[0]
        )
