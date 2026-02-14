"""Welcome generator — creates randomised welcome messages that aren't shit"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


class WelcomeGenerator:
    """
    Generates randomised welcome messages from templates.

    Supports variable substitution and weighted template groups.
    """

    def __init__(self):
        self.templates: list[str] = []
        self._load_templates()

    def _load_templates(self) -> None:
        """Load welcome templates from data/welcome_templates.json"""
        templates_path = Path("data/welcome_templates.json")

        if not templates_path.exists():
            logger.warning("data/welcome_templates.json not found — using fallback templates")
            self.templates = [
                "Welcome to {server_name}, {name}!",
                "Hey {name}, welcome to the neighborhood!",
                "Everyone say hi to {name}!",
            ]
            return

        try:
            with templates_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Flatten weighted groups into a single list (duplicate based on weight)
            all_templates = []
            for group in data.get("groups", []):
                weight = group.get("weight", 1)
                sentences = group.get("sentences", [])
                # Add each sentence `weight` times to increase probability
                all_templates.extend(sentences * weight)

            if all_templates:
                self.templates = all_templates
                logger.info(
                    "Loaded %d welcome templates from %d groups",
                    len(all_templates),
                    len(data.get("groups", [])),
                )
            else:
                logger.warning("No templates found in welcome_templates.json")
                self.templates = ["Welcome to {server_name}, {name}!"]

        except Exception:
            logger.exception("Failed to load welcome templates")
            self.templates = ["Welcome to {server_name}, {name}!"]

    def generate_welcome(
        self,
        name: str,
        server_name: str = "The Gayborhood",
        pronouns: str | None = None,
        location: str | None = None,
    ) -> str:
        """
        Generate a random welcome message.

        Args:
            name: Member's preferred name
            server_name: Server name for {server_name} variable
            pronouns: Member's pronouns (optional, for future templates)
            location: Member's location (optional, for future templates)

        Returns:
            Welcome message string
        """
        if not self.templates:
            return f"Welcome to {server_name}, {name}!"

        template = random.choice(self.templates)

        # Substitute variables
        message = template.format(
            name=name,
            server_name=server_name,
            pronouns=pronouns or "they/them",
            location=location or "parts unknown",
        )

        return message
