"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  activatePromptVersion,
  createPromptVersion,
  getCharacter,
  updateCharacter,
} from "../../lib/api/characters";
import ReferenceLibrary from "./ReferenceLibrary";

function draftKey(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function textDrafts(character) {
  return character.short_texts.map((item) => ({ ...item, key: item.id }));
}

function blockDrafts(character) {
  return character.prompt_blocks.map((item) => ({ ...item, key: item.id }));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function SectionHeader({ eyebrow, title, description }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-soft">
        {eyebrow}
      </p>
      <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
        {description}
      </p>
    </div>
  );
}

export default function CharacterDetailView({ projectId, characterId }) {
  const [character, setCharacter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [nameDraft, setNameDraft] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [nameError, setNameError] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [texts, setTexts] = useState([]);
  const [textsError, setTextsError] = useState("");
  const [savingTexts, setSavingTexts] = useState(false);
  const [blocks, setBlocks] = useState([]);
  const [blocksError, setBlocksError] = useState("");
  const [savingBlocks, setSavingBlocks] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [selectedBlockIds, setSelectedBlockIds] = useState([]);
  const [promptError, setPromptError] = useState("");
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [activatingPromptId, setActivatingPromptId] = useState(null);
  const [referencesMutating, setReferencesMutating] = useState(false);
  const editorMutating =
    savingName ||
    savingTexts ||
    savingBlocks ||
    savingPrompt ||
    activatingPromptId !== null;
  const isMutating = editorMutating || referencesMutating;

  useEffect(() => {
    let cancelled = false;
    getCharacter(projectId, characterId)
      .then((loadedCharacter) => {
        if (!cancelled) {
          setCharacter(loadedCharacter);
          setNameDraft(loadedCharacter.name);
          setTexts(textDrafts(loadedCharacter));
          setBlocks(blockDrafts(loadedCharacter));
          setSelectedBlockIds((ids) =>
            ids.filter((id) =>
              loadedCharacter.prompt_blocks.some((block) => block.id === id),
            ),
          );
          setLoadError("");
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, characterId, reloadKey]);

  function retry() {
    setLoading(true);
    setReloadKey((key) => key + 1);
  }

  async function handleRename(event) {
    event.preventDefault();
    const name = nameDraft.trim();
    if (!name) {
      setNameError("Saisissez un nom de personnage.");
      return;
    }
    setNameError("");
    setSavingName(true);
    try {
      const updated = await updateCharacter(projectId, characterId, {
        expected_revision: character.revision,
        name,
      });
      setCharacter(updated);
      setNameDraft(updated.name);
      setRenaming(false);
    } catch (error) {
      setNameError(error.message);
    } finally {
      setSavingName(false);
    }
  }

  function addText() {
    setTexts((items) => [
      ...items,
      { id: null, key: draftKey("text"), text: "" },
    ]);
  }

  function updateText(key, value) {
    setTexts((items) =>
      items.map((item) => (item.key === key ? { ...item, text: value } : item)),
    );
  }

  function removeText(key) {
    setTexts((items) => items.filter((item) => item.key !== key));
  }

  async function saveTexts() {
    if (texts.some((item) => !item.text.trim())) {
      setTextsError("Chaque texte ajoute doit contenir au moins un caractere.");
      return;
    }
    setSavingTexts(true);
    setTextsError("");
    try {
      const updated = await updateCharacter(projectId, characterId, {
        expected_revision: character.revision,
        short_texts: texts.map((item) => ({
          ...(item.id ? { id: item.id } : {}),
          text: item.text.trim(),
        })),
      });
      setCharacter(updated);
      setTexts(textDrafts(updated));
    } catch (error) {
      setTextsError(error.message);
    } finally {
      setSavingTexts(false);
    }
  }

  function addBlock() {
    setBlocks((items) => [
      ...items,
      { id: null, key: draftKey("block"), name: "", text: "" },
    ]);
  }

  function updateBlock(key, field, value) {
    setBlocks((items) =>
      items.map((item) =>
        item.key === key ? { ...item, [field]: value } : item,
      ),
    );
  }

  function removeBlock(key) {
    setBlocks((items) => items.filter((item) => item.key !== key));
  }

  async function saveBlocks() {
    if (blocks.some((item) => !item.name.trim() || !item.text.trim())) {
      setBlocksError("Chaque bloc doit avoir un nom et un contenu.");
      return;
    }
    setSavingBlocks(true);
    setBlocksError("");
    try {
      const updated = await updateCharacter(projectId, characterId, {
        expected_revision: character.revision,
        prompt_blocks: blocks.map((item) => ({
          ...(item.id ? { id: item.id } : {}),
          name: item.name.trim(),
          text: item.text.trim(),
        })),
      });
      setCharacter(updated);
      setBlocks(blockDrafts(updated));
      setSelectedBlockIds((ids) =>
        ids.filter((id) => updated.prompt_blocks.some((block) => block.id === id)),
      );
    } catch (error) {
      setBlocksError(error.message);
    } finally {
      setSavingBlocks(false);
    }
  }

  function togglePromptBlock(blockId) {
    setSelectedBlockIds((ids) =>
      ids.includes(blockId)
        ? ids.filter((id) => id !== blockId)
        : [...ids, blockId],
    );
  }

  async function handleCreatePrompt(event) {
    event.preventDefault();
    const text = promptText.trim();
    if (!text) {
      setPromptError("Saisissez le contenu de la nouvelle version.");
      return;
    }
    setSavingPrompt(true);
    setPromptError("");
    try {
      const updated = await createPromptVersion(projectId, characterId, {
        expected_revision: character.revision,
        text,
        block_ids: selectedBlockIds,
      });
      setCharacter(updated);
      setPromptText("");
      setSelectedBlockIds([]);
    } catch (error) {
      setPromptError(error.message);
    } finally {
      setSavingPrompt(false);
    }
  }

  async function activatePrompt(promptId) {
    setActivatingPromptId(promptId);
    setPromptError("");
    try {
      const updated = await activatePromptVersion(
        projectId,
        characterId,
        promptId,
        { expected_revision: character.revision },
      );
      setCharacter(updated);
    } catch (error) {
      setPromptError(error.message);
    } finally {
      setActivatingPromptId(null);
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-zinc-400">
        Chargement de la fiche...
      </div>
    );
  }

  if (loadError) {
    return (
      <div role="alert" className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="font-medium text-red-200">{loadError}</p>
        <button
          type="button"
          onClick={retry}
          className="mt-4 min-h-11 rounded-xl border border-white/10 px-4 text-sm font-medium hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
        >
          Reessayer
        </button>
      </div>
    );
  }

  const referencedBlockIds = new Set(
    character.prompt_versions.flatMap((prompt) => prompt.block_ids),
  );
  const promptHistory = [...character.prompt_versions].reverse();

  return (
    <div className="space-y-8">
      <header>
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex min-h-11 items-center text-sm text-zinc-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus"
        >
          Retour au projet
        </Link>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft">
              Fiche personnage
            </p>
            <h1 className="break-words [overflow-wrap:anywhere] text-3xl font-semibold tracking-tight text-white md:text-4xl">
              {character.name}
            </h1>
            <p className="mt-2 text-sm text-zinc-500">
              Revision {character.revision} sur disque
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={retry}
              disabled={isMutating}
              className="min-h-11 rounded-xl border border-white/10 px-4 text-sm text-zinc-400 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
            >
              Recharger
            </button>
            <button
              type="button"
              onClick={() => setRenaming((visible) => !visible)}
              disabled={isMutating}
              className="min-h-11 rounded-xl border border-white/10 px-4 text-sm font-medium text-zinc-200 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
            >
              Renommer
            </button>
          </div>
        </div>
      </header>

      {renaming && (
        <form
          onSubmit={handleRename}
          className="rounded-2xl border border-accent/20 bg-accent/5 p-5"
        >
          <label className="block text-sm font-medium text-zinc-200">
            Nouveau nom du personnage
            <input
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
              disabled={isMutating}
              maxLength={120}
              className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-4 text-white outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              disabled={isMutating}
              className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {savingName ? "Enregistrement..." : "Enregistrer"}
            </button>
            <button
              type="button"
              onClick={() => setRenaming(false)}
              disabled={isMutating}
              className="min-h-11 rounded-xl px-4 text-sm text-zinc-400 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Annuler
            </button>
          </div>
          {nameError && (
            <p role="alert" className="mt-3 text-sm text-red-300">
              {nameError}
            </p>
          )}
        </form>
      )}

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
        <SectionHeader
          eyebrow="01 / References"
          title="Images de reference"
          description="Importez les images qui guideront ce personnage. Elles sont copiees dans sa bibliotheque locale."
        />
        <ReferenceLibrary
          projectId={projectId}
          character={character}
          disabled={editorMutating}
          onCharacterChange={setCharacter}
          onBusyChange={setReferencesMutating}
        />
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
        <SectionHeader
          eyebrow="02 / Description"
          title="Textes courts"
          description="Consignez les elements narratifs utiles sans les melanger aux prompts techniques."
        />
        <div className="space-y-3">
          {texts.map((item, index) => (
            <div key={item.key} className="flex flex-col gap-2 sm:flex-row sm:items-start">
              <label className="min-w-0 flex-1 text-sm text-zinc-300">
                <span className="sr-only">Texte court {index + 1}</span>
                <textarea
                  value={item.text}
                  onChange={(event) => updateText(item.key, event.target.value)}
                  disabled={isMutating}
                  maxLength={1000}
                  rows={3}
                  placeholder="Silhouette, attitude, histoire ou intention..."
                  className="w-full resize-y rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-zinc-600 focus:border-accent focus:ring-2 focus:ring-accent/20"
                />
              </label>
              <button
                type="button"
                onClick={() => removeText(item.key)}
                disabled={isMutating}
                className="min-h-11 rounded-xl px-3 text-sm text-zinc-500 hover:bg-red-500/10 hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
              >
                Retirer
              </button>
            </div>
          ))}
          {texts.length === 0 && (
            <p className="rounded-xl border border-dashed border-white/10 p-5 text-sm text-zinc-600">
              Aucun texte court enregistre.
            </p>
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={addText}
            disabled={isMutating}
            className="min-h-11 rounded-xl border border-white/10 px-4 text-sm text-zinc-300 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
          >
            Ajouter un texte
          </button>
          <button
            type="button"
            onClick={saveTexts}
            disabled={isMutating}
            className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:opacity-50"
          >
            {savingTexts ? "Enregistrement..." : "Enregistrer les textes"}
          </button>
        </div>
        {textsError && (
          <p role="alert" className="mt-3 text-sm text-red-300">
            {textsError}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
        <SectionHeader
          eyebrow="03 / Modules"
          title="Blocs reutilisables"
          description="Ajoutez des fragments optionnels. Un bloc utilise par une version devient immuable pour preserver l'historique."
        />
        <div className="space-y-3">
          {blocks.map((block, index) => {
            const isReferenced = block.id && referencedBlockIds.has(block.id);
            return (
              <div
                key={block.key}
                className="rounded-xl border border-white/10 bg-black/25 p-4"
              >
                <div className="grid gap-3 md:grid-cols-[minmax(0,0.35fr)_minmax(0,1fr)_auto]">
                  <label className="text-sm text-zinc-300">
                    Nom du bloc {index + 1}
                    <input
                      value={block.name}
                      onChange={(event) =>
                        updateBlock(block.key, "name", event.target.value)
                      }
                      disabled={isReferenced || isMutating}
                      maxLength={120}
                      className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-black/40 px-3 text-white outline-none focus:border-accent disabled:cursor-not-allowed disabled:text-zinc-500"
                    />
                  </label>
                  <label className="text-sm text-zinc-300">
                    Contenu
                    <textarea
                      value={block.text}
                      onChange={(event) =>
                        updateBlock(block.key, "text", event.target.value)
                      }
                      disabled={isReferenced || isMutating}
                      maxLength={4000}
                      rows={2}
                      className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-white outline-none focus:border-accent disabled:cursor-not-allowed disabled:text-zinc-500"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => removeBlock(block.key)}
                    disabled={isReferenced || isMutating}
                    title={
                      isReferenced
                        ? "Ce bloc est utilise par une version de prompt"
                        : undefined
                    }
                    className="min-h-11 self-end rounded-xl px-3 text-sm text-zinc-500 hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-35"
                  >
                    Retirer
                  </button>
                </div>
                {isReferenced && (
                  <p className="mt-2 text-xs text-zinc-600">
                    Verrouille par les versions de prompt.
                  </p>
                )}
              </div>
            );
          })}
          {blocks.length === 0 && (
            <p className="rounded-xl border border-dashed border-white/10 p-5 text-sm text-zinc-600">
              Aucun bloc reutilisable.
            </p>
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={addBlock}
            disabled={isMutating}
            className="min-h-11 rounded-xl border border-white/10 px-4 text-sm text-zinc-300 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:cursor-not-allowed disabled:opacity-50"
          >
            Ajouter un bloc
          </button>
          <button
            type="button"
            onClick={saveBlocks}
            disabled={isMutating}
            className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:opacity-50"
          >
            {savingBlocks ? "Enregistrement..." : "Enregistrer les blocs"}
          </button>
        </div>
        {blocksError && (
          <p role="alert" className="mt-3 text-sm text-red-300">
            {blocksError}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
        <SectionHeader
          eyebrow="04 / Prompt"
          title="Nouvelle version"
          description="Chaque enregistrement cree une version immuable. L'activation reste une action separee."
        />
        <form onSubmit={handleCreatePrompt}>
          <label className="block text-sm font-medium text-zinc-200">
            Nouveau prompt
            <textarea
              value={promptText}
              onChange={(event) => setPromptText(event.target.value)}
              disabled={isMutating}
              maxLength={12000}
              rows={6}
              placeholder="Decrivez le portrait, le cadrage, la lumiere et l'intention..."
              className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-zinc-600 focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </label>
          {character.prompt_blocks.length > 0 && (
            <fieldset className="mt-4">
              <legend className="text-sm font-medium text-zinc-300">
                Blocs a associer
              </legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {character.prompt_blocks.map((block) => (
                  <label
                    key={block.id}
                    className="flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-black/25 px-3 text-sm text-zinc-300 hover:border-accent/30"
                  >
                    <input
                      type="checkbox"
                      checked={selectedBlockIds.includes(block.id)}
                      onChange={() => togglePromptBlock(block.id)}
                      disabled={isMutating}
                      className="h-4 w-4 accent-accent"
                    />
                    <span className="sr-only">Utiliser le bloc </span>
                    {block.name}
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <button
            type="submit"
            disabled={isMutating}
            className="mt-4 min-h-11 rounded-xl bg-accent px-5 text-sm font-semibold hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:opacity-50"
          >
            {savingPrompt ? "Creation..." : "Creer la version"}
          </button>
        </form>
        {promptError && (
          <p role="alert" className="mt-3 text-sm text-red-300">
            {promptError}
          </p>
        )}

        <div className="mt-8 border-t border-white/10 pt-6">
          <div className="mb-4 flex items-baseline justify-between">
            <h3 className="font-semibold text-white">Historique</h3>
            <span className="text-xs tabular-nums text-zinc-500">
              {promptHistory.length} version{promptHistory.length > 1 ? "s" : ""}
            </span>
          </div>
          {promptHistory.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 p-5 text-sm text-zinc-600">
              Aucune version de prompt.
            </p>
          ) : (
            <div className="space-y-3">
              {promptHistory.map((prompt, index) => {
                const isActive = character.active_prompt_version_id === prompt.id;
                const promptBlocks = character.prompt_blocks.filter((block) =>
                  prompt.block_ids.includes(block.id),
                );
                return (
                  <article
                    key={prompt.id}
                    className={`rounded-xl border p-4 ${
                      isActive
                        ? "border-accent/35 bg-accent/[0.07]"
                        : "border-white/10 bg-black/25"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span>Version {promptHistory.length - index}</span>
                        <span>{formatDate(prompt.created_at)}</span>
                        {isActive && (
                          <span className="rounded-full bg-accent/15 px-2 py-1 font-semibold text-accent-soft">
                            Version active
                          </span>
                        )}
                      </div>
                      {!isActive && (
                        <button
                          type="button"
                          onClick={() => activatePrompt(prompt.id)}
                          disabled={isMutating}
                          aria-label={`Activer la version ${promptHistory.length - index}`}
                          className="min-h-11 rounded-xl border border-white/10 px-3 text-xs font-medium text-zinc-300 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus disabled:opacity-50"
                        >
                          {activatingPromptId === prompt.id
                            ? "Activation..."
                            : "Activer la version"}
                        </button>
                      )}
                    </div>
                    <p className="mt-4 whitespace-pre-wrap break-words [overflow-wrap:anywhere] text-sm leading-6 text-zinc-200">
                      {prompt.text}
                    </p>
                    {promptBlocks.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {promptBlocks.map((block) => (
                          <span
                            key={block.id}
                            className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-zinc-500"
                          >
                            {block.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
