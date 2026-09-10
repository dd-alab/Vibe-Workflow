from dataclasses import dataclass
from uuid import UUID

from app.domain.models import (
    Character,
    PromptBlock,
    PromptBlockSnapshot,
    PromptVersion,
    TextBlock,
    utc_now,
)
from app.repositories.character_repository import CharacterRepository
from app.repositories.errors import ConflictError, NotFoundError

from .errors import ServiceValidationError


@dataclass(frozen=True)
class TextBlockChange:
    id: UUID | None
    text: str


@dataclass(frozen=True)
class PromptBlockChange:
    id: UUID | None
    name: str
    text: str


class CharacterService:
    def __init__(self, characters: CharacterRepository) -> None:
        self.characters = characters

    def list_characters(self, project_id: UUID) -> list[Character]:
        return self.characters.list_for_project(project_id)

    def create_character(
        self,
        project_id: UUID,
        name: str,
        slug: str | None = None,
    ) -> Character:
        try:
            return self.characters.create(project_id, name=name, slug=slug)
        except ValueError as error:
            raise ServiceValidationError(
                "Le nom ne permet pas de creer un dossier asset valide."
            ) from error

    def get_character(self, project_id: UUID, character_id: UUID) -> Character:
        return self.characters.get(project_id, character_id)

    def update_character(
        self,
        project_id: UUID,
        character_id: UUID,
        *,
        expected_revision: int,
        name: str | None = None,
        short_texts: list[TextBlockChange] | None = None,
        prompt_blocks: list[PromptBlockChange] | None = None,
    ) -> Character:
        character = self.characters.get(project_id, character_id)
        self._check_revision(character.revision, expected_revision)
        data = character.model_dump()
        if name is not None:
            data["name"] = name.strip()
        if short_texts is not None:
            data["short_texts"] = self._merge_texts(character, short_texts)
        if prompt_blocks is not None:
            data["prompt_blocks"] = self._merge_prompt_blocks(
                character, prompt_blocks
            )
        return self.characters.save(Character.model_validate(data))

    def create_prompt(
        self,
        project_id: UUID,
        character_id: UUID,
        *,
        expected_revision: int,
        text: str,
        block_ids: list[UUID],
    ) -> Character:
        character = self.characters.get(project_id, character_id)
        self._check_revision(character.revision, expected_revision)
        known = {block.id: block for block in character.prompt_blocks}
        if any(block_id not in known for block_id in block_ids):
            raise ServiceValidationError(
                "Le prompt reference un bloc inconnu de cette fiche."
            )
        snapshots = [
            PromptBlockSnapshot(
                id=known[block_id].id,
                name=known[block_id].name,
                text=known[block_id].text,
            )
            for block_id in block_ids
        ]
        data = character.model_dump()
        data["prompt_versions"] = [
            *character.prompt_versions,
            PromptVersion(
                text=text.strip(),
                block_ids=block_ids,
                blocks=snapshots,
            ),
        ]
        return self.characters.save(Character.model_validate(data))

    def activate_prompt(
        self,
        project_id: UUID,
        character_id: UUID,
        prompt_id: UUID,
        *,
        expected_revision: int,
    ) -> Character:
        character = self.characters.get(project_id, character_id)
        self._check_revision(character.revision, expected_revision)
        if not any(prompt.id == prompt_id for prompt in character.prompt_versions):
            raise NotFoundError(f"prompt '{prompt_id}' was not found")
        if character.active_prompt_version_id == prompt_id:
            return character
        data = character.model_dump()
        data["active_prompt_version_id"] = prompt_id
        return self.characters.save(Character.model_validate(data))

    @staticmethod
    def _merge_texts(
        character: Character,
        changes: list[TextBlockChange],
    ) -> list[TextBlock]:
        existing = {block.id: block for block in character.short_texts}
        merged = []
        for change in changes:
            text = change.text.strip()
            if change.id is None:
                merged.append(TextBlock(text=text))
                continue
            current = existing.get(change.id)
            if current is None:
                raise ServiceValidationError(
                    "Un texte court n'appartient pas a cette fiche."
                )
            merged.append(
                TextBlock(
                    id=current.id,
                    text=text,
                    created_at=current.created_at,
                    updated_at=(
                        utc_now() if text != current.text else current.updated_at
                    ),
                )
            )
        return merged

    @staticmethod
    def _merge_prompt_blocks(
        character: Character,
        changes: list[PromptBlockChange],
    ) -> list[PromptBlock]:
        existing = {block.id: block for block in character.prompt_blocks}
        merged = []
        for change in changes:
            name = change.name.strip()
            text = change.text.strip()
            if change.id is None:
                merged.append(PromptBlock(name=name, text=text))
                continue
            current = existing.get(change.id)
            if current is None:
                raise ServiceValidationError(
                    "Un bloc de prompt n'appartient pas a cette fiche."
                )
            merged.append(
                PromptBlock(
                    id=current.id,
                    name=name,
                    text=text,
                    created_at=current.created_at,
                    updated_at=(
                        utc_now()
                        if name != current.name or text != current.text
                        else current.updated_at
                    ),
                )
            )
        return merged

    @staticmethod
    def _check_revision(current: int, expected: int) -> None:
        if current != expected:
            raise ConflictError(
                "La fiche a change sur disque; rechargez avant de sauver."
            )
