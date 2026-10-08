---
name: 261009-steam-legacy-match-search
status: complete
commit: 5a63d7ca5
---

Fixed the missing Steam provider in the legacy `/api/search/roms` matching path. Steam candidates now carry `steam_id` and `steam_url_cover`, and selecting one persists the App ID and hydrated Steam metadata through the existing ROM update endpoint. The frontend filter and cover selection now recognize Steam results.

Live verification on Dwarf Fortress confirmed App ID 975370, German Steam text, Steam cover, and 20 stored screenshots. Frontend typecheck passed. Focused backend pytest was attempted but blocked before assertions by the pre-existing unavailable test MariaDB at `127.0.0.1:3306`.
