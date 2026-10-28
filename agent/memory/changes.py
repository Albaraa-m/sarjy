from pydantic import BaseModel, ConfigDict


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str


class MemoryChanges(BaseModel):
    """Edits to a user's facts. Removals apply before sets, so a key in both ends up set."""

    model_config = ConfigDict(extra="forbid")

    set: list[Fact]
    remove: list[str]

    @classmethod
    def none(cls) -> MemoryChanges:
        return cls(set=[], remove=[])

    def __bool__(self) -> bool:
        return bool(self.set or self.remove)

    def apply_to(self, facts: dict[str, str]) -> None:
        for key in self.remove:
            facts.pop(key, None)
        facts.update((fact.key, fact.value) for fact in self.set)
