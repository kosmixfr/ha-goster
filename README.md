# Goster pour Home Assistant

Intégration Home Assistant pour surveiller un serveur Goster via son API HTTP.

## Fonctionnalités

- Statistiques de la bibliothèque : films, séries, épisodes, fichiers, taille, torrents, utilisateurs.
- Activité utilisateur : téléchargements actifs, demandes en attente, partages actifs.
- Supervision système avec un token administrateur : CPU, mémoire, charge, débits réseau, I/O disque, transcodages actifs, IPv4 publique.
- État de joignabilité BitTorrent.
- Mise à jour configurable et réauthentification automatique.

## Installation avec HACS

1. Dans Home Assistant, ouvrez **HACS** → **Intégrations**.
2. Ouvrez le menu (⋮) → **Dépôts personnalisés**.
3. Ajoutez `https://github.com/kosmixfr/ha-goster` avec la catégorie **Intégration**.
4. Recherchez **Goster**, installez l'intégration puis redémarrez Home Assistant.
5. Allez dans **Paramètres** → **Appareils et services** → **Ajouter une intégration** → **Goster**.

## Configuration

| Champ | Description |
| --- | --- |
| URL de l'application (`app_url`) | URL de votre instance Goster, par exemple `https://goster.example.com` |
| Token API | Token d'un utilisateur Goster |

Le token se trouve dans les paramètres de l'utilisateur Goster. Un compte
administrateur est nécessaire pour les capteurs système (CPU, mémoire, réseau,
disque, transcodages).

## Entités

Les entités sont regroupées dans un appareil de type service nommé d'après le
compte Goster configuré.

### Capteurs

`Films`, `Séries`, `Épisodes`, `Fichiers`, `Taille de la bibliothèque`,
`Torrents`, `Utilisateurs`, `Durée de fonctionnement`, `Téléchargements actifs`,
`Demandes en attente`, `Partages actifs`, et pour les administrateurs :
`Utilisation CPU`, `Utilisation mémoire`, `Charge (1 min)`, `Débit descendant`,
`Débit montant`, `Lecture disque`, `Écriture disque`, `Transcodages actifs`,
`IPv4 publique`.

### Capteurs binaires

`BitTorrent joignable`.

## Options

- **Intervalle de mise à jour** : 60 secondes par défaut (15 à 3600).
- **Interface réseau** : vide pour une détection automatique (`tun0`, puis `eth0`).

## Sécurité

Le token est stocké dans le fichier de configuration Home Assistant
(`.storage/core.config_entries`). Utilisez de préférence un token dédié et
révoquez-le si nécessaire. Ne publiez jamais votre token dans une issue ou un
dépôt Git.

## Licence

MIT
