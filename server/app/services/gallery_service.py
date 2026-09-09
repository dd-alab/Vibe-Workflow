from dataclasses import dataclass
from uuid import UUID

from app.domain.models import Asset
from app.repositories.asset_repository import AssetRepository
from app.repositories.character_repository import CharacterRepository


@dataclass(frozen=True)
class GalleryItem:
    character_id: UUID
    character_name: str
    character_slug: str
    selected_asset: Asset | None


class GalleryService:
    def __init__(
        self,
        characters: CharacterRepository,
        assets: AssetRepository,
    ) -> None:
        self.characters = characters
        self.assets = assets

    def list_gallery(self, project_id: UUID) -> list[GalleryItem]:
        items: list[GalleryItem] = []
        for character in self.characters.list_for_project(project_id):
            selected = None
            if character.selected_asset_id is not None:
                selected = next(
                    (
                        asset
                        for asset in character.assets
                        if asset.id == character.selected_asset_id
                    ),
                    None,
                )
            items.append(
                GalleryItem(
                    character_id=character.id,
                    character_name=character.name,
                    character_slug=character.slug,
                    selected_asset=selected,
                )
            )
        return items
