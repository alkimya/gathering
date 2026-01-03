"""Social media platforms skill for reading and posting content."""

from dataclasses import dataclass
from typing import Any

import httpx

from gathering.skills.base import BaseSkill


@dataclass
class SocialConfig:
    """Configuration for social media integrations."""

    # Twitter/X API credentials
    twitter_bearer_token: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""

    # Reddit credentials
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "GatheRing-Agent/1.0"

    # GitHub credentials
    github_token: str = ""

    # Discord webhook URL
    discord_webhook_url: str = ""

    # Slack webhook URL
    slack_webhook_url: str = ""

    # Mastodon instance and token
    mastodon_instance: str = ""
    mastodon_token: str = ""

    # Request timeout
    timeout: float = 30.0


class SocialMediaSkill(BaseSkill):
    """Skill for interacting with social media platforms."""

    name = "social"
    description = "Interact with social media platforms (Twitter, Reddit, GitHub, Discord, Slack, Mastodon)"
    version = "1.0.0"

    def __init__(self, config: SocialConfig | dict | None = None):
        super().__init__(config if isinstance(config, dict) else None)
        self.social_config = config if isinstance(config, SocialConfig) else SocialConfig()

    def get_tools_definition(self) -> list[dict[str, Any]]:
        return [
            # Twitter/X Tools
            {
                "name": "twitter_search",
                "description": "Search for tweets on Twitter/X (requires API credentials)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (10-100)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "twitter_user_timeline",
                "description": "Get tweets from a Twitter user's timeline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Twitter username (without @)"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tweets",
                            "default": 10
                        }
                    },
                    "required": ["username"]
                }
            },

            # Reddit Tools
            {
                "name": "reddit_search",
                "description": "Search Reddit posts and comments",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "subreddit": {
                            "type": "string",
                            "description": "Optional: limit to specific subreddit"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["relevance", "hot", "top", "new", "comments"],
                            "default": "relevance"
                        },
                        "time": {
                            "type": "string",
                            "enum": ["hour", "day", "week", "month", "year", "all"],
                            "default": "all"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "reddit_subreddit",
                "description": "Get posts from a subreddit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subreddit": {
                            "type": "string",
                            "description": "Subreddit name (without r/)"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["hot", "new", "top", "rising"],
                            "default": "hot"
                        },
                        "time": {
                            "type": "string",
                            "enum": ["hour", "day", "week", "month", "year", "all"],
                            "default": "day"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    },
                    "required": ["subreddit"]
                }
            },
            {
                "name": "reddit_post",
                "description": "Get a Reddit post with its comments",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Reddit post URL"
                        },
                        "comment_limit": {
                            "type": "integer",
                            "description": "Number of top comments to retrieve",
                            "default": 10
                        }
                    },
                    "required": ["url"]
                }
            },

            # GitHub Tools
            {
                "name": "github_search_repos",
                "description": "Search GitHub repositories",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "language": {
                            "type": "string",
                            "description": "Filter by programming language"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["stars", "forks", "updated", "help-wanted-issues"],
                            "default": "stars"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "github_repo_info",
                "description": "Get information about a GitHub repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "github_issues",
                "description": "List issues from a GitHub repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "default": "open"
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of labels"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "github_trending",
                "description": "Get trending GitHub repositories",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "description": "Filter by programming language"
                        },
                        "since": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "default": "daily"
                        }
                    }
                }
            },

            # Discord Tools
            {
                "name": "discord_send",
                "description": "Send a message to a Discord channel via webhook",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "username": {
                            "type": "string",
                            "description": "Override webhook username"
                        },
                        "embed": {
                            "type": "object",
                            "description": "Discord embed object",
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
                                }
                            }
                        }
                    },
                    "required": ["content"]
                }
            },

            # Slack Tools
            {
                "name": "slack_send",
                "description": "Send a message to a Slack channel via webhook",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Slack Block Kit blocks for rich formatting"
                        },
                        "attachments": {
                            "type": "array",
                            "description": "Legacy attachments"
                        }
                    },
                    "required": ["text"]
                }
            },

            # Mastodon Tools
            {
                "name": "mastodon_search",
                "description": "Search Mastodon for posts, accounts, or hashtags",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["accounts", "hashtags", "statuses"],
                            "default": "statuses"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "mastodon_timeline",
                "description": "Get Mastodon public timeline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "timeline": {
                            "type": "string",
                            "enum": ["public", "local", "tag"],
                            "default": "public"
                        },
                        "tag": {
                            "type": "string",
                            "description": "Hashtag (required if timeline is 'tag')"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 20
                        }
                    }
                }
            },
            {
                "name": "mastodon_post",
                "description": "Post a status to Mastodon (requires token)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Status text (max 500 chars)"
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["public", "unlisted", "private", "direct"],
                            "default": "public"
                        },
                        "sensitive": {
                            "type": "boolean",
                            "description": "Mark as sensitive content",
                            "default": False
                        },
                        "spoiler_text": {
                            "type": "string",
                            "description": "Content warning text"
                        }
                    },
                    "required": ["status"]
                }
            },

            # Hacker News
            {
                "name": "hackernews_top",
                "description": "Get top stories from Hacker News",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["top", "new", "best", "ask", "show", "job"],
                            "default": "top"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "hackernews_item",
                "description": "Get a Hacker News story with comments",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "integer",
                            "description": "Story ID"
                        },
                        "comment_limit": {
                            "type": "integer",
                            "description": "Number of comments to retrieve",
                            "default": 10
                        }
                    },
                    "required": ["item_id"]
                }
            }
        ]

    def _request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        json_data: dict | None = None
    ) -> dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            with httpx.Client(timeout=self.social_config.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data
                )
                response.raise_for_status()

                if response.headers.get("content-type", "").startswith("application/json"):
                    return {"success": True, "data": response.json()}
                return {"success": True, "text": response.text}

        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Twitter implementations
    def _twitter_search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        if not self.social_config.twitter_bearer_token:
            return {"success": False, "error": "Twitter API credentials not configured"}

        headers = {"Authorization": f"Bearer {self.social_config.twitter_bearer_token}"}
        params = {
            "query": query,
            "max_results": min(max(10, max_results), 100),
            "tweet.fields": "created_at,author_id,public_metrics,source"
        }

        return self._request(
            "GET",
            "https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params=params
        )

    # Reddit implementations
    def _reddit_search(
        self,
        query: str,
        subreddit: str = "",
        sort: str = "relevance",
        time: str = "all",
        limit: int = 10
    ) -> dict[str, Any]:
        headers = {"User-Agent": self.social_config.reddit_user_agent}

        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {"q": query, "restrict_sr": "on", "sort": sort, "t": time, "limit": limit}
        else:
            url = "https://www.reddit.com/search.json"
            params = {"q": query, "sort": sort, "t": time, "limit": limit}

        result = self._request("GET", url, headers=headers, params=params)

        if result.get("success") and "data" in result:
            posts = []
            for child in result["data"].get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append({
                    "title": post.get("title"),
                    "subreddit": post.get("subreddit"),
                    "author": post.get("author"),
                    "score": post.get("score"),
                    "url": post.get("url"),
                    "permalink": f"https://reddit.com{post.get('permalink')}",
                    "num_comments": post.get("num_comments"),
                    "created_utc": post.get("created_utc")
                })
            return {"success": True, "posts": posts}

        return result

    def _reddit_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        time: str = "day",
        limit: int = 10
    ) -> dict[str, Any]:
        headers = {"User-Agent": self.social_config.reddit_user_agent}
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {"t": time, "limit": limit}

        result = self._request("GET", url, headers=headers, params=params)

        if result.get("success") and "data" in result:
            posts = []
            for child in result["data"].get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append({
                    "title": post.get("title"),
                    "author": post.get("author"),
                    "score": post.get("score"),
                    "url": post.get("url"),
                    "permalink": f"https://reddit.com{post.get('permalink')}",
                    "num_comments": post.get("num_comments"),
                    "selftext": post.get("selftext", "")[:500]
                })
            return {"success": True, "subreddit": subreddit, "posts": posts}

        return result

    # GitHub implementations
    def _github_search_repos(
        self,
        query: str,
        language: str = "",
        sort: str = "stars",
        limit: int = 10
    ) -> dict[str, Any]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.social_config.github_token:
            headers["Authorization"] = f"token {self.social_config.github_token}"

        q = query
        if language:
            q += f" language:{language}"

        params = {"q": q, "sort": sort, "per_page": limit}

        result = self._request(
            "GET",
            "https://api.github.com/search/repositories",
            headers=headers,
            params=params
        )

        if result.get("success") and "data" in result:
            repos = []
            for item in result["data"].get("items", []):
                repos.append({
                    "name": item.get("full_name"),
                    "description": item.get("description"),
                    "url": item.get("html_url"),
                    "stars": item.get("stargazers_count"),
                    "forks": item.get("forks_count"),
                    "language": item.get("language"),
                    "topics": item.get("topics", [])[:5],
                    "updated_at": item.get("updated_at")
                })
            return {"success": True, "repositories": repos}

        return result

    def _github_repo_info(self, owner: str, repo: str) -> dict[str, Any]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.social_config.github_token:
            headers["Authorization"] = f"token {self.social_config.github_token}"

        result = self._request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers
        )

        if result.get("success") and "data" in result:
            r = result["data"]
            return {
                "success": True,
                "repo": {
                    "name": r.get("full_name"),
                    "description": r.get("description"),
                    "url": r.get("html_url"),
                    "homepage": r.get("homepage"),
                    "stars": r.get("stargazers_count"),
                    "forks": r.get("forks_count"),
                    "watchers": r.get("watchers_count"),
                    "open_issues": r.get("open_issues_count"),
                    "language": r.get("language"),
                    "license": r.get("license", {}).get("name") if r.get("license") else None,
                    "topics": r.get("topics", []),
                    "created_at": r.get("created_at"),
                    "updated_at": r.get("updated_at"),
                    "default_branch": r.get("default_branch")
                }
            }

        return result

    def _github_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = "",
        limit: int = 10
    ) -> dict[str, Any]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.social_config.github_token:
            headers["Authorization"] = f"token {self.social_config.github_token}"

        params = {"state": state, "per_page": limit}
        if labels:
            params["labels"] = labels

        result = self._request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers=headers,
            params=params
        )

        if result.get("success") and "data" in result:
            issues = []
            for item in result["data"]:
                if "pull_request" not in item:  # Exclude PRs
                    issues.append({
                        "number": item.get("number"),
                        "title": item.get("title"),
                        "state": item.get("state"),
                        "url": item.get("html_url"),
                        "author": item.get("user", {}).get("login"),
                        "labels": [lbl.get("name") for lbl in item.get("labels", [])],
                        "comments": item.get("comments"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at")
                    })
            return {"success": True, "issues": issues}

        return result

    # Discord implementation
    def _discord_send(
        self,
        content: str,
        username: str = "",
        embed: dict | None = None
    ) -> dict[str, Any]:
        if not self.social_config.discord_webhook_url:
            return {"success": False, "error": "Discord webhook URL not configured"}

        payload = {"content": content}
        if username:
            payload["username"] = username
        if embed:
            payload["embeds"] = [embed]

        return self._request(
            "POST",
            self.social_config.discord_webhook_url,
            json_data=payload
        )

    # Slack implementation
    def _slack_send(
        self,
        text: str,
        blocks: list | None = None,
        attachments: list | None = None
    ) -> dict[str, Any]:
        if not self.social_config.slack_webhook_url:
            return {"success": False, "error": "Slack webhook URL not configured"}

        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments

        return self._request(
            "POST",
            self.social_config.slack_webhook_url,
            json_data=payload
        )

    # Mastodon implementations
    def _mastodon_search(
        self,
        query: str,
        search_type: str = "statuses",
        limit: int = 10
    ) -> dict[str, Any]:
        if not self.social_config.mastodon_instance:
            return {"success": False, "error": "Mastodon instance not configured"}

        instance = self.social_config.mastodon_instance.rstrip("/")
        headers = {}
        if self.social_config.mastodon_token:
            headers["Authorization"] = f"Bearer {self.social_config.mastodon_token}"

        params = {"q": query, "type": search_type, "limit": limit}

        return self._request(
            "GET",
            f"{instance}/api/v2/search",
            headers=headers,
            params=params
        )

    def _mastodon_timeline(
        self,
        timeline: str = "public",
        tag: str = "",
        limit: int = 20
    ) -> dict[str, Any]:
        if not self.social_config.mastodon_instance:
            return {"success": False, "error": "Mastodon instance not configured"}

        instance = self.social_config.mastodon_instance.rstrip("/")
        headers = {}
        if self.social_config.mastodon_token:
            headers["Authorization"] = f"Bearer {self.social_config.mastodon_token}"

        if timeline == "tag":
            if not tag:
                return {"success": False, "error": "Tag required for tag timeline"}
            url = f"{instance}/api/v1/timelines/tag/{tag}"
        else:
            url = f"{instance}/api/v1/timelines/{timeline}"

        params = {"limit": limit}

        result = self._request("GET", url, headers=headers, params=params)

        if result.get("success") and "data" in result:
            statuses = []
            for s in result["data"]:
                statuses.append({
                    "id": s.get("id"),
                    "content": s.get("content"),
                    "author": s.get("account", {}).get("acct"),
                    "created_at": s.get("created_at"),
                    "reblogs": s.get("reblogs_count"),
                    "favourites": s.get("favourites_count"),
                    "url": s.get("url")
                })
            return {"success": True, "statuses": statuses}

        return result

    def _mastodon_post(
        self,
        status: str,
        visibility: str = "public",
        sensitive: bool = False,
        spoiler_text: str = ""
    ) -> dict[str, Any]:
        if not self.social_config.mastodon_instance or not self.social_config.mastodon_token:
            return {"success": False, "error": "Mastodon credentials not configured"}

        instance = self.social_config.mastodon_instance.rstrip("/")
        headers = {"Authorization": f"Bearer {self.social_config.mastodon_token}"}

        payload = {
            "status": status[:500],  # Mastodon limit
            "visibility": visibility,
            "sensitive": sensitive
        }
        if spoiler_text:
            payload["spoiler_text"] = spoiler_text

        return self._request(
            "POST",
            f"{instance}/api/v1/statuses",
            headers=headers,
            json_data=payload
        )

    # Hacker News implementations
    def _hackernews_top(self, type_: str = "top", limit: int = 10) -> dict[str, Any]:
        type_map = {
            "top": "topstories",
            "new": "newstories",
            "best": "beststories",
            "ask": "askstories",
            "show": "showstories",
            "job": "jobstories"
        }

        endpoint = type_map.get(type_, "topstories")
        result = self._request(
            "GET",
            f"https://hacker-news.firebaseio.com/v0/{endpoint}.json"
        )

        if not result.get("success"):
            return result

        story_ids = result.get("data", [])[:limit]
        stories = []

        for story_id in story_ids:
            story_result = self._request(
                "GET",
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            )
            if story_result.get("success") and story_result.get("data"):
                s = story_result["data"]
                stories.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "url": s.get("url"),
                    "score": s.get("score"),
                    "author": s.get("by"),
                    "comments": s.get("descendants", 0),
                    "time": s.get("time"),
                    "hn_url": f"https://news.ycombinator.com/item?id={s.get('id')}"
                })

        return {"success": True, "stories": stories}

    def _hackernews_item(self, item_id: int, comment_limit: int = 10) -> dict[str, Any]:
        result = self._request(
            "GET",
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        )

        if not result.get("success") or not result.get("data"):
            return result

        item = result["data"]
        story = {
            "id": item.get("id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "text": item.get("text"),
            "score": item.get("score"),
            "author": item.get("by"),
            "time": item.get("time"),
            "comments": []
        }

        # Fetch top comments
        kids = item.get("kids", [])[:comment_limit]
        for kid_id in kids:
            comment_result = self._request(
                "GET",
                f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json"
            )
            if comment_result.get("success") and comment_result.get("data"):
                c = comment_result["data"]
                if c.get("type") == "comment" and not c.get("deleted"):
                    story["comments"].append({
                        "id": c.get("id"),
                        "author": c.get("by"),
                        "text": c.get("text"),
                        "time": c.get("time")
                    })

        return {"success": True, "story": story}

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a social media tool."""

        # Twitter
        if tool_name == "twitter_search":
            return self._twitter_search(
                tool_input["query"],
                tool_input.get("max_results", 10)
            )

        elif tool_name == "twitter_user_timeline":
            if not self.social_config.twitter_bearer_token:
                return {"success": False, "error": "Twitter API credentials not configured"}
            # Would need user lookup first, simplified here
            return {"success": False, "error": "User timeline requires user ID lookup"}

        # Reddit
        elif tool_name == "reddit_search":
            return self._reddit_search(
                tool_input["query"],
                tool_input.get("subreddit", ""),
                tool_input.get("sort", "relevance"),
                tool_input.get("time", "all"),
                tool_input.get("limit", 10)
            )

        elif tool_name == "reddit_subreddit":
            return self._reddit_subreddit(
                tool_input["subreddit"],
                tool_input.get("sort", "hot"),
                tool_input.get("time", "day"),
                tool_input.get("limit", 10)
            )

        elif tool_name == "reddit_post":
            # Parse URL and fetch
            url = tool_input["url"]
            if not url.endswith(".json"):
                url = url.rstrip("/") + ".json"

            headers = {"User-Agent": self.social_config.reddit_user_agent}
            return self._request("GET", url, headers=headers)

        # GitHub
        elif tool_name == "github_search_repos":
            return self._github_search_repos(
                tool_input["query"],
                tool_input.get("language", ""),
                tool_input.get("sort", "stars"),
                tool_input.get("limit", 10)
            )

        elif tool_name == "github_repo_info":
            return self._github_repo_info(
                tool_input["owner"],
                tool_input["repo"]
            )

        elif tool_name == "github_issues":
            return self._github_issues(
                tool_input["owner"],
                tool_input["repo"],
                tool_input.get("state", "open"),
                tool_input.get("labels", ""),
                tool_input.get("limit", 10)
            )

        elif tool_name == "github_trending":
            # Use GitHub search with date filter for trending
            from datetime import datetime, timedelta

            since = tool_input.get("since", "daily")
            days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 1)
            date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            query = f"created:>{date}"
            if tool_input.get("language"):
                query += f" language:{tool_input['language']}"

            return self._github_search_repos(query, sort="stars", limit=10)

        # Discord
        elif tool_name == "discord_send":
            return self._discord_send(
                tool_input["content"],
                tool_input.get("username", ""),
                tool_input.get("embed")
            )

        # Slack
        elif tool_name == "slack_send":
            return self._slack_send(
                tool_input["text"],
                tool_input.get("blocks"),
                tool_input.get("attachments")
            )

        # Mastodon
        elif tool_name == "mastodon_search":
            return self._mastodon_search(
                tool_input["query"],
                tool_input.get("type", "statuses"),
                tool_input.get("limit", 10)
            )

        elif tool_name == "mastodon_timeline":
            return self._mastodon_timeline(
                tool_input.get("timeline", "public"),
                tool_input.get("tag", ""),
                tool_input.get("limit", 20)
            )

        elif tool_name == "mastodon_post":
            return self._mastodon_post(
                tool_input["status"],
                tool_input.get("visibility", "public"),
                tool_input.get("sensitive", False),
                tool_input.get("spoiler_text", "")
            )

        # Hacker News
        elif tool_name == "hackernews_top":
            return self._hackernews_top(
                tool_input.get("type", "top"),
                tool_input.get("limit", 10)
            )

        elif tool_name == "hackernews_item":
            return self._hackernews_item(
                tool_input["item_id"],
                tool_input.get("comment_limit", 10)
            )

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
