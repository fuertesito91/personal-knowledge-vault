"""Markdown templates for vault documents."""

from typing import Any


def render_frontmatter(data: dict[str, Any]) -> str:
    """Render YAML frontmatter block."""
    import yaml
    fm = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm}---\n"


def render_document(title: str, content: str, frontmatter: dict[str, Any], entities: list[str] | None = None) -> str:
    """Render a full vault document."""
    parts = [render_frontmatter(frontmatter)]
    parts.append(f"# {title}\n")
    parts.append(content)

    if entities:
        parts.append("\n\n## Related Entities\n")
        for entity in entities:
            parts.append(f"- [[{entity}]]")

    return "\n".join(parts)


def render_entity_page(entity_name: str, entity_type: str, properties: dict[str, Any], icon: str = "📄") -> str:
    """Render an entity page."""
    fm = {
        "title": entity_name,
        "type": entity_type,
        "tags": [entity_type.lower()],
    }
    fm.update(properties)

    parts = [render_frontmatter(fm)]
    parts.append(f"# {icon} {entity_name}\n")
    parts.append(f"**Type:** {entity_type}\n")

    for key, value in properties.items():
        if value:
            if isinstance(value, list):
                parts.append(f"## {key.replace('_', ' ').title()}")
                for item in value:
                    parts.append(f"- [[{item}]]" if isinstance(item, str) else f"- {item}")
            else:
                parts.append(f"**{key.replace('_', ' ').title()}:** {value}")

    return "\n".join(parts)
