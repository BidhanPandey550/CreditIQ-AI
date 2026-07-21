"""Validated model lineage traversal over registry records."""

from __future__ import annotations

from creditiq_ai.exceptions import LineageError
from creditiq_ai.model_operations.domain import ModelIdentity, ModelVersion


class LineageGraph:
    """Resolve ancestry and descendants without coupling to registry storage."""

    def __init__(self, versions: list[ModelVersion]) -> None:
        self._versions = {item.version: item for item in versions}
        identities = {item.identity.key for item in versions}
        if len(identities) > 1:
            raise LineageError("Lineage graph requires one model identity")
        self._validate()

    @property
    def identity(self) -> ModelIdentity | None:
        return next(iter(self._versions.values())).identity if self._versions else None

    def ancestors(self, version: str) -> list[ModelVersion]:
        current = self._get(version)
        result: list[ModelVersion] = []
        visited = {version}
        while current.lineage.parent_version:
            parent = current.lineage.parent_version
            if parent in visited:
                raise LineageError("Circular model lineage detected", context={"version": parent})
            current = self._get(parent)
            result.append(current)
            visited.add(parent)
        return result

    def children(self, version: str) -> list[ModelVersion]:
        self._get(version)
        return sorted(
            [item for item in self._versions.values() if item.lineage.parent_version == version],
            key=lambda item: item.version,
        )

    def _validate(self) -> None:
        for version, item in self._versions.items():
            parent = item.lineage.parent_version
            if parent is not None and parent not in self._versions:
                raise LineageError(
                    "Model lineage references an unknown parent",
                    context={"version": version, "parent": parent},
                )
            self.ancestors(version)

    def _get(self, version: str) -> ModelVersion:
        try:
            return self._versions[version]
        except KeyError as exc:
            raise LineageError(
                "Lineage version was not found", context={"version": version}
            ) from exc
