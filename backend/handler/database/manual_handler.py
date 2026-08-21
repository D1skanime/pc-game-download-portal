from sqlalchemy import select
from sqlalchemy.orm import Session

from decorators.database import begin_session
from handler.database.base_handler import DBBaseHandler
from models.rom import Rom


class DBPrimaryManualHandler(DBBaseHandler):
    @begin_session
    def compare_and_swap_path(
        self,
        rom_id: int,
        *,
        expected_path: str,
        new_path: str,
        session: Session = None,  # type: ignore
    ) -> bool:
        rom = session.scalar(
            select(Rom).where(Rom.id == rom_id).with_for_update(of=Rom)
        )
        if rom is None or (rom.path_manual or "") != expected_path:
            return False
        rom.path_manual = new_path
        session.flush()
        return True
