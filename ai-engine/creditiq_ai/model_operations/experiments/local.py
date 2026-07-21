"""Durable local experiment tracking adapter."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from creditiq_ai.exceptions import ModelRegistryError


class ExperimentRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: str = "running"
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


class LocalExperimentTracker:
    """Atomic JSON experiment tracker; replaceable by an MLflow adapter."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()

    def start(
        self,
        name: str,
        *,
        parameters: dict[str, str | int | float | bool] | None = None,
        tags: dict[str, str] | None = None,
    ) -> ExperimentRun:
        run = ExperimentRun(name=name, parameters=parameters or {}, tags=tags or {})
        with self._lock:
            state = self._read()
            state.append(run.model_dump(mode="json"))
            self._write(state)
        return run

    def finish(
        self, run_id: str, *, metrics: dict[str, float], status: str = "completed"
    ) -> ExperimentRun:
        with self._lock:
            state = self._read()
            for index, raw in enumerate(state):
                run = ExperimentRun.model_validate(raw)
                if run.run_id == run_id:
                    updated = run.model_copy(
                        update={
                            "status": status,
                            "metrics": metrics,
                            "ended_at": datetime.now(timezone.utc),
                        }
                    )
                    state[index] = updated.model_dump(mode="json")
                    self._write(state)
                    return updated
        raise ModelRegistryError("Experiment run was not found", context={"run_id": run_id})

    def list_runs(self) -> list[ExperimentRun]:
        with self._lock:
            return [ExperimentRun.model_validate(raw) for raw in self._read()]

    def _read(self) -> list[dict[str, object]]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("experiment state is not a list")
            return raw
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ModelRegistryError("Experiment storage is invalid") from exc

    def _write(self, state: list[dict[str, object]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self._path)
