-- ============================================
-- Script SQL : Authentification + Templates
-- Base : excalidraw_storage
-- Auteur : Claude Code + Christophe Martin
-- Date : 16 mai 2026
-- ============================================

-- 1. Table utilisateurs
-- =====================
CREATE TABLE IF NOT EXISTS utilisateurs (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL, -- bcrypt hash
  nom VARCHAR(100),
  actif BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ,
  CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Index pour recherche rapide par email
CREATE INDEX idx_utilisateurs_email ON utilisateurs(email);
CREATE INDEX idx_utilisateurs_actif ON utilisateurs(actif);

COMMENT ON TABLE utilisateurs IS 'Utilisateurs du système Excalidraw - Gestion via NocoDB';
COMMENT ON COLUMN utilisateurs.password_hash IS 'Hash bcrypt du mot de passe (10 rounds minimum)';
COMMENT ON COLUMN utilisateurs.actif IS 'Si false, utilisateur ne peut plus se connecter';

-- 2. Table templates
-- ==================
CREATE TABLE IF NOT EXISTS templates (
  id SERIAL PRIMARY KEY,
  nom VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  excalidraw_json JSONB NOT NULL,
  thumbnail_url TEXT,
  categorie VARCHAR(50),
  tags TEXT[], -- ex: ['strategy', 'consulting', 'opepartner']
  created_by INTEGER REFERENCES utilisateurs(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version INTEGER DEFAULT 1,
  actif BOOLEAN DEFAULT true
);

-- Index pour recherche par catégorie et tags
CREATE INDEX idx_templates_categorie ON templates(categorie);
CREATE INDEX idx_templates_tags ON templates USING GIN(tags);
CREATE INDEX idx_templates_actif ON templates(actif);

COMMENT ON TABLE templates IS 'Templates Excalidraw réutilisables (BMC, PESTEL, SWOT, etc.)';
COMMENT ON COLUMN templates.excalidraw_json IS 'JSON complet de la scène Excalidraw (avec placeholders)';
COMMENT ON COLUMN templates.tags IS 'Tags pour filtrage (ex: strategy, marketing, project_management)';

-- 3. Modifier la table keyv (ajouter colonnes tracking)
-- ======================================================
DO $$
BEGIN
  -- Ajouter created_by si n'existe pas
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='keyv' AND column_name='created_by'
  ) THEN
    ALTER TABLE keyv ADD COLUMN created_by INTEGER REFERENCES utilisateurs(id);
  END IF;

  -- Ajouter template_id si n'existe pas
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='keyv' AND column_name='template_id'
  ) THEN
    ALTER TABLE keyv ADD COLUMN template_id INTEGER REFERENCES templates(id);
  END IF;

  -- Ajouter created_at_tracked si n'existe pas (éviter conflit avec created_at potentiel)
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='keyv' AND column_name='created_at_tracked'
  ) THEN
    ALTER TABLE keyv ADD COLUMN created_at_tracked TIMESTAMPTZ DEFAULT NOW();
  END IF;

  -- Ajouter metadata JSONB pour futurs besoins
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='keyv' AND column_name='metadata'
  ) THEN
    ALTER TABLE keyv ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
  END IF;
END $$;

-- Index pour recherche par auteur
CREATE INDEX IF NOT EXISTS idx_keyv_created_by ON keyv(created_by);
CREATE INDEX IF NOT EXISTS idx_keyv_template_id ON keyv(template_id);
CREATE INDEX IF NOT EXISTS idx_keyv_created_at_tracked ON keyv(created_at_tracked);

COMMENT ON COLUMN keyv.created_by IS 'ID de l''utilisateur qui a créé cette scène';
COMMENT ON COLUMN keyv.template_id IS 'ID du template utilisé (si créé depuis un template)';
COMMENT ON COLUMN keyv.metadata IS 'Métadonnées additionnelles (tags, client_id, mission_id, etc.)';

-- 4. Fonction trigger pour updated_at (templates)
-- ================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_templates_updated_at
BEFORE UPDATE ON templates
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 5. Vue pour les scènes avec informations utilisateur
-- =====================================================
CREATE OR REPLACE VIEW scenes_with_user AS
SELECT
  k.key AS scene_id,
  k.value AS scene_data,
  k.created_by,
  u.email AS created_by_email,
  u.nom AS created_by_name,
  k.template_id,
  t.nom AS template_name,
  k.created_at_tracked,
  k.metadata
FROM keyv k
LEFT JOIN utilisateurs u ON k.created_by = u.id
LEFT JOIN templates t ON k.template_id = t.id
ORDER BY k.created_at_tracked DESC;

COMMENT ON VIEW scenes_with_user IS 'Vue enrichie des scènes avec infos utilisateur et template';

-- 6. Permissions pour l'utilisateur excalidraw_backend
-- =====================================================
GRANT ALL PRIVILEGES ON TABLE utilisateurs TO excalidraw_backend;
GRANT ALL PRIVILEGES ON TABLE templates TO excalidraw_backend;
GRANT USAGE, SELECT ON SEQUENCE utilisateurs_id_seq TO excalidraw_backend;
GRANT USAGE, SELECT ON SEQUENCE templates_id_seq TO excalidraw_backend;
GRANT SELECT ON scenes_with_user TO excalidraw_backend;

-- ============================================
-- FIN DU SCRIPT
-- ============================================

-- Pour vérifier que tout est OK :
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
-- \d utilisateurs
-- \d templates
-- \d keyv
