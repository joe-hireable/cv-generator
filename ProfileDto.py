from dataclasses import dataclass

@dataclass
class Profile:
    schema: str
    template: str

def map_to_dto(data: dict) -> Profile:
    return Profile(
        schema=data["schema"],
        template=data["template"]
    )