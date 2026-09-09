# Circus Portraits Workflow - Plan d'implementation V1

Date: 2026-09-08
Spec de reference: `docs/superpowers/specs/2026-09-08-circus-portraits-workflow-design.md`

## Objectif du plan

Transformer progressivement le fork Vibe-Workflow en application locale de production de portraits, sans conserver MuAPI comme infrastructure centrale.

La V1 doit fournir un flux complet et testable : creer un projet, gerer 30 personnages, importer des references, versionner les prompts, executer des workflows avec des connecteurs simules puis reels, selectionner et upscaler des images, et afficher la selection courante dans une galerie.

## Constat sur le depot actuel

L'inspection du depot montre que les briques existantes ne sont pas separees comme le suggere le README :

- `client/app/page.js` est une landing page marketing, pas une vue projet.
- `client/app/workflow/page.js` et `client/app/workflow/[id]/page.js` chargent les donnees depuis le backend MuAPI.
- `server/app/routers/workflow_router.py` expose principalement un proxy vers MuAPI.
- `server/app/utils/workflow_helper.py` contient des URLs MuAPI codees en dur pour la persistance, les schemas, l'execution, les uploads et les resultats.
- `packages/workflow-builder/src/components/NodeFlow.jsx` concentre dans environ 2 900 lignes le canvas, l'etat, la serialisation, l'execution, le polling, les formulaires et les appels HTTP.
- `packages/workflow-builder/src/components/WorkflowStore.jsx` utilise deux variables globales au lieu d'un store isole.
- Aucun modele Project, Character, Asset ou Job n'existe.
- Aucun stockage local de projet, aucune miniature locale et aucune base operationnelle n'existent.
- Aucun test automatise n'existe dans le depot.

La partie a reutiliser est donc principalement React Flow, certaines interactions du canvas et quelques composants visuels. La persistance, l'execution, les uploads et le protocole de nodes doivent etre remplaces.

## Principes de mise en oeuvre

- Les fichiers du projet creatif sont la source de verite.
- Tous les chemins stockes dans les JSON sont relatifs a la racine du projet.
- Les ecritures JSON sont atomiques.
- Les cles API restent uniquement dans `server/.env`.
- Le frontend ne recoit jamais la valeur d'une cle API.
- Aucun appel fournisseur n'est effectue avant une action explicite de l'utilisateur.
- Les connecteurs simules valident tout le parcours avant le branchement d'une API payante.
- Le package `workflow-builder` ne connait ni Next.js, ni Axios, ni les routes backend.
- Chaque lot doit laisser le depot executable et teste.
- Les donnees de production et les images ne sont jamais ajoutees au depot Git.

## Architecture cible

```text
client/
  app/
    projects/
    projects/[projectId]/
    projects/[projectId]/characters/[characterId]/
    projects/[projectId]/gallery/
    projects/[projectId]/workflows/
    projects/[projectId]/workflows/[workflowId]/
    connectors/
  components/
  lib/api/

packages/workflow-builder/src/
  WorkflowBuilder.jsx
  canvas/
  nodes/
  registry/
  serialization/
  validation/

server/app/
  api/
  connectors/
  domain/
  repositories/
  services/
  storage/
  main.py

server/tests/
client/tests/
packages/workflow-builder/tests/
```

Les donnees utilisateur vivent hors du depot, sous une racine configuree par `PROJECTS_ROOT`.

```text
<PROJECTS_ROOT>/
  <project-slug>/
    project.json
    characters/<character-slug>/character.json
    characters/<character-slug>/references/
    characters/<character-slug>/generations/
    characters/<character-slug>/upscales/
    characters/<character-slug>/exports/
    workflows/
    runs/
    jobs/
    thumbnails/
```

## Lot 0 - Baseline et outils de verification

### But

Rendre l'existant reproductible et ajouter un filet de securite avant toute restructuration.

### Changements

- Ajouter les scripts racine `lint`, `test` et `build` dans `package.json`.
- Faire construire `packages/workflow-builder` avant le build Next.js.
- Ajouter Vitest et Testing Library dans `client/package.json` et `packages/workflow-builder/package.json`.
- Ajouter `pytest`, `pytest-asyncio` et les dependances de test HTTP dans `server/requirements-dev.txt`.
- Corriger la commande de lancement documentee dans `server/README.md` vers `uvicorn app.main:app`.
- Ajouter un test backend du healthcheck.
- Ajouter un test de rendu minimal du composant `WorkflowBuilder` existant.
- Documenter les commandes Windows de lancement dans le README racine.

### Fichiers principaux

- `package.json`
- `client/package.json`
- `packages/workflow-builder/package.json`
- `server/requirements-dev.txt`
- `server/tests/test_health.py`
- `packages/workflow-builder/tests/WorkflowBuilder.test.jsx`
- `server/README.md`
- `README.md`

### Verification

```text
npm run build:lib
npm run lint -w client
npm run test -w packages/workflow-builder
python -m pytest server/tests
python -m ruff check server
npm run build:app
```

### Critere de sortie

Les commandes de verification passent sur un clone propre sans cle MuAPI.

## Lot 1 - Configuration et stockage local atomique

### But

Creer les fondations locales avant toute nouvelle interface.

### Changements

- Ajouter une configuration Pydantic lisant `PROJECTS_ROOT` et les identifiants publics des connecteurs depuis `server/.env`.
- Definir les modeles versionnes `Project`, `Character`, `PromptVersion`, `Asset`, `Workflow`, `WorkflowRun` et `Job`.
- Utiliser des UUID stables comme identifiants et des slugs uniquement pour les noms de dossiers.
- Stocker les dates au format ISO 8601 UTC.
- Implementer la validation des chemins pour interdire toute sortie de `PROJECTS_ROOT`.
- Implementer les ecritures JSON atomiques par fichier temporaire puis remplacement.
- Implementer un verrou local par projet pour serialiser les modifications concurrentes.
- Creer les repositories Project et Character.
- Conserver les jobs dans `jobs/<job-id>.json` pour la V1 ; ne pas introduire SQLite tant qu'un besoin concret ne l'exige pas.

### Fichiers principaux

- `server/app/config.py`
- `server/app/domain/models.py`
- `server/app/storage/paths.py`
- `server/app/storage/atomic_json.py`
- `server/app/storage/locks.py`
- `server/app/repositories/project_repository.py`
- `server/app/repositories/character_repository.py`
- `server/tests/storage/`
- `server/.env.example`

### Tests

- Creation d'un projet et de son arborescence.
- Relecture identique apres redemarrage du repository.
- Rejet de `..`, chemins absolus et slugs invalides.
- Ecriture interrompue ne detruisant pas le JSON precedent.
- Deux mises a jour concurrentes ne perdant pas de donnees.
- Aucun secret present dans les modeles serialises.

### Critere de sortie

Un projet et 30 personnages peuvent etre crees, relus et deplaces sous une autre racine sans modifier leurs JSON.

## Lot 2 - API projets, personnages et prompts

### But

Exposer le modele local au frontend et couvrir le premier parcours metier sans image.

### Changements

- Ajouter des routes FastAPI avec schemas Pydantic explicites.
- Remplacer la landing page par une vue minimale des projets.
- Ajouter la creation et l'ouverture d'un projet.
- Ajouter la liste, la creation, le renommage et l'ouverture des personnages.
- Ajouter l'edition des textes courts.
- Ajouter des versions immuables de prompts avec un pointeur `active_prompt_version_id`.
- Ajouter les blocs de prompt optionnels comme entites reutilisables dans une fiche.
- Centraliser les appels HTTP du client dans `client/lib/api/`.
- Ajouter une navigation sobre : `Projet`, `Galerie`, `Workflows`, `Connecteurs`.

### Endpoints

```text
GET  /api/projects
POST /api/projects
GET  /api/projects/{project_id}
PATCH /api/projects/{project_id}
GET  /api/projects/{project_id}/characters
POST /api/projects/{project_id}/characters
GET  /api/projects/{project_id}/characters/{character_id}
PATCH /api/projects/{project_id}/characters/{character_id}
POST /api/projects/{project_id}/characters/{character_id}/prompts
POST /api/projects/{project_id}/characters/{character_id}/prompts/{prompt_id}/activate
```

### Fichiers principaux

- `server/app/api/projects.py`
- `server/app/api/characters.py`
- `server/app/services/project_service.py`
- `server/app/services/character_service.py`
- `server/app/main.py`
- `client/app/page.js`
- `client/app/projects/page.js`
- `client/app/projects/[projectId]/page.js`
- `client/app/projects/[projectId]/characters/[characterId]/page.js`
- `client/components/AppShell.jsx`
- `client/lib/api/projects.js`
- `client/lib/api/characters.js`

### Tests

- Validation API des champs obligatoires et erreurs 404.
- Creation de 30 personnages via l'API.
- Conservation de tout l'historique des prompts.
- Une seule version active a la fois.
- Tests composants des etats vide, chargement et erreur.

### Critere de sortie

L'utilisateur peut creer son projet, ses 30 fiches, leurs textes et leurs prompts depuis l'interface.

## Lot 3 - Bibliotheque d'images locale

### But

Importer et servir les references sans envoi vers MuAPI ou un autre service externe.

### Changements

- Ajouter `python-multipart` et Pillow aux dependances backend.
- Ajouter un endpoint multipart d'import de reference.
- Valider extension, MIME reel, taille maximale et dimensions.
- Calculer un hash SHA-256 pour la tracabilite sans fusion automatique des doublons.
- Generer un nom de fichier controle et une miniature locale.
- Enregistrer uniquement des chemins relatifs dans `character.json`.
- Servir les images et miniatures par `asset_id`, jamais par chemin fourni par le client.
- Signaler un fichier manquant sans supprimer ses metadonnees.
- Ajouter l'import par glisser-deposer et la grille de references dans la fiche personnage.
- Supprimer l'utilisation du flux d'upload signe MuAPI dans le nouveau parcours.

### Endpoints

```text
POST   /api/projects/{project_id}/characters/{character_id}/references
GET    /api/assets/{asset_id}/content
GET    /api/assets/{asset_id}/thumbnail
DELETE /api/projects/{project_id}/characters/{character_id}/references/{asset_id}
```

### Fichiers principaux

- `server/app/api/assets.py`
- `server/app/services/asset_service.py`
- `server/app/services/thumbnail_service.py`
- `server/app/repositories/asset_repository.py`
- `client/components/characters/ReferenceLibrary.jsx`
- `client/lib/api/assets.js`
- `server/tests/assets/`

### Tests

- Import PNG, JPEG et WebP valides.
- Rejet des fichiers trop lourds, MIME trompeur et contenu non image.
- Rejet du path traversal.
- Miniature creee et lisible.
- Projet deplace restant fonctionnel.
- Fichier manquant affiche comme anomalie.

### Critere de sortie

Les references sont copiees dans le dossier personnage, visibles dans l'interface et recuperables hors application.

## Lot 4 - Workflows locaux et nouvel editeur controle

### But

Remplacer la persistance MuAPI par un format local minimal et rendre le package nodal independant du framework et du fournisseur.

### Format de workflow

Le JSON contient uniquement : version de schema, identifiant, nom, nodes, positions, parametres non secrets, `connector_id` et edges. Les resultats et historiques n'appartiennent pas a la definition du workflow.

### Changements backend

- Definir un registre local de nodes V1 et leurs ports types.
- Valider IDs uniques, ports compatibles, edges valides et absence de cycle.
- Ajouter le repository de workflows sous `workflows/`.
- Exposer le CRUD local des workflows.
- Ne jamais retourner ou accepter de cle API dans les payloads.

### Changements workflow-builder

- Remplacer `WorkflowBuilder.jsx` par une interface controlee : `workflow`, `nodeDefinitions`, `onChange`, `onSave`, `onRun`.
- Creer un `WorkflowCanvas` focalise sur React Flow.
- Extraire le registre des nodes, les regles de connexion, la serialisation et la validation.
- Implementer les representations minimales des sept nodes V1.
- Retirer `useParams`, `Link`, Axios et tous les appels `/api` du package.
- Retirer les variables globales de `WorkflowStore.jsx`.
- Alimenter le menu depuis le registre local, pas depuis des schemas MuAPI.
- Une fois le nouvel editeur valide, supprimer les composants MuAPI, video/audio, publication, assistant et calcul de cout devenus inutilises.

### Endpoints

```text
GET    /api/projects/{project_id}/workflows
POST   /api/projects/{project_id}/workflows
GET    /api/projects/{project_id}/workflows/{workflow_id}
PUT    /api/projects/{project_id}/workflows/{workflow_id}
DELETE /api/projects/{project_id}/workflows/{workflow_id}
GET    /api/workflow-node-definitions
```

### Fichiers principaux

- `server/app/domain/workflow.py`
- `server/app/repositories/workflow_repository.py`
- `server/app/services/workflow_validation.py`
- `server/app/api/workflows.py`
- `packages/workflow-builder/src/WorkflowBuilder.jsx`
- `packages/workflow-builder/src/canvas/WorkflowCanvas.jsx`
- `packages/workflow-builder/src/registry/nodeDefinitions.js`
- `packages/workflow-builder/src/serialization/workflowSerializer.js`
- `packages/workflow-builder/src/validation/connectionRules.js`
- `packages/workflow-builder/src/nodes/`
- `client/app/projects/[projectId]/workflows/`

### Tests

- Round-trip JSON sans perte.
- Rejet des graphes cycliques et ports incompatibles.
- Rejet de tout champ ressemblant a un secret dans la definition.
- Ajout, deplacement, connexion et suppression d'un node dans le canvas.
- Sauvegarde explicite d'un workflow local.
- Le package se rend sans contexte Next.js et sans serveur HTTP.

### Critere de sortie

Un workflow V1 peut etre cree, edite, sauvegarde, recharge et deplace avec le projet, sans requete MuAPI.

## Lot 5 - Jobs durables, connecteurs simules et execution du graphe

### But

Valider le parcours complet sans cout API et sans dependance fournisseur.

### Changements

- Definir le contrat `Connector` avec `capabilities`, `validate`, `estimate_cost`, `submit`, `poll`, `cancel`, `fetch_results` et `normalize_error`.
- Creer un registre de connecteurs cote backend.
- Implementer `mock-generation` et `mock-upscale` avec sorties deterministes.
- Implementer les transitions `queued`, `running`, `completed`, `failed`, `cancelled`.
- Persister chaque job avant execution.
- Au demarrage, remettre les jobs interrompus dans un etat recuperable explicite.
- Implementer le retry en creant une nouvelle tentative liee au job precedent.
- Implementer un executeur topologique du workflow.
- Donner au run un contexte `project_id` et `character_id`.
- Implementer les sept nodes V1 cote backend.
- Traiter `Selection` comme lecture de l'image selectionnee courante, pas comme pause interactive au milieu d'un run.
- Copier les resultats simules dans `generations/`, `upscales/` ou `exports/` selon le node.
- Ajouter une vue simple de file d'attente et polling client.

### Endpoints

```text
POST /api/projects/{project_id}/workflow-runs
GET  /api/workflow-runs/{run_id}
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/retry
POST /api/jobs/{job_id}/cancel
GET  /api/connectors
POST /api/connectors/{connector_id}/check
```

### Fichiers principaux

- `server/app/connectors/base.py`
- `server/app/connectors/registry.py`
- `server/app/connectors/mock_generation.py`
- `server/app/connectors/mock_upscale.py`
- `server/app/domain/jobs.py`
- `server/app/repositories/job_repository.py`
- `server/app/services/job_runner.py`
- `server/app/services/workflow_executor.py`
- `server/app/api/jobs.py`
- `server/app/api/connectors.py`
- `client/components/jobs/JobQueue.jsx`
- `client/lib/api/jobs.js`

### Tests

- Toutes les transitions de statut autorisees et interdites.
- Reprise apres simulation de redemarrage.
- Retry conservant l'historique de la tentative precedente.
- Echec d'un connecteur ne modifiant pas les assets existants.
- Execution topologique et propagation des sorties typees.
- Generation puis upscale simules avec fichiers locaux.
- Aucun appel reseau pendant toute la suite de tests mock.

### Critere de sortie

Un workflow generation puis un workflow upscale peuvent etre executes de bout en bout avec les mocks, avec jobs persistants et fichiers locaux.

## Lot 6 - Selection, favoris, rejets, exports et galerie

### But

Completer le parcours de production et la planche contact interactive.

### Changements

- Ajouter la classification manuelle d'un asset : neutre, favori ou rejete.
- Autoriser une seule image selectionnee courante par personnage.
- Conserver l'historique des generations et upscales meme apres changement de selection.
- Ajouter la comparaison visuelle des resultats dans la fiche personnage.
- Ajouter l'action d'export vers `exports/` avec un nom deterministe.
- Ajouter la galerie projet utilisant exclusivement les miniatures.
- Afficher un placeholder explicite lorsqu'un personnage n'a pas de selection.
- Ouvrir la fiche personnage depuis la galerie.
- Ne pas implementer encore l'export statique de planche contact.

### Endpoints

```text
PATCH /api/projects/{project_id}/characters/{character_id}/assets/{asset_id}
POST  /api/projects/{project_id}/characters/{character_id}/selection
POST  /api/projects/{project_id}/characters/{character_id}/exports
GET   /api/projects/{project_id}/gallery
```

### Fichiers principaux

- `server/app/api/gallery.py`
- `server/app/services/selection_service.py`
- `server/app/services/export_service.py`
- `client/components/characters/ResultGrid.jsx`
- `client/app/projects/[projectId]/gallery/page.js`
- `client/components/gallery/ContactSheet.jsx`
- `client/lib/api/gallery.js`

### Tests

- Favori et rejet independants de la selection courante.
- Changement de selection mettant la galerie a jour.
- Placeholder pour les fiches sans selection.
- Galerie de 30 personnages utilisant des miniatures.
- Export n'ecrasant pas silencieusement un fichier existant.
- Asset manquant signale sans perte de metadata.

### Critere de sortie

Les 30 personnages sont visibles en planche contact avec leur derniere image selectionnee, et chaque carte ouvre la bonne fiche.

## Lot 7 - Premiers connecteurs API reels

### But

Remplacer les mocks par une generation et un upscale reels sans modifier le domaine ni les workflows.

### Decision requise avant ce lot

Choisir le premier fournisseur reel de generation et le premier fournisseur d'upscale. MuAPI est le choix le plus rapide a evaluer car le depot l'utilise deja, mais son integration devra passer par le nouveau contrat et non par les anciens proxies.

Cette decision ne bloque pas les lots 0 a 6.

### Changements

- Ajouter les variables de connecteur dans `server/.env.example` sans valeur secrete.
- Implementer un connecteur de generation et un connecteur d'upscale.
- Mapper les parametres communs vers le schema du fournisseur.
- Envoyer les references uniquement lors du lancement explicite du job.
- Gerer timeout, polling avec backoff, annulation si disponible et erreurs normalisees.
- Telecharger chaque resultat distant dans le dossier local avant de marquer le job `completed`.
- Exposer uniquement disponibilite, capacites et presence du secret a la vue Connecteurs.
- Ajouter une estimation de cout uniquement si l'API fournit une information fiable.
- Ajouter un test de contrat commun reutilisable pour tous les connecteurs.

### Fichiers principaux

- `server/app/connectors/<generation_provider>.py`
- `server/app/connectors/<upscale_provider>.py`
- `server/tests/connectors/test_contract.py`
- `server/tests/connectors/test_<provider>.py`
- `client/app/connectors/page.js`
- `client/components/connectors/ConnectorStatus.jsx`
- `server/.env.example`

### Tests

- Tests unitaires avec HTTP simule pour succes, timeout, erreur, polling et resultat invalide.
- Test d'integration reel optionnel, desactive sans cle API.
- Verification qu'une cle sentinelle n'apparait dans aucun JSON du projet.
- Verification qu'aucune reference n'est envoyee avant `submit`.
- Resultat distant telecharge et servi localement.

### Critere de sortie

Un portrait peut etre genere puis upscale avec de vraies APIs, tout en restant gere par les memes workflows que les mocks.

## Lot 8 - Nettoyage, qualite et exploitation locale

### But

Retirer l'architecture MuAPI devenue obsolete et fiabiliser l'usage quotidien sur Windows 11.

### Changements

- Supprimer les routes proxy MuAPI et les composants frontend non utilises.
- Supprimer les dependances mortes, notamment SQLAlchemy et asyncpg si elles restent inutilisees.
- Nettoyer le lockfile et l'ancienne entree workspace extraneous.
- Epingler les dependances Python dans un mecanisme reproductible.
- Ajouter Playwright pour les parcours critiques.
- Ajouter une CI qui lance lint, tests et builds avant le build Docker.
- Corriger Docker Compose avec bind mounts explicites pour `PROJECTS_ROOT` et la configuration locale.
- Supprimer les URLs `127.0.0.1` codees en dur des Server Components.
- Verifier le fonctionnement sur Edge et Chrome actuels.
- Documenter sauvegarde, restauration, changement d'ordinateur et gestion du `.env`.

### Parcours E2E

- Creer un projet.
- Creer 30 personnages.
- Importer une reference.
- Creer deux versions de prompt et en activer une.
- Executer une generation simulee.
- Marquer un favori et selectionner une image.
- Executer un upscale simule.
- Exporter le resultat.
- Verifier la galerie.
- Redemarrer le backend et retrouver toutes les donnees.

### Critere de sortie

Toutes les validations de la spec passent sur Windows 11 avec un dossier projet hors du depot, et le flux principal ne depend plus des services MuAPI historiques.

## Ordre de livraison recommande

1. Baseline et tests.
2. Stockage local.
3. Projets, personnages et prompts.
4. References et miniatures.
5. Workflows locaux et editeur controle.
6. Jobs et connecteurs simules.
7. Selection, export et galerie.
8. Connecteurs reels.
9. Nettoyage et durcissement.

Cet ordre evite de modifier d'abord l'interface nodale sans disposer d'un modele fiable pour les donnees qu'elle doit manipuler.

## Strategie de commits

Chaque lot doit etre decoupe en petits commits autonomes : tests/configuration, domaine, repository, API, interface, puis documentation. Ne pas melanger le retrait massif de l'ancien code MuAPI avec l'ajout des fondations locales dans un seul commit.

Avant de commencer l'implementation, creer une branche de travail depuis `main`. Le premier point de validation utilisateur est la fin du lot 2 ; le second est la fin du lot 4 avec l'editeur local ; le troisieme est la fin du lot 6 avec la galerie complete.

## Verification finale V1

```text
npm run lint
npm run test
npm run build
python -m ruff check server
python -m pytest server/tests
npm run test:e2e -w client
```

Les commandes racine devront etre ajoutees au lot 0 pour rendre cette verification uniforme.
