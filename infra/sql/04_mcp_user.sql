-- ============================================
-- Script SQL : Création user MCP Excalidraw
-- Base : excalidraw_storage
-- Auteur : Claude Code + Christophe Martin
-- Date : 16 mai 2026
-- ============================================
--
-- Objectif : Créer un utilisateur PostgreSQL DÉDIÉ au MCP Excalidraw
--            avec des droits strictement minimaux (moindre privilège)
--
-- Principe de sécurité :
-- - Ne PAS réutiliser excalidraw_backend (qui a ALL PRIVILEGES)
-- - User isolé, droits granulaires, audit possible
-- - Aucun droit DDL (CREATE, ALTER, DROP)
-- - Aucun accès aux autres bases
--
-- ============================================

-- 1. Créer l'utilisateur mcp_excalidraw
-- ======================================
-- ⚠️ REMPLACER <PASSWORD> par un mot de passe fort (généré aléatoirement)
-- Exemple génération : openssl rand -base64 32

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_user WHERE usename = 'mcp_excalidraw'
  ) THEN
    -- ⚠️ MODIFIER LE MOT DE PASSE ICI
    CREATE USER mcp_excalidraw WITH PASSWORD '<PASSWORD>';
    RAISE NOTICE 'User mcp_excalidraw créé avec succès';
  ELSE
    RAISE NOTICE 'User mcp_excalidraw existe déjà';
  END IF;
END $$;

-- 2. Révoquer tous les droits par défaut (principe du moindre privilège)
-- =======================================================================
REVOKE ALL PRIVILEGES ON DATABASE excalidraw_storage FROM mcp_excalidraw;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM mcp_excalidraw;

-- 3. Donner USAGE sur le schéma public (requis pour accéder aux tables)
-- ======================================================================
GRANT USAGE ON SCHEMA public TO mcp_excalidraw;

-- 4. Droits sur la table keyv
-- ===========================
-- SELECT : lire les scènes existantes
-- INSERT : créer de nouvelles scènes
-- UPDATE : modifier des scènes (version++, metadata)
-- DELETE : supprimer des scènes (droit à l'oubli RGPD)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE keyv TO mcp_excalidraw;

-- 5. Droits sur la table templates
-- =================================
-- SELECT uniquement : lire les templates pour la génération
-- Pas d'INSERT/UPDATE/DELETE (les templates sont gérés par l'admin via NocoDB)
GRANT SELECT ON TABLE templates TO mcp_excalidraw;

-- 6. Droits sur la table utilisateurs
-- ====================================
-- SELECT uniquement : résoudre created_by pour traçabilité
-- Pas d'INSERT/UPDATE/DELETE (les users sont gérés par l'admin)
GRANT SELECT ON TABLE utilisateurs TO mcp_excalidraw;

-- 7. Droits sur la vue scenes_with_user
-- ======================================
-- SELECT : requêtes enrichies avec infos utilisateur/template
GRANT SELECT ON scenes_with_user TO mcp_excalidraw;

-- 8. Permissions par défaut pour les futures tables (par sécurité)
-- =================================================================
-- Si de nouvelles tables sont créées, mcp_excalidraw n'aura AUCUN droit par défaut
-- (contrairement à excalidraw_backend qui pourrait hériter de ALL PRIVILEGES)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE ALL ON TABLES FROM mcp_excalidraw;

-- 9. Pas de droits sur les séquences
-- ===================================
-- Le MCP ne crée pas de nouveaux users/templates, donc pas besoin d'accès aux séquences
-- (excalidraw_backend garde USAGE, SELECT sur les séquences pour INSERT dans utilisateurs/templates)

-- 10. Pas de droits superuser
-- ============================
-- Vérifier que le user n'a PAS de droits élevés
ALTER USER mcp_excalidraw WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- 11. Connexion limitée (défense en profondeur)
-- ==============================================
-- Limite le nombre de connexions simultanées (sécurité anti-abuse)
ALTER USER mcp_excalidraw CONNECTION LIMIT 10;

-- 12. Résumé des droits accordés
-- ===============================
-- Table keyv :          SELECT, INSERT, UPDATE, DELETE
-- Table templates :     SELECT
-- Table utilisateurs :  SELECT
-- Vue scenes_with_user: SELECT
-- Schéma public :       USAGE
-- Séquences :           AUCUN droit
-- DDL (CREATE, ALTER) : AUCUN droit
-- Autres bases :        AUCUN accès

-- ============================================
-- VÉRIFICATION DES PERMISSIONS
-- ============================================

-- Lister les droits du user mcp_excalidraw
DO $$
DECLARE
  privileges TEXT;
BEGIN
  RAISE NOTICE '=== DROITS DU USER mcp_excalidraw ===';

  -- Droits sur keyv
  SELECT string_agg(privilege_type, ', ')
  INTO privileges
  FROM information_schema.role_table_grants
  WHERE grantee = 'mcp_excalidraw' AND table_name = 'keyv';

  RAISE NOTICE 'keyv: %', COALESCE(privileges, 'AUCUN');

  -- Droits sur templates
  SELECT string_agg(privilege_type, ', ')
  INTO privileges
  FROM information_schema.role_table_grants
  WHERE grantee = 'mcp_excalidraw' AND table_name = 'templates';

  RAISE NOTICE 'templates: %', COALESCE(privileges, 'AUCUN');

  -- Droits sur utilisateurs
  SELECT string_agg(privilege_type, ', ')
  INTO privileges
  FROM information_schema.role_table_grants
  WHERE grantee = 'mcp_excalidraw' AND table_name = 'utilisateurs';

  RAISE NOTICE 'utilisateurs: %', COALESCE(privileges, 'AUCUN');

  RAISE NOTICE '=====================================';
END $$;

-- ============================================
-- COMMANDES DE TEST (ne pas exécuter dans ce script)
-- ============================================

-- Tester la connexion avec le nouveau user :
-- docker exec -it pk4s888o4wkc8ogokg0sg840 psql -U mcp_excalidraw -d excalidraw_storage

-- Tester que le user NE PEUT PAS faire de DDL (doit échouer) :
-- CREATE TABLE test_forbidden (id INT); -- Doit renvoyer une erreur "permission denied"

-- Tester que le user PEUT lire keyv :
-- SELECT COUNT(*) FROM keyv WHERE key LIKE 'SCENES:%';

-- Tester que le user PEUT lire templates :
-- SELECT id, nom, categorie FROM templates;

-- Tester que le user NE PEUT PAS modifier templates (doit échouer) :
-- UPDATE templates SET nom = 'test' WHERE id = 1; -- Doit renvoyer une erreur

-- Tester que le user PEUT créer/modifier/supprimer dans keyv :
-- INSERT INTO keyv (key, value) VALUES ('TEST:123', '{"test": true}');
-- UPDATE keyv SET value = '{"test": false}' WHERE key = 'TEST:123';
-- DELETE FROM keyv WHERE key = 'TEST:123';

-- ============================================
-- FIN DU SCRIPT
-- ============================================
