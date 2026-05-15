-- =====================================================
-- Script d'initialisation : excalidraw_storage
-- =====================================================
-- Base dédiée au stockage des scènes Excalidraw
-- Utilisée par le service excalidraw-storage-backend
-- Container Postgres : pk4s888o4wkc8ogokg0sg840
-- User applicatif : excalidraw_backend
-- =====================================================

-- Table principale : stockage des scènes Excalidraw
CREATE TABLE IF NOT EXISTS excalidraw_scenes (
  id VARCHAR(50) PRIMARY KEY,
  json_data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour les requêtes par date (optionnel, utile pour le MCP list_scenes)
CREATE INDEX IF NOT EXISTS idx_excalidraw_scenes_created_at ON excalidraw_scenes(created_at DESC);

-- Fonction trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_excalidraw_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur UPDATE
CREATE TRIGGER trg_excalidraw_scenes_updated_at
BEFORE UPDATE ON excalidraw_scenes
FOR EACH ROW
EXECUTE FUNCTION update_excalidraw_updated_at();

-- Donner les droits au user excalidraw_backend sur la table
GRANT ALL PRIVILEGES ON TABLE excalidraw_scenes TO excalidraw_backend;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO excalidraw_backend;

-- Log de fin
DO $$
BEGIN
  RAISE NOTICE 'Table excalidraw_scenes créée avec succès';
END $$;
