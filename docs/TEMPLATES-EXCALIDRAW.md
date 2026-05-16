# Templates Excalidraw — Guide complet

> Comment créer et utiliser des templates réutilisables (BMC, PESTEL, SWOT, etc.)

---

## 🎯 Concept

Un **template Excalidraw** est une scène pré-dessinée qui sert de base pour créer de nouveaux documents. Par exemple :

- **Business Model Canvas** avec les 9 cases structurées
- **PESTEL** avec les 6 catégories (Politique, Économique, Social, etc.)
- **SWOT** avec les 4 quadrants (Forces, Faiblesses, Opportunités, Menaces)
- **Organigramme** avec des formes pré-positionnées

**Principe de fonctionnement** :

1. Tu crées manuellement le template "vierge" dans Excalidraw
2. Tu insères des **placeholders** (textes type `{{CLIENT_NAME}}`, `{{PARTNERS}}`)
3. On sauvegarde le JSON du template dans la table `templates`
4. Le MCP custom clone le template et remplace les placeholders par les vraies données
5. Le nouveau document est sauvegardé avec un nouvel ID unique

---

## 📐 Deux approches pour les templates

### Approche A — Placeholders textuels (SIMPLE, RECOMMANDÉ)

**Principe** : Insérer des marqueurs texte type `{{VARIABLE}}` que le MCP remplacera.

**Exemple BMC** :

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│  Partenaires clés       │  Activités clés         │  Propositions de valeur │
│                         │                         │                         │
│  {{PARTNERS}}           │  {{KEY_ACTIVITIES}}     │  {{VALUE_PROPOSITION}}  │
│                         │                         │                         │
├─────────────────────────┼─────────────────────────┤                         │
│  Ressources clés        │  Relations clients      │  Segments clients       │
│                         │                         │                         │
│  {{KEY_RESOURCES}}      │  {{CUSTOMER_RELATIONS}} │  {{CUSTOMER_SEGMENTS}}  │
│                         │                         │                         │
├─────────────────────────┴─────────────────────────┴─────────────────────────┤
│  Structure de coûts                    │  Flux de revenus                   │
│                                        │                                    │
│  {{COST_STRUCTURE}}                    │  {{REVENUE_STREAMS}}               │
└────────────────────────────────────────┴────────────────────────────────────┘
```

**Workflow MCP** :

```python
# 1. Récupérer le template
template = get_template('BMC')
scene_json = template['excalidraw_json']

# 2. Remplacer les placeholders
replacements = {
    '{{CLIENT_NAME}}': 'Dupont SAS',
    '{{PARTNERS}}': '• Fournisseur A\n• Fournisseur B',
    '{{KEY_ACTIVITIES}}': '• Production\n• Distribution',
    # ... autres remplacements
}

for element in scene_json['elements']:
    if element['type'] == 'text':
        for placeholder, value in replacements.items():
            element['text'] = element['text'].replace(placeholder, value)

# 3. Sauvegarder avec un nouvel ID
new_id = generate_unique_id()
save_scene(new_id, scene_json)
```

**Avantages** :
- ✅ Ultra-simple à mettre en place
- ✅ Facile à débugger (on voit les placeholders dans Excalidraw)
- ✅ Pas besoin de parsing complexe

**Inconvénients** :
- ❌ Moins flexible pour du contenu dynamique (listes de longueur variable)
- ❌ Risque de collision si un utilisateur tape `{{PARTNERS}}` dans un texte libre

---

### Approche B — Zones identifiées (AVANCÉ, PLUS TARD)

**Principe** : Utiliser des éléments invisibles ou avec `customData` pour marquer les zones à remplir.

**Exemple** :

```json
{
  "elements": [
    {
      "id": "rect-partners",
      "type": "rectangle",
      "x": 100,
      "y": 100,
      "width": 300,
      "height": 400,
      "customData": { "zone": "PARTNERS" }
    },
    {
      "id": "marker-partners-content",
      "type": "text",
      "x": 110,
      "y": 150,
      "text": "",
      "customData": { "contentFor": "PARTNERS", "mode": "list" }
    }
  ]
}
```

**Workflow MCP** :

```python
# 1. Identifier les markers
for element in scene_json['elements']:
    if 'customData' in element and 'contentFor' in element['customData']:
        zone = element['customData']['contentFor']
        mode = element['customData'].get('mode', 'text')
        
        if zone == 'PARTNERS':
            if mode == 'list':
                # Générer dynamiquement des éléments texte pour chaque partenaire
                y_offset = element['y']
                for partner in partners_list:
                    scene_json['elements'].append({
                        'type': 'text',
                        'x': element['x'],
                        'y': y_offset,
                        'text': f'• {partner}',
                        'fontSize': 16
                    })
                    y_offset += 30
```

**Avantages** :
- ✅ Très flexible (listes dynamiques, positionnement intelligent)
- ✅ Pas de risque de collision avec du texte libre
- ✅ Peut gérer des cas complexes (organigrammes avec N niveaux)

**Inconvénients** :
- ❌ Plus complexe à mettre en place
- ❌ Nécessite un parsing/génération plus sophistiqué

---

## 🛠️ Création d'un template (étape par étape)

### Exemple : Business Model Canvas

**Étape 1 : Dessiner le template dans Excalidraw**

1. Ouvrir https://excalidraw.agnisolution.fr (s'authentifier)
2. Créer les 9 rectangles du BMC avec les titres
3. Ajouter les placeholders dans chaque case :
   - Case "Partenaires clés" : `{{PARTNERS}}`
   - Case "Activités clés" : `{{KEY_ACTIVITIES}}`
   - Case "Propositions de valeur" : `{{VALUE_PROPOSITION}}`
   - Case "Relations clients" : `{{CUSTOMER_RELATIONS}}`
   - Case "Segments clients" : `{{CUSTOMER_SEGMENTS}}`
   - Case "Canaux de distribution" : `{{CHANNELS}}`
   - Case "Ressources clés" : `{{KEY_RESOURCES}}`
   - Case "Structure de coûts" : `{{COST_STRUCTURE}}`
   - Case "Flux de revenus" : `{{REVENUE_STREAMS}}`

4. Ajouter un titre en haut : `Business Model Canvas — {{CLIENT_NAME}}`

5. Sauvegarder la scène (bouton "Save")

**Étape 2 : Récupérer l'ID de la scène**

L'URL ressemble à : `https://excalidraw.agnisolution.fr/#json=abc123def456`

L'ID est `abc123def456`.

**Étape 3 : Récupérer le JSON depuis Postgres**

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c \"SELECT value FROM keyv WHERE key='abc123def456';\""
```

Copier le JSON retourné.

**Étape 4 : Insérer le template dans la table `templates`**

```sql
INSERT INTO templates (nom, description, excalidraw_json, categorie, tags, created_by)
VALUES (
  'BMC',
  'Business Model Canvas avec 9 cases (Osterwalder)',
  '{"type":"excalidraw","version":2,"elements":[...]}',  -- Le JSON complet
  'strategy',
  ARRAY['consulting', 'strategy', 'business-model'],
  1  -- ID de Christophe dans la table utilisateurs
);
```

Ou via un script Node.js :

```javascript
// save-template.js
const { Pool } = require('pg');
const fs = require('fs');

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const templateJson = JSON.parse(fs.readFileSync('bmc-template.json', 'utf8'));

pool.query(
  `INSERT INTO templates (nom, description, excalidraw_json, categorie, tags, created_by)
   VALUES ($1, $2, $3, $4, $5, $6)
   RETURNING id`,
  [
    'BMC',
    'Business Model Canvas avec 9 cases (Osterwalder)',
    templateJson,
    'strategy',
    ['consulting', 'strategy', 'business-model'],
    1
  ],
  (err, res) => {
    if (err) throw err;
    console.log('Template créé avec ID:', res.rows[0].id);
    pool.end();
  }
);
```

**Étape 5 : Vérifier que le template est bien en base**

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c \"SELECT id, nom, description, categorie FROM templates;\""
```

---

## 🤖 Utilisation des templates dans le MCP custom (Phase H)

### Fonction `create_from_template`

```python
# mcp-custom/tools.py

import json
import copy
from typing import Dict, List, Optional

def create_from_template(
    template_name: str,
    data: Dict[str, str],
    user_id: int,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Crée une nouvelle scène depuis un template.
    
    Args:
        template_name: Nom du template (ex: 'BMC', 'PESTEL', 'SWOT')
        data: Dictionnaire des données à injecter (ex: {'CLIENT_NAME': 'Dupont SAS', ...})
        user_id: ID de l'utilisateur créateur
        metadata: Métadonnées additionnelles (client_id, mission_id, etc.)
    
    Returns:
        {
            'id': '3793308620810895',
            'url': 'https://excalidraw.agnisolution.fr/#json=3793308620810895',
            'edit_url': 'https://excalidraw.agnisolution.fr/#json=3793308620810895',
            'template_used': 'BMC'
        }
    """
    # 1. Récupérer le template depuis Postgres
    template = db.query(
        "SELECT id, excalidraw_json FROM templates WHERE nom = $1",
        [template_name]
    ).fetchone()
    
    if not template:
        raise ValueError(f"Template '{template_name}' non trouvé")
    
    # 2. Clone le JSON (deep copy)
    scene_json = copy.deepcopy(template['excalidraw_json'])
    
    # 3. Remplacer les placeholders
    for element in scene_json.get('elements', []):
        if element.get('type') == 'text':
            text = element.get('text', '')
            
            # Remplacer tous les placeholders {{KEY}} par leur valeur
            for key, value in data.items():
                placeholder = f'{{{{{key}}}}}'  # {{KEY}}
                if placeholder in text:
                    text = text.replace(placeholder, str(value))
            
            element['text'] = text
    
    # 4. Générer un nouvel ID unique
    new_id = generate_unique_id(length=12)
    
    # 5. Sauvegarder dans le backend Excalidraw
    response = requests.post(
        f"{EXCALIDRAW_BACKEND_URL}/api/v2/scenes",
        json=scene_json,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 201:
        raise Exception(f"Échec sauvegarde backend: {response.text}")
    
    # 6. Insérer le tracking dans keyv avec les colonnes custom
    db.execute(
        """UPDATE keyv
           SET created_by = $1,
               template_id = $2,
               metadata = $3
           WHERE key = $4""",
        [user_id, template['id'], json.dumps(metadata or {}), new_id]
    )
    
    # 7. Retourner les infos
    return {
        'id': new_id,
        'url': f'https://excalidraw.agnisolution.fr/#json={new_id}',
        'edit_url': f'https://excalidraw.agnisolution.fr/#json={new_id}',
        'template_used': template_name
    }
```

### Fonctions simplifiées pour chaque template

```python
def create_bmc(client_name: str, data: Dict, user_id: int) -> Dict:
    """Crée un Business Model Canvas."""
    template_data = {
        'CLIENT_NAME': client_name,
        'PARTNERS': '\n'.join([f'• {p}' for p in data.get('partners', [])]),
        'KEY_ACTIVITIES': '\n'.join([f'• {a}' for a in data.get('key_activities', [])]),
        'VALUE_PROPOSITION': data.get('value_proposition', ''),
        'CUSTOMER_RELATIONS': data.get('customer_relations', ''),
        'CUSTOMER_SEGMENTS': '\n'.join([f'• {s}' for s in data.get('customer_segments', [])]),
        'CHANNELS': '\n'.join([f'• {c}' for c in data.get('channels', [])]),
        'KEY_RESOURCES': '\n'.join([f'• {r}' for r in data.get('key_resources', [])]),
        'COST_STRUCTURE': data.get('cost_structure', ''),
        'REVENUE_STREAMS': data.get('revenue_streams', '')
    }
    
    return create_from_template('BMC', template_data, user_id, {
        'document_type': 'BMC',
        'client_name': client_name
    })

def create_pestel(client_name: str, data: Dict, user_id: int) -> Dict:
    """Crée une analyse PESTEL."""
    template_data = {
        'CLIENT_NAME': client_name,
        'POLITICAL': data.get('political', ''),
        'ECONOMIC': data.get('economic', ''),
        'SOCIAL': data.get('social', ''),
        'TECHNOLOGICAL': data.get('technological', ''),
        'ENVIRONMENTAL': data.get('environmental', ''),
        'LEGAL': data.get('legal', '')
    }
    
    return create_from_template('PESTEL', template_data, user_id, {
        'document_type': 'PESTEL',
        'client_name': client_name
    })

def create_swot(client_name: str, data: Dict, user_id: int) -> Dict:
    """Crée une analyse SWOT."""
    template_data = {
        'CLIENT_NAME': client_name,
        'STRENGTHS': '\n'.join([f'• {s}' for s in data.get('strengths', [])]),
        'WEAKNESSES': '\n'.join([f'• {w}' for w in data.get('weaknesses', [])]),
        'OPPORTUNITIES': '\n'.join([f'• {o}' for o in data.get('opportunities', [])]),
        'THREATS': '\n'.join([f'• {t}' for t in data.get('threats', [])])
    }
    
    return create_from_template('SWOT', template_data, user_id, {
        'document_type': 'SWOT',
        'client_name': client_name
    })
```

### Exemple d'utilisation depuis Claude Desktop

**Prompt utilisateur** :

> "Crée un BMC pour le client Dupont SAS avec les partenaires : Fournisseur A, Fournisseur B, et les activités clés : Production, Distribution"

**Appel MCP** :

```python
result = create_bmc(
    client_name='Dupont SAS',
    data={
        'partners': ['Fournisseur A', 'Fournisseur B'],
        'key_activities': ['Production', 'Distribution'],
        'value_proposition': 'Solutions sur mesure',
        'customer_segments': ['PME industrielles', 'Grands comptes'],
        # ... autres champs
    },
    user_id=1  # ID de Christophe
)

print(f"BMC créé : {result['url']}")
```

**Résultat** :

```json
{
  "id": "3793308620810895",
  "url": "https://excalidraw.agnisolution.fr/#json=3793308620810895",
  "edit_url": "https://excalidraw.agnisolution.fr/#json=3793308620810895",
  "template_used": "BMC"
}
```

Le BMC est créé avec les données injectées, accessible via le lien, et traçable en base :

```sql
SELECT 
  k.key AS scene_id,
  u.email AS created_by,
  t.nom AS template_used,
  k.metadata->>'client_name' AS client_name
FROM keyv k
LEFT JOIN utilisateurs u ON k.created_by = u.id
LEFT JOIN templates t ON k.template_id = t.id
WHERE k.key = '3793308620810895';
```

---

## 📋 Templates à créer (Phase H)

| Template | Priorité | Description | Placeholders clés |
|----------|----------|-------------|-------------------|
| **BMC** | 🔴 Haute | Business Model Canvas (9 cases) | CLIENT_NAME, PARTNERS, KEY_ACTIVITIES, VALUE_PROPOSITION, etc. |
| **PESTEL** | 🔴 Haute | Analyse macro-environnement (6 catégories) | CLIENT_NAME, POLITICAL, ECONOMIC, SOCIAL, TECHNOLOGICAL, ENVIRONMENTAL, LEGAL |
| **SWOT** | 🔴 Haute | Analyse forces/faiblesses (4 quadrants) | CLIENT_NAME, STRENGTHS, WEAKNESSES, OPPORTUNITIES, THREATS |
| **Organigramme** | 🟡 Moyenne | Structure hiérarchique | COMPANY_NAME, CEO, DEPARTMENTS, TEAMS |
| **Value Proposition Canvas** | 🟡 Moyenne | Proposition de valeur détaillée | CLIENT_NAME, JOBS, PAINS, GAINS, PRODUCTS, PAIN_RELIEVERS, GAIN_CREATORS |
| **Plan 90 jours** | 🟢 Basse | Roadmap avec milestones | CLIENT_NAME, MONTH1, MONTH2, MONTH3, OBJECTIVES |

---

## 🎨 Bonnes pratiques

### Design des templates

1. **Utiliser des polices lisibles** (16-20pt pour le texte, 24-32pt pour les titres)
2. **Couleurs cohérentes** (palette OPEPARTNER : bleus, gris, vert accent)
3. **Espacement généreux** (marges internes 20-30px dans les rectangles)
4. **Placeholders visibles** (en gras ou en italique pour les repérer facilement)

### Nommage des placeholders

- **Convention** : `{{UPPERCASE_SNAKE_CASE}}`
- **Explicite** : `{{CLIENT_NAME}}` plutôt que `{{NAME}}`
- **Cohérent** : Même placeholder pour même donnée dans tous les templates

### Versioning des templates

Quand un template est modifié :

```sql
-- Incrémenter la version
UPDATE templates
SET version = version + 1,
    updated_at = NOW(),
    excalidraw_json = '...',  -- Nouveau JSON
WHERE nom = 'BMC';
```

Les scènes créées gardent `template_id` qui pointe vers le template, on peut donc tracer quelle version a été utilisée.

---

## 🔮 Évolutions futures (post-Phase H)

1. **Templates collaboratifs** — Plusieurs users peuvent créer des templates
2. **Marketplace de templates** — Partage entre différents workspaces
3. **Templates avec variables conditionnelles** — Sections qui apparaissent/disparaissent selon les données
4. **Export templates vers fichiers** — Pour backup/partage hors système

---

**Auteur** : Claude Code + Christophe Martin  
**Date** : 16 mai 2026  
**Statut** : 📋 **DOCUMENTATION COMPLÈTE**
