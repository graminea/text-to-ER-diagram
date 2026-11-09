from collections import Counter

from app.er.models import ConceptualSchema, Issue, ValidationReport


def validate_schema(schema: ConceptualSchema) -> ValidationReport:
    """Check structural integrity; validity does not prove requirements coverage."""
    issues: list[Issue] = []

    def duplicate_names(names: list[str], path: str) -> None:
        for name, count in Counter(n.casefold() for n in names).items():
            if count > 1:
                issues.append(
                    Issue(code="duplicate_name", path=path, message=f"Duplicate name: {name}")
                )

    duplicate_names([e.name for e in schema.entities], "entities")
    duplicate_names([r.name for r in schema.relationships], "relationships")
    # References are exact; case-insensitive uniqueness prevents ambiguous names.
    entities = {e.name for e in schema.entities}
    for i, entity in enumerate(schema.entities):
        path = f"entities.{i}"
        duplicate_names([a.name for a in entity.attributes], f"{path}.attributes")
        if not any(a.is_identifier for a in entity.attributes):
            issues.append(
                Issue(
                    code="missing_identifier",
                    path=path,
                    message=f"{entity.name} needs an identifier.",
                )
            )
    for i, relationship in enumerate(schema.relationships):
        path = f"relationships.{i}.participants"
        duplicate_names([p.role for p in relationship.participants], path)
        for j, participant in enumerate(relationship.participants):
            if participant.entity not in entities:
                issues.append(
                    Issue(
                        code="unknown_entity",
                        path=f"{path}.{j}.entity",
                        message=f"Unknown entity: {participant.entity}",
                    )
                )
    for i, ambiguity in enumerate(schema.ambiguities):
        issues.append(
            Issue(
                code="unresolved_ambiguity",
                path=f"ambiguities.{i}",
                message=ambiguity,
                severity="warning",
            )
        )
    return ValidationReport(valid=not any(i.severity == "error" for i in issues), issues=issues)
