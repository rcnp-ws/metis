from pydantic import BaseModel, ConfigDict, Field


class RegisterNameRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1)


class GreetingValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None
    counts: dict[str, int]