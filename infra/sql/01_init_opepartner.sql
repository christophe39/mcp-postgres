-- ============================================================================
-- Script d'initialisation de la base OPEPARTNER
-- ============================================================================
-- Projet : OPEPARTNER Stack (Excalidraw + AFFiNE + NocoDB)
-- Auteur : Christophe Martin (AGNI Consult)
-- Date : 2026-05-15
-- Container cible : pk4s888o4wkc8ogokg0sg840 (postgres:17-alpine)
-- User : postgres
-- Database : opepartner
-- ============================================================================

-- Extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Pour recherche full-text optimisée

-- ============================================================================
-- TABLE 1 : Clients
-- ============================================================================
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom_entreprise VARCHAR(255) NOT NULL,
    forme_juridique VARCHAR(50), -- SASU, SAS, SARL, etc.
    siret VARCHAR(14) UNIQUE,
    secteur_activite VARCHAR(255),
    effectif_approx INT,
    ca_annuel_approx DECIMAL(15,2),
    adresse_siege TEXT,
    ville VARCHAR(100),
    code_postal VARCHAR(10),
    pays VARCHAR(100) DEFAULT 'France',
    site_web VARCHAR(255),
    statut VARCHAR(50) DEFAULT 'actif' CHECK (statut IN ('prospect', 'actif', 'inactif', 'archive')),
    notes_internes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clients_nom ON clients(nom_entreprise);
CREATE INDEX idx_clients_statut ON clients(statut);
CREATE INDEX idx_clients_siret ON clients(siret);

-- ============================================================================
-- TABLE 2 : Contacts
-- ============================================================================
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    prenom VARCHAR(100),
    nom VARCHAR(100) NOT NULL,
    fonction VARCHAR(100),
    email VARCHAR(255),
    telephone VARCHAR(20),
    mobile VARCHAR(20),
    linkedin_url VARCHAR(255),
    role_dans_mission VARCHAR(100), -- Décideur, Opérationnel, Sponsor, etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contacts_client ON contacts(client_id);
CREATE INDEX idx_contacts_email ON contacts(email);

-- ============================================================================
-- TABLE 3 : Référentiel_modèles
-- ============================================================================
CREATE TABLE referentiel_modeles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom_modele VARCHAR(255) NOT NULL UNIQUE,
    categorie VARCHAR(100), -- Stratégie, Marketing, Opérations, etc.
    description TEXT,
    template_excalidraw_url VARCHAR(500),
    template_affine_url VARCHAR(500),
    tags TEXT[], -- Array PostgreSQL pour tags multiples
    actif BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_referentiel_categorie ON referentiel_modeles(categorie);
CREATE INDEX idx_referentiel_tags ON referentiel_modeles USING GIN(tags);

-- ============================================================================
-- TABLE 4 : Missions
-- ============================================================================
CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    titre_mission VARCHAR(255) NOT NULL,
    contexte TEXT,
    objectifs TEXT,
    perimetre TEXT,
    date_debut DATE,
    date_fin_prevue DATE,
    date_fin_reelle DATE,
    statut VARCHAR(50) DEFAULT 'en_preparation' CHECK (statut IN ('en_preparation', 'en_cours', 'en_pause', 'terminee', 'annulee')),
    budget_prevu DECIMAL(15,2),
    budget_consomme DECIMAL(15,2) DEFAULT 0,
    contact_principal_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    notes_internes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_missions_client ON missions(client_id);
CREATE INDEX idx_missions_statut ON missions(statut);
CREATE INDEX idx_missions_dates ON missions(date_debut, date_fin_prevue);

-- ============================================================================
-- TABLE 5 : Ateliers
-- ============================================================================
CREATE TABLE ateliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    titre_atelier VARCHAR(255) NOT NULL,
    date_atelier DATE,
    duree_minutes INT,
    lieu VARCHAR(255),
    participants TEXT[], -- Array des noms/rôles participants
    objectifs TEXT,
    compte_rendu_url VARCHAR(500),
    affine_doc_id VARCHAR(100),
    statut VARCHAR(50) DEFAULT 'planifie' CHECK (statut IN ('planifie', 'realise', 'annule')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ateliers_mission ON ateliers(mission_id);
CREATE INDEX idx_ateliers_date ON ateliers(date_atelier);

-- ============================================================================
-- TABLE 6 : Livrables
-- ============================================================================
CREATE TABLE livrables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    modele_id UUID REFERENCES referentiel_modeles(id) ON DELETE SET NULL,
    titre_livrable VARCHAR(255) NOT NULL,
    type_livrable VARCHAR(100), -- Rapport, Présentation, Schéma, Plan d'action, etc.
    date_prevue DATE,
    date_livraison DATE,
    statut VARCHAR(50) DEFAULT 'a_faire' CHECK (statut IN ('a_faire', 'en_cours', 'en_validation', 'valide', 'livre')),
    version VARCHAR(20) DEFAULT '1.0',
    url_document VARCHAR(500),
    affine_doc_id VARCHAR(100),
    excalidraw_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_livrables_mission ON livrables(mission_id);
CREATE INDEX idx_livrables_modele ON livrables(modele_id);
CREATE INDEX idx_livrables_statut ON livrables(statut);

-- ============================================================================
-- TABLE 7 : Actions
-- ============================================================================
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    titre_action VARCHAR(255) NOT NULL,
    description TEXT,
    responsable VARCHAR(100),
    echeance DATE,
    priorite VARCHAR(20) DEFAULT 'moyenne' CHECK (priorite IN ('faible', 'moyenne', 'haute', 'critique')),
    statut VARCHAR(50) DEFAULT 'a_faire' CHECK (statut IN ('a_faire', 'en_cours', 'bloquee', 'terminee', 'annulee')),
    date_cloture DATE,
    resultat TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_actions_mission ON actions(mission_id);
CREATE INDEX idx_actions_statut ON actions(statut);
CREATE INDEX idx_actions_echeance ON actions(echeance);
CREATE INDEX idx_actions_priorite ON actions(priorite);

-- ============================================================================
-- TABLE 8 : Comptes_rendus
-- ============================================================================
CREATE TABLE comptes_rendus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    titre VARCHAR(255) NOT NULL,
    date_reunion DATE NOT NULL,
    participants TEXT[],
    ordre_du_jour TEXT,
    decisions TEXT,
    actions_definies TEXT,
    prochaine_reunion DATE,
    affine_doc_id VARCHAR(100),
    url_document VARCHAR(500),
    redacteur VARCHAR(100),
    statut VARCHAR(50) DEFAULT 'brouillon' CHECK (statut IN ('brouillon', 'diffuse', 'archive')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cr_mission ON comptes_rendus(mission_id);
CREATE INDEX idx_cr_date ON comptes_rendus(date_reunion);

-- ============================================================================
-- TABLE 9 : Business_Model_Canvas
-- ============================================================================
CREATE TABLE business_model_canvas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'BMC_visuel',
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    -- Contenu des 9 blocs BMC (JSONB pour flexibilité)
    partenaires_cles JSONB,
    activites_cles JSONB,
    ressources_cles JSONB,
    propositions_valeur JSONB,
    relations_clients JSONB,
    canaux_distribution JSONB,
    segments_clients JSONB,
    structure_couts JSONB,
    sources_revenus JSONB,

    -- URLs et références
    html_url VARCHAR(500),
    affine_url VARCHAR(500),
    excalidraw_url VARCHAR(500),
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bmc_mission ON business_model_canvas(mission_id);
CREATE INDEX idx_bmc_client ON business_model_canvas(client_id);
CREATE INDEX idx_bmc_status ON business_model_canvas(status);

-- ============================================================================
-- TABLE 10 : SWOT
-- ============================================================================
CREATE TABLE swot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'SWOT',
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    -- Contenu des 4 quadrants SWOT
    forces JSONB,
    faiblesses JSONB,
    opportunites JSONB,
    menaces JSONB,

    -- URLs et références
    html_url VARCHAR(500),
    affine_url VARCHAR(500),
    excalidraw_url VARCHAR(500),
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_swot_mission ON swot(mission_id);
CREATE INDEX idx_swot_client ON swot(client_id);
CREATE INDEX idx_swot_status ON swot(status);

-- ============================================================================
-- TABLE 11 : PESTEL
-- ============================================================================
CREATE TABLE pestel (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'PESTEL',
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    -- Contenu des 6 dimensions PESTEL
    politique JSONB,
    economique JSONB,
    socioculturel JSONB,
    technologique JSONB,
    environnemental JSONB,
    legal JSONB,

    -- URLs et références
    html_url VARCHAR(500),
    affine_url VARCHAR(500),
    excalidraw_url VARCHAR(500),
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pestel_mission ON pestel(mission_id);
CREATE INDEX idx_pestel_client ON pestel(client_id);
CREATE INDEX idx_pestel_status ON pestel(status);

-- ============================================================================
-- TABLE 12 : Value_Proposition_Canvas
-- ============================================================================
CREATE TABLE value_proposition_canvas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'VPC',
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    -- Profil client (3 éléments)
    taches_clients JSONB,
    problemes_clients JSONB,
    gains_clients JSONB,

    -- Proposition de valeur (3 éléments)
    produits_services JSONB,
    soulageurs_problemes JSONB,
    createurs_gains JSONB,

    -- URLs et références
    html_url VARCHAR(500),
    affine_url VARCHAR(500),
    excalidraw_url VARCHAR(500),
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vpc_mission ON value_proposition_canvas(mission_id);
CREATE INDEX idx_vpc_client ON value_proposition_canvas(client_id);
CREATE INDEX idx_vpc_status ON value_proposition_canvas(status);

-- ============================================================================
-- TABLE 13 : Plan_90_jours
-- ============================================================================
CREATE TABLE plan_90_jours (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    document_type VARCHAR(50) DEFAULT 'Plan_90j',
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,

    -- Structuration par mois (JSONB pour flexibilité)
    mois_1_objectifs JSONB,
    mois_1_actions JSONB,
    mois_2_objectifs JSONB,
    mois_2_actions JSONB,
    mois_3_objectifs JSONB,
    mois_3_actions JSONB,

    indicateurs_suivi JSONB,
    ressources_necessaires JSONB,

    -- URLs et références
    html_url VARCHAR(500),
    affine_url VARCHAR(500),
    excalidraw_url VARCHAR(500),
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plan90_mission ON plan_90_jours(mission_id);
CREATE INDEX idx_plan90_client ON plan_90_jours(client_id);
CREATE INDEX idx_plan90_dates ON plan_90_jours(date_debut, date_fin);

-- ============================================================================
-- TABLE 14 : Schemas_Excalidraw (NOUVEAU - pour MCP custom)
-- ============================================================================
CREATE TABLE schemas_excalidraw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,

    -- Métadonnées documentaires
    document_type VARCHAR(50) DEFAULT 'Schéma', -- BMC_visuel, PESTEL, SWOT, Organigramme, Technique, etc.
    document_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'validated', 'archived')),
    version VARCHAR(20) DEFAULT '1.0',
    owner VARCHAR(100),

    -- Spécifique Excalidraw
    excalidraw_id VARCHAR(255) UNIQUE NOT NULL, -- ID unique du schéma dans Excalidraw
    edit_url VARCHAR(500), -- URL d'édition complète
    preview_url VARCHAR(500), -- URL de preview (image PNG/SVG)
    scene_json JSONB, -- Stockage du JSON Excalidraw complet (optionnel, si backup souhaité)

    -- Intégration AFFiNE
    affine_doc_id VARCHAR(100), -- ID du doc AFFiNE associé
    affine_url VARCHAR(500),

    -- Sécurité et organisation
    confidentiel BOOLEAN DEFAULT true,
    tags TEXT[],

    -- Autres
    html_url VARCHAR(500),
    excalidraw_url VARCHAR(500), -- Alias vers edit_url pour cohérence avec autres tables
    notes_internal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schemas_mission ON schemas_excalidraw(mission_id);
CREATE INDEX idx_schemas_client ON schemas_excalidraw(client_id);
CREATE INDEX idx_schemas_excalidraw_id ON schemas_excalidraw(excalidraw_id);
CREATE INDEX idx_schemas_type ON schemas_excalidraw(document_type);
CREATE INDEX idx_schemas_tags ON schemas_excalidraw USING GIN(tags);
CREATE INDEX idx_schemas_confidentiel ON schemas_excalidraw(confidentiel);

-- ============================================================================
-- TRIGGERS : Mise à jour automatique de updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_referentiel_updated_at BEFORE UPDATE ON referentiel_modeles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_missions_updated_at BEFORE UPDATE ON missions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ateliers_updated_at BEFORE UPDATE ON ateliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_livrables_updated_at BEFORE UPDATE ON livrables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_actions_updated_at BEFORE UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cr_updated_at BEFORE UPDATE ON comptes_rendus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bmc_updated_at BEFORE UPDATE ON business_model_canvas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_swot_updated_at BEFORE UPDATE ON swot
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pestel_updated_at BEFORE UPDATE ON pestel
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vpc_updated_at BEFORE UPDATE ON value_proposition_canvas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plan90_updated_at BEFORE UPDATE ON plan_90_jours
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schemas_updated_at BEFORE UPDATE ON schemas_excalidraw
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DONNÉES DE RÉFÉRENCE : Modèles standards
-- ============================================================================
INSERT INTO referentiel_modeles (nom_modele, categorie, description, tags) VALUES
    ('Business Model Canvas', 'Stratégie', 'Modèle des 9 blocs pour décrire le modèle économique', ARRAY['strategie', 'business-model', 'canvas']),
    ('SWOT Analysis', 'Stratégie', 'Forces, Faiblesses, Opportunités, Menaces', ARRAY['strategie', 'diagnostic']),
    ('PESTEL Analysis', 'Stratégie', 'Analyse macro-environnement (6 dimensions)', ARRAY['strategie', 'environnement', 'prospective']),
    ('Value Proposition Canvas', 'Marketing', 'Adéquation Produit-Marché (VPC)', ARRAY['marketing', 'proposition-valeur']),
    ('Plan 90 jours', 'Opérations', 'Roadmap trimestrielle avec jalons', ARRAY['operations', 'planification', 'roadmap']),
    ('Organigramme', 'RH', 'Structure organisationnelle', ARRAY['rh', 'organisation']),
    ('Carte de parcours client', 'Marketing', 'Customer Journey Map', ARRAY['marketing', 'experience-client']),
    ('Matrice BCG', 'Stratégie', 'Portfolio produits (Stars, Vaches à lait, Dilemmes, Poids morts)', ARRAY['strategie', 'portfolio']);

-- ============================================================================
-- VUES UTILES
-- ============================================================================

-- Vue : Tous les documents d'une mission (agrégation)
CREATE OR REPLACE VIEW v_mission_documents AS
SELECT
    m.id AS mission_id,
    m.titre_mission,
    c.nom_entreprise AS client,
    'BMC' AS type_document,
    bmc.document_title AS titre,
    bmc.status,
    bmc.version,
    bmc.affine_url,
    bmc.excalidraw_url,
    bmc.created_at,
    bmc.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN business_model_canvas bmc ON bmc.mission_id = m.id

UNION ALL

SELECT
    m.id, m.titre_mission, c.nom_entreprise,
    'SWOT', sw.document_title, sw.status, sw.version,
    sw.affine_url, sw.excalidraw_url, sw.created_at, sw.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN swot sw ON sw.mission_id = m.id

UNION ALL

SELECT
    m.id, m.titre_mission, c.nom_entreprise,
    'PESTEL', p.document_title, p.status, p.version,
    p.affine_url, p.excalidraw_url, p.created_at, p.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN pestel p ON p.mission_id = m.id

UNION ALL

SELECT
    m.id, m.titre_mission, c.nom_entreprise,
    'VPC', vpc.document_title, vpc.status, vpc.version,
    vpc.affine_url, vpc.excalidraw_url, vpc.created_at, vpc.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN value_proposition_canvas vpc ON vpc.mission_id = m.id

UNION ALL

SELECT
    m.id, m.titre_mission, c.nom_entreprise,
    'Plan 90j', p90.document_title, p90.status, p90.version,
    p90.affine_url, p90.excalidraw_url, p90.created_at, p90.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN plan_90_jours p90 ON p90.mission_id = m.id

UNION ALL

SELECT
    m.id, m.titre_mission, c.nom_entreprise,
    se.document_type, se.document_title, se.status, se.version,
    se.affine_url, se.excalidraw_url, se.created_at, se.validated_at
FROM missions m
JOIN clients c ON m.client_id = c.id
LEFT JOIN schemas_excalidraw se ON se.mission_id = m.id;

-- Vue : Dashboard missions (KPIs)
CREATE OR REPLACE VIEW v_dashboard_missions AS
SELECT
    m.id,
    m.titre_mission,
    c.nom_entreprise AS client,
    m.statut,
    m.date_debut,
    m.date_fin_prevue,
    m.budget_prevu,
    m.budget_consomme,
    ROUND((m.budget_consomme / NULLIF(m.budget_prevu, 0)) * 100, 2) AS taux_consommation_budget,
    COUNT(DISTINCT a.id) AS nb_actions,
    COUNT(DISTINCT l.id) AS nb_livrables,
    COUNT(DISTINCT at.id) AS nb_ateliers,
    COUNT(DISTINCT se.id) AS nb_schemas
FROM missions m
LEFT JOIN clients c ON m.client_id = c.id
LEFT JOIN actions a ON a.mission_id = m.id
LEFT JOIN livrables l ON l.mission_id = m.id
LEFT JOIN ateliers at ON at.mission_id = m.id
LEFT JOIN schemas_excalidraw se ON se.mission_id = m.id
GROUP BY m.id, c.nom_entreprise;

-- ============================================================================
-- FIN DU SCRIPT
-- ============================================================================
-- Total : 14 tables créées
-- Extensions : uuid-ossp, pg_trgm
-- Triggers : update_updated_at sur toutes les tables
-- Données de référence : 8 modèles standards
-- Vues : v_mission_documents, v_dashboard_missions
-- ============================================================================
