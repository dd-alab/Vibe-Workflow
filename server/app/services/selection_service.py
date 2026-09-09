from uuid import UUID

from app.domain.models import AssetClassification, Character
from app.repositories.asset_repository import AssetRepository


class SelectionService:
    def __init__(self, assets: AssetRepository) -> None:
        self.assets = assets

    def classify_asset(
        self,
        project_id: UUID,
        character_id: UUID,
        asset_id: UUID,
        *,
        expected_revision: int,
        classification: AssetClassification,
    ) -> Character:
        return self.assets.update_classification(
            project_id,
            character_id,
            asset_id,
            expected_revision=expected_revision,
            classification=classification,
        )

    def select_asset(
        self,
        project_id: UUID,
        character_id: UUID,
        asset_id: UUID | None,
        *,
        expected_revision: int,
    ) -> Character:
        return self.assets.select_asset(
            project_id,
            character_id,
            asset_id,
            expected_revision=expected_revision,
        )
