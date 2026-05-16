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
    available_endpoints: ['/auth', '/health', '/test']
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
