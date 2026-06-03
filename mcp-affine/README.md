# MCP AFFiNE (DAWNCR0W)

Serveur MCP pour AFFiNE basé sur [DAWNCR0W/affine-mcp-server](https://github.com/DAWNCR0W/affine-mcp-server) v2.x.

## Statut

🚧 **En préparation** — dossier créé le 3 juin 2026

## Objectif

Déployer le serveur MCP AFFiNE en mode HTTP remote pour accès cross-device (Claude Desktop, Web, iOS, iPad).

## Workspaces cibles

- **OPEPARTNER** : `3869ae28-9638-4390-a28d-905ff5c563d6`
- **AGNI Consult** : `85a5d444-80db-49e6-996d-f2ecda4d66ae`

## Configuration future

- **URL** : `mcp-affine.agnisolution.fr`
- **Auth** : OIDC/Keycloak (realm `mcp`, client `mcp-affine`)
- **Instance AFFiNE** : `https://affine.agnisolution.fr`

## Prochaines étapes

1. Cloner le repo DAWNCR0W v2.x
2. Adapter la configuration pour mode HTTP
3. Configurer les variables d'environnement
4. Tester localement
5. Déployer via Coolify
