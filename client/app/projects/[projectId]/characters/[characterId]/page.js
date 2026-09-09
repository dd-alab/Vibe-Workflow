import CharacterDetailView from "../../../../../components/characters/CharacterDetailView";

export default async function CharacterPage({ params }) {
  const { projectId, characterId } = await params;
  return (
    <CharacterDetailView projectId={projectId} characterId={characterId} />
  );
}
