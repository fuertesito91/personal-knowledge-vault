# Ontology Guide

The ontology defines entity types and relationships in your knowledge vault. Edit `ontology.yaml` to customize.

## Entity Types

| Type | Folder | Properties |
|------|--------|------------|
| Person | entities/people | name, role, organization, notes |
| Project | entities/projects | name, status, description, stakeholders |
| Meeting | meetings | date, participants, summary, decisions, action_items |
| Conversation | conversations | date, platform, participants, summary, topics |
| Topic | entities/topics | name, description, related_topics |
| Decision | decisions | date, context, decision, rationale, stakeholders |
| Document | documents | title, date, source, summary |

## Relationships

Relationships are expressed as `[[wikilinks]]` in document content and typed in frontmatter. The enrichment pipeline discovers new relationships automatically.

## Customizing

Add new entity types by editing `ontology.yaml`:

```yaml
entities:
  MyCustomType:
    properties: [name, description, custom_field]
    folder: my-custom-folder
    icon: 🔮
```
