"""Bounded receipt preparation for one accepted atomic provider inventory."""

from handler.filesystem.scan_media_publication import ScanMediaBatch


class ScanMediaInventory(ScanMediaBatch):
    def __init__(self, rom_id, platform_id, storage, *, output_limit):
        if type(output_limit) is not int or output_limit < 0:
            raise ValueError("scan_media_inventory_limit")
        super().__init__(rom_id, platform_id, storage)
        self.output_limit = output_limit
        self.prepared_count = 0
        self.batches: list[ScanMediaBatch] = [self]

    def prepare(self, original_path):
        if self._closed or self.prepared_count >= self.output_limit:
            raise ValueError("scan_media_inventory_closed_or_full")
        unit = self.batches[-1]
        if not unit.can_prepare(original_path):
            unit = ScanMediaBatch(self.rom_id, self.platform_id, self.storage)
            self.batches.append(unit)
        output = ScanMediaBatch.prepare(unit, original_path)
        self.prepared_count += 1
        return output

    def finish(self, output):
        for unit in self.batches:
            if output in unit.outputs:
                return ScanMediaBatch.finish(unit, output)
        raise ValueError("scan_media_output_invalid")

    def _publication_units(self):
        return self.batches

    def abort(self):
        for unit in self.batches:
            ScanMediaBatch.abort(unit)
