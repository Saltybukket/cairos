from dataclasses import dataclass, field

@dataclass
class Plan:
    summary: str
    commands: list[str] = field(default_factory=list)
    risk: str = "low"
    notes: list[str] = field(default_factory=list)

    def joined(self) -> str:
        return " && ".join(self.commands)
