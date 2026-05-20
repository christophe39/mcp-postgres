-- ========================================
-- CORRECTION : Tunnel SSH accessible via gateway 10.0.1.1
-- Date: 2026-05-19
-- ========================================
-- Problème : localhost:5433 ne fonctionne pas depuis les containers Docker
-- Solution : Utiliser l'IP du gateway Docker (10.0.1.1:5433)
-- ========================================

-- Corriger les 3 sources CaloCalc (OVH via tunnel)
-- Remplacer localhost par 10.0.1.1

UPDATE nc_sources_v2
SET config = json_replace(config, '$.connection.host', '10.0.1.1')
WHERE alias IN ('Calocalc', 'Calocalc_inscription', 'Calocalc_native')
AND json_extract(config, '$.connection.host') = 'localhost';

-- Vérification
SELECT
    alias,
    json_extract(config, '$.connection.host') as host,
    json_extract(config, '$.connection.port') as port,
    json_extract(config, '$.connection.user') as user,
    json_extract(config, '$.connection.database') as database
FROM nc_sources_v2
WHERE alias IN ('Calocalc', 'Calocalc_inscription', 'Calocalc_native')
ORDER BY alias;
