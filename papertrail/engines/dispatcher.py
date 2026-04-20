"""Engine dispatcher — routes regions to appropriate extraction engines."""

from __future__ import annotations

from papertrail.models.extraction import Region, RegionExtractionResult


class EngineDispatcher:
    """Routes extraction requests to appropriate engines based on region type and config."""

    def __init__(self, engines: dict, default_config: dict):
        self._engines = engines
        self._default_config = default_config

    async def extract_region(
        self,
        region: Region,
        file_uri: str,
        file_mime: str,
        playbook_engines: dict,
    ) -> RegionExtractionResult:
        """Dispatch a region to the appropriate engine with fallback."""
        # TODO: Implement real dispatch logic per Section 9.2
        return RegionExtractionResult(
            region_id=region.id,
            text=f"Stub text for region {region.id}",
            confidence=0.85,
            engine_used="stub",
            fallback_used=False,
        )
