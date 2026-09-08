# Circus Portraits Workflow - Design V1

Date: 2026-09-08

## Objectif

Creer une application locale personnelle pour produire 30 portraits imaginaires de personnages de cirque a partir d'images de reference, de textes courts et de variantes de prompts.

L'outil partira de `Vibe-Workflow` comme base technique afin de reutiliser son editeur nodal open source. La V1 doit rester minimale, propre et efficace : elle organise la production, lance des generations et des upscales via APIs configurables, conserve l'historique utile et permet de visualiser l'ensemble des personnages dans une galerie de type planche contact.

## Hors Perimetre V1

- Retouche IA avancee ou image editing.
- Execution locale ComfyUI ou Stable Diffusion.
- Direction artistique globale obligatoire.
- Multi-utilisateur, authentification, partage reseau ou hebergement cloud.
- Marketplace, statistiques avancees, billing ou gestion de credits detaillee.
- Coffre de secrets Windows Credential Manager.

## Base Technique

Le projet sera derive de `https://github.com/SamurAIGPT/Vibe-Workflow`.

Structure de reference conservee autant que possible :

```text
Vibe-Workflow/
  client/                # Application Next.js locale
  packages/
    workflow-builder/    # Editeur nodal reutilisable
  server/                # Backend FastAPI local
```

La V1 ajoute une couche metier au-dessus du workflow nodal :

```text
Project -> Characters -> Assets -> AI Jobs
```

L'editeur nodal reste separe des fiches personnages. Les workflows sont crees une fois, puis appliques a une fiche personnage ou a un ensemble de fiches.

## Mode D'Utilisation

L'application est une application locale personnelle sur Windows 11. La V1 peut s'executer en mode developpement local ; le packaging en application installee n'est pas requis pour valider la V1.

Il n'y a pas de compte utilisateur. Les projets et les images restent sur le disque local. Les donnees ne quittent la machine que lorsque l'utilisateur execute un node appelant une API externe configuree.

## Projet Et Personnages

Un projet represente une serie de production. Pour le cas initial, il contient 30 fiches personnages.

Chaque fiche personnage contient :

- Un identifiant stable.
- Un nom ou titre.
- De courts textes descriptifs.
- Une bibliotheque interne d'images de reference.
- Des prompts libres versionnes.
- Des blocs de prompt reutilisables optionnels.
- Les generations brutes.
- Les upscales.
- Les favoris et rejets.
- L'image selectionnee courante.
- Les exports finaux.

Il n'y a pas de coherence globale imposee entre les personnages. Les blocs de prompts restent disponibles comme aide ponctuelle, sans contrainte de serie.

## Galerie / Planche Contact

La V1 inclut une vue galerie minimale affichant tous les personnages du projet.

Pour chaque personnage, la galerie affiche l'image selectionnee courante, ou un etat vide si aucune image n'est encore selectionnee. Cette vue sert a controler rapidement l'avancement, ouvrir une fiche, reperer les personnages incomplets et juger visuellement le corpus.

L'exportation statique de la planche contact n'est pas requise pour valider la V1. Elle pourra etre ajoutee ensuite a partir de la galerie interactive.

## Organisation Des Fichiers

Chaque projet est un dossier lisible hors de l'application. La base de donnees locale peut servir a accelerer l'interface, mais les fichiers du projet doivent rester recuperables et comprehensibles directement sur disque.

Structure proposee :

```text
circus-portraits/
  project.json
  characters/
    001-auguste-melancolique/
      character.json
      references/
      generations/
      upscales/
      exports/
    002-ecuyere-fantome/
      character.json
      references/
      generations/
      upscales/
      exports/
  contact-sheets/
  workflows/
```

Les images de reference importees sont copiees dans `references/`. Elles ne sont pas seulement liees depuis leur emplacement d'origine, afin de garder le projet portable.

Les generations et upscales sont nommes avec des informations utiles : date, fournisseur, workflow et numero de variante. Les metadonnees detaillees restent dans `character.json` et/ou dans la base locale.

## Donnees Persistantes

`project.json` contient les informations generales du projet : nom, date de creation, version de schema, liste des personnages et workflows associes.

`character.json` contient les informations propres a la fiche : textes, prompts, references, jobs, assets, favoris, rejets, image selectionnee et exports.

Les workflows exportables ne contiennent jamais de secrets. Ils referencent les connecteurs par identifiant.

## Workflows Nodaux V1

Nodes minimaux :

- `Character Input` : charge les textes, prompts, references et parametres du personnage.
- `Prompt Variant` : selectionne ou combine un prompt libre avec des blocs optionnels.
- `Image Generation API` : appelle un connecteur configurable de generation.
- `Result Set` : enregistre les images brutes dans `generations/`.
- `Selection` : permet de marquer favoris, rejets et image courante.
- `Upscale API` : appelle un connecteur configurable d'upscale depuis une image selectionnee.
- `Export` : copie ou convertit la version finale dans `exports/`.

La retouche IA future pourra etre ajoutee comme node `Image Edit API` entre `Selection` et `Upscale API`, sans modifier le modele general.

## Connecteurs API

Les fournisseurs de generation et d'upscale sont configurables. La V1 ne doit pas verrouiller l'outil sur un seul fournisseur.

Chaque connecteur expose une interface commune :

- Identifiant du connecteur.
- Type : generation ou upscale.
- Parametres acceptes.
- Validation minimale des parametres.
- Estimation de cout si le fournisseur la rend disponible.
- Soumission du job.
- Suivi de statut.
- Recuperation des resultats.
- Normalisation des erreurs.

Les connecteurs peuvent etre ajoutes progressivement. La V1 peut commencer avec un connecteur de generation et un connecteur d'upscale, plus des connecteurs simules pour tester le flux sans consommer d'API.

## Jobs Asynchrones

Les generations et upscales sont geres comme jobs asynchrones par le backend FastAPI.

Statuts requis :

- `queued`
- `running`
- `completed`
- `failed`
- `cancelled` si le fournisseur ou l'implementation le permet

Chaque job garde :

- Le personnage cible.
- Le workflow utilise.
- Le connecteur utilise.
- Les parametres envoyes.
- Les fichiers produits.
- Le statut courant.
- Le message d'erreur eventuel.
- Les timestamps utiles.

Un echec de job ne supprime jamais les references, prompts, generations precedentes ou selections existantes.

## Interface

L'interface V1 contient cinq vues principales :

- `Projet` : liste ou grille des personnages, etat d'avancement, acces galerie.
- `Fiche personnage` : references, textes courts, prompts, generations, upscales, selection finale.
- `Galerie` : planche contact interactive des images selectionnees courantes.
- `Workflows` : editeur nodal adapte depuis Vibe-Workflow.
- `Connecteurs` : configuration des fournisseurs et verification de disponibilite.

La navigation doit rester courte et lisible. Il faut eviter les dashboards generiques, les panneaux inutiles et les metriques qui ne servent pas directement la production des images.

Parcours principal d'une fiche : importer references, saisir textes, creer ou choisir un prompt, lancer un workflow, comparer les resultats, selectionner une image, lancer l'upscale, exporter.

## Securite Et Secrets

Pour la V1, les cles API sont stockees en clair dans un fichier `.env` local non versionne.

Regles :

- Les dossiers projet ne contiennent jamais de cles API.
- Les workflows ne contiennent jamais de cles API.
- Les fiches personnages ne contiennent jamais de cles API.
- Les exports ne contiennent jamais de cles API.
- Les nodes referencent uniquement des identifiants de connecteurs.
- `.env` est reserve a la machine locale et doit etre ignore par Git.

Cette decision reduit la complexite de la V1. Une evolution future pourra remplacer `.env` par Windows Credential Manager sans changer le modele projet.

## Erreurs Et Recuperation

L'outil doit privilegier la preservation des donnees creatives.

En cas d'erreur API, le job passe en `failed`, le message est visible, et l'utilisateur peut relancer. Les fichiers deja produits restent en place. Les donnees de la fiche ne sont pas modifiees silencieusement.

En cas de fichier manquant sur disque, l'interface signale l'anomalie sans supprimer automatiquement la reference de metadata.

## Validation V1

La V1 est validee si les scenarios suivants fonctionnent :

- Creer un projet local.
- Creer 30 fiches personnages.
- Importer des images de reference dans une fiche.
- Ajouter des textes courts a une fiche.
- Creer et versionner plusieurs prompts.
- Creer ou reutiliser un workflow nodal simple.
- Executer un connecteur de generation simule.
- Enregistrer les resultats dans `generations/`.
- Marquer des images favorites et rejetees.
- Selectionner une image courante.
- Executer un connecteur d'upscale simule.
- Enregistrer l'upscale dans `upscales/`.
- Exporter une image finale dans `exports/`.
- Afficher la galerie des images selectionnees courantes.
- Confirmer qu'aucune cle API n'est presente dans les dossiers projet, workflows ou exports.

## Risques

- `Vibe-Workflow` peut etre plus oriente demo/API MuAPI que plateforme extensible prete a adapter. Une exploration technique devra verifier la separation entre editeur nodal, backend et execution.
- La portabilite des fichiers dependra d'une convention de chemins stricte.
- Les APIs de generation et d'upscale peuvent avoir des schemas tres differents. L'interface commune doit rester minimale pour ne pas bloquer l'ajout de fournisseurs.
- La galerie peut devenir lente si les images sont tres lourdes. Il faudra generer ou utiliser des miniatures.
- Le stockage `.env` en clair est volontairement simple, mais moins sur qu'un coffre OS.

## Decisions Validees

- Partir de `Vibe-Workflow`.
- Construire une application locale personnelle.
- Utiliser des APIs pour generation et upscale.
- Reporter la retouche IA.
- Utiliser des connecteurs configurables.
- Gerer la production par fiches personnages.
- Importer les references dans une bibliotheque interne par fiche.
- Memoriser textes courts et variantes de prompts.
- Ne pas imposer de coherence globale entre les 30 portraits.
- Organiser les fichiers dans des dossiers lisibles hors app.
- Utiliser un editeur de workflow separe, applique aux fiches.
- Ajouter une galerie / planche contact des images selectionnees.
- Stocker les cles API dans `.env` en clair pour la V1.
