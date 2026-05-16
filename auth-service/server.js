const express = require('express');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Pool de connexion PostgreSQL
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_SSL === 'true' ? { rejectUnauthorized: false } : false
});

// Test de connexion au démarrage
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('❌ Erreur connexion PostgreSQL:', err);
    process.exit(1);
  }
  console.log('✅ Connexion PostgreSQL OK:', res.rows[0].now);
});

// Middleware de logging
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path} - IP: ${req.ip}`);
  next();
});

// Middleware pour parser le JSON (pour l'endpoint admin)
app.use(express.json());

// Parse BasicAuth header
function parseBasicAuth(authHeader) {
  if (!authHeader || !authHeader.startsWith('Basic ')) {
    return null;
  }

  try {
    const base64Credentials = authHeader.slice(6); // Enlever "Basic "
    const credentials = Buffer.from(base64Credentials, 'base64').toString('utf-8');
    const [email, password] = credentials.split(':');
    return { email, password };
  } catch (error) {
    console.error('Erreur parsing BasicAuth:', error);
    return null;
  }
}

// Endpoint principal pour Traefik ForwardAuth
app.get('/auth', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      console.log('❌ Auth échouée : pas de header Authorization');
      return res.status(401).set('WWW-Authenticate', 'Basic realm="Excalidraw OPEPARTNER"').send('Authentification requise');
    }

    const credentials = parseBasicAuth(authHeader);

    if (!credentials) {
      console.log('❌ Auth échouée : format BasicAuth invalide');
      return res.status(401).set('WWW-Authenticate', 'Basic realm="Excalidraw OPEPARTNER"').send('Format authentification invalide');
    }

    const { email, password } = credentials;

    // Requête SQL pour récupérer l'utilisateur
    const result = await pool.query(
      'SELECT id, email, password_hash, nom, actif FROM utilisateurs WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      console.log(`❌ Auth échouée : utilisateur ${email} non trouvé`);
      return res.status(401).set('WWW-Authenticate', 'Basic realm="Excalidraw OPEPARTNER"').send('Email ou mot de passe incorrect');
    }

    const user = result.rows[0];

    if (!user.actif) {
      console.log(`❌ Auth échouée : utilisateur ${email} désactivé`);
      return res.status(401).set('WWW-Authenticate', 'Basic realm="Excalidraw OPEPARTNER"').send('Compte désactivé');
    }

    // Vérifier le mot de passe
    const passwordMatch = await bcrypt.compare(password, user.password_hash);

    if (!passwordMatch) {
      console.log(`❌ Auth échouée : mot de passe incorrect pour ${email}`);
      return res.status(401).set('WWW-Authenticate', 'Basic realm="Excalidraw OPEPARTNER"').send('Email ou mot de passe incorrect');
    }

    // Succès ! Mettre à jour last_login
    await pool.query(
      'UPDATE utilisateurs SET last_login = NOW() WHERE id = $1',
      [user.id]
    );

    console.log(`✅ Auth réussie : ${user.email} (ID: ${user.id})`);

    // Retourner les headers pour Traefik
    res.status(200)
      .set('X-Forwarded-User', user.id.toString())
      .set('X-Forwarded-Email', user.email)
      .set('X-Forwarded-Name', user.nom || '')
      .send('OK');

  } catch (error) {
    console.error('❌ Erreur interne:', error);
    res.status(500).send('Erreur interne du serveur');
  }
});

// Endpoint admin pour créer un utilisateur (protégé par token)
app.post('/admin/create-user', async (req, res) => {
  try {
    // Vérifier le token admin
    const authHeader = req.headers.authorization;
    const adminToken = process.env.ADMIN_TOKEN;

    if (!adminToken) {
      console.error('❌ ADMIN_TOKEN non configuré dans les variables d\'environnement');
      return res.status(500).json({ error: 'Configuration serveur incorrecte' });
    }

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Token d\'authentification requis' });
    }

    const token = authHeader.slice(7); // Enlever "Bearer "

    if (token !== adminToken) {
      console.log('❌ Tentative d\'accès admin avec token invalide');
      return res.status(403).json({ error: 'Token invalide' });
    }

    // Récupérer les données du body
    const { email, password, nom } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email et mot de passe requis' });
    }

    // Vérifier que l'email n'existe pas déjà
    const existingUser = await pool.query(
      'SELECT id FROM utilisateurs WHERE email = $1',
      [email]
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: 'Cet email existe déjà' });
    }

    // Hasher le mot de passe
    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    // Insérer l'utilisateur
    const result = await pool.query(
      `INSERT INTO utilisateurs (email, password_hash, nom, actif)
       VALUES ($1, $2, $3, true)
       RETURNING id, email, nom, created_at`,
      [email, passwordHash, nom || null]
    );

    const user = result.rows[0];

    console.log(`✅ Utilisateur créé via admin endpoint : ${user.email} (ID: ${user.id})`);

    res.status(201).json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        nom: user.nom,
        created_at: user.created_at
      }
    });

  } catch (error) {
    console.error('❌ Erreur création utilisateur:', error);
    res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// Healthcheck endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'excalidraw-auth-service'
  });
});

// Endpoint pour tester la connexion (à retirer en prod)
app.get('/test', async (req, res) => {
  try {
    const result = await pool.query('SELECT id, email, nom, actif FROM utilisateurs ORDER BY created_at DESC LIMIT 5');
    res.json({
      status: 'ok',
      users_count: result.rows.length,
      users: result.rows
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Endpoint non trouvé',
    available_endpoints: ['/auth', '/health', '/admin/create-user', '/test']
  });
});

// Démarrage du serveur
app.listen(PORT, () => {
  console.log(`🚀 Service d'authentification démarré sur le port ${PORT}`);
  console.log(`📍 Endpoint ForwardAuth: http://localhost:${PORT}/auth`);
  console.log(`💚 Healthcheck: http://localhost:${PORT}/health`);
});

// Gestion arrêt propre
process.on('SIGTERM', () => {
  console.log('SIGTERM reçu, arrêt en cours...');
  pool.end(() => {
    console.log('Pool PostgreSQL fermé');
    process.exit(0);
  });
});
