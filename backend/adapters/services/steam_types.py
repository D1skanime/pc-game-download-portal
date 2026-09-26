from typing import NotRequired, TypedDict


class SteamPlatforms(TypedDict):
    windows: bool
    mac: bool
    linux: bool


class SteamStoreSearchItem(TypedDict):
    type: str
    name: str
    id: int
    platforms: NotRequired[SteamPlatforms]


class SteamFullGame(TypedDict):
    appid: int | str
    name: NotRequired[str]


class SteamAppDetails(TypedDict):
    type: str
    name: str
    steam_appid: int
    short_description: NotRequired[str]
    header_image: NotRequired[str]
    developers: NotRequired[list[str]]
    publishers: NotRequired[list[str]]
    platforms: NotRequired[SteamPlatforms]
    screenshots: NotRequired[list[dict[str, str | int]]]
    release_date: NotRequired[dict[str, str | bool]]
    fullgame: NotRequired[SteamFullGame]
