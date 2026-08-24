"""Dialogue/audio production service (MODULE-035, building on MODULE-034's
voice profiles and Module 07's `MediaProviderRouter`).

Chooses/assembles `native`/`tts_lipsync`/`hybrid` audio per shot (Module 03's
`Shot.audio_mode`, copied onto `ShotAudioProduction` at creation). For
`native` mode the dialogue audio is the video provider's own output track -
this service is not invoked. For `tts_lipsync`/`hybrid`, this service
generates a controlled TTS take from the character's `VoiceProfile` so exact
scripted dialogue and a persistent voice identity can be enforced
independently of whichever video provider generated the shot ("hybrid"
still means native ambience/effects plus this controlled dialogue layer -
mixing them together is Module 12/MODULE-046's deterministic editor, not
this service).
"""

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.audio_production import ShotAudioProduction
from xerama.domain.enums import AudioMode
from xerama.providers.voice import VoiceGenerationRequest, VoiceProvider
from xerama.repositories.interfaces import AudioProductionRepository, VoiceProfileRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_router import MediaProviderRouter


class AudioProductionService:
    def __init__(
        self,
        production_repo: AudioProductionRepository,
        voice_profile_repo: VoiceProfileRepository,
        asset_service: AssetService,
    ) -> None:
        self._production_repo = production_repo
        self._voice_profile_repo = voice_profile_repo
        self._asset_service = asset_service

    async def get_or_create_production(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        audio_mode: AudioMode = AudioMode.NATIVE,
    ) -> ShotAudioProduction:
        return await self._production_repo.get_or_create(
            episode_id, scene_number, shot_number, audio_mode
        )

    async def get(self, production_id: str) -> ShotAudioProduction:
        production = await self._production_repo.get(production_id)
        if production is None:
            raise ValueError(f"audio production {production_id} not found")
        return production

    async def list_by_episode(self, episode_id: str) -> list[ShotAudioProduction]:
        return await self._production_repo.list_by_episode(episode_id)

    async def generate_dialogue_take(
        self,
        production_id: str,
        project_id: str,
        character_id: str,
        text: str,
        voice_router: MediaProviderRouter[VoiceProvider],
        series_id: str | None = None,
    ) -> Asset:
        """Align scripted dialogue to this shot: `text` should be the
        shot's exact scripted line (`Shot.dialogue`), so the take is
        reproducible from canon, not improvised per attempt."""
        production = await self.get(production_id)
        profile = await self._voice_profile_repo.get_or_create(character_id)

        def is_compatible(provider: VoiceProvider) -> bool:
            capabilities = provider.capabilities
            if profile.language not in capabilities.languages:
                return False
            return len(text) <= capabilities.max_characters

        async def call(provider: VoiceProvider) -> bytes:
            return await provider.synthesize(
                VoiceGenerationRequest(
                    text=text, voice_id=profile.provider_voice_id, language=profile.language
                )
            )

        provider, data, attempts = await voice_router.generate(is_compatible, call)

        take_number = await self._next_take_number(project_id, production)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.AUDIO,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=production.episode_id,
                scene_number=production.scene_number,
                shot_number=production.shot_number,
                character_id=character_id,
            ),
            provenance=AssetProvenance(
                provider=provider.name,
                model=profile.provider_voice_id,
                generation_params={
                    "character_id": character_id,
                    "language": profile.language,
                    "audio_mode": production.audio_mode.value,
                    "routing_attempts": [a.model_dump() for a in attempts],
                },
            ),
            mime_type="audio/mpeg",
            ext=".mp3",
            take_number=take_number,
        )

    async def upload_dialogue_take(
        self,
        production_id: str,
        project_id: str,
        data: bytes,
        mime_type: str = "",
        ext: str = "",
        duration_seconds: float | None = None,
        series_id: str | None = None,
    ) -> Asset:
        """Manual upload fallback - first-class, same principle as every
        other media-ingest path in this codebase."""
        production = await self.get(production_id)
        take_number = await self._next_take_number(project_id, production)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.AUDIO,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=production.episode_id,
                scene_number=production.scene_number,
                shot_number=production.shot_number,
            ),
            provenance=AssetProvenance(provider="manual_upload"),
            mime_type=mime_type,
            ext=ext,
            duration_seconds=duration_seconds,
            take_number=take_number,
        )

    async def accept_take(self, production_id: str, asset_id: str) -> ShotAudioProduction:
        await self._asset_service.accept(asset_id)
        return await self._production_repo.approve(production_id, asset_id)

    async def reject_take(self, asset_id: str, reason: str) -> Asset:
        """Production stays `draft` - the next generate/upload call is the
        retry. Never overwrites/deletes the rejected take (ADR-019)."""
        return await self._asset_service.reject(asset_id, reason)

    async def list_takes(self, project_id: str, production: ShotAudioProduction) -> list[Asset]:
        return await self._asset_service.list_by_ownership(
            project_id,
            episode_id=production.episode_id,
            scene_number=production.scene_number,
            shot_number=production.shot_number,
            asset_type=AssetType.AUDIO,
        )

    async def _next_take_number(self, project_id: str, production: ShotAudioProduction) -> int:
        existing = await self.list_takes(project_id, production)
        return max((a.take_number for a in existing), default=0) + 1
