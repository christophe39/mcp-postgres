const express = require('express');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const session = require('express-session');
const pgSession = require('connect-pg-simple')(session);
const cookieParser = require('cookie-parser');
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

// Créer la table sessions si elle n'existe pas
pool.query(`
  CREATE TABLE IF NOT EXISTS "session" (
    "sid" varchar NOT NULL COLLATE "default",
    "sess" json NOT NULL,
    "expire" timestamp(6) NOT NULL,
    CONSTRAINT "session_pkey" PRIMARY KEY ("sid")
  );
  CREATE INDEX IF NOT EXISTS "IDX_session_expire" ON "session" ("expire");
`, (err) => {
  if (err) {
    console.error('⚠️  Erreur création table session:', err);
  } else {
    console.log('✅ Table session prête');
  }
});

// Rate limiting en mémoire (IP → {count, blockedUntil})
const loginAttempts = new Map();

function checkRateLimit(ip) {
  const attempt = loginAttempts.get(ip);

  if (attempt?.blockedUntil && Date.now() < attempt.blockedUntil) {
    const remainingMin = Math.ceil((attempt.blockedUntil - Date.now()) / 60000);
    return { blocked: true, remainingMin };
  }

  return { blocked: false };
}

function recordFailure(ip) {
  const attempt = loginAttempts.get(ip) || { count: 0, firstAttempt: Date.now() };
  attempt.count++;

  if (attempt.count >= 3) {
    attempt.blockedUntil = Date.now() + (5 * 60 * 1000); // 5 minutes
    attempt.count = 0;
    console.log(`🚫 IP ${ip} bloquée pour 5 minutes (3 tentatives échouées)`);
  }

  loginAttempts.set(ip, attempt);
}

function recordSuccess(ip) {
  loginAttempts.delete(ip); // Reset le compteur
}

// Middleware de logging
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path} - IP: ${req.ip}`);
  next();
});

// Middleware pour parser le body et cookies
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());

// Configuration de session
app.use(session({
  store: new pgSession({
    pool: pool,
    tableName: 'session',
    createTableIfMissing: false // On l'a déjà créée
  }),
  secret: process.env.SESSION_SECRET || 'changeme-in-production',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production', // HTTPS en prod
    httpOnly: true,
    maxAge: 365 * 24 * 60 * 60 * 1000, // 1 an (accès définitif)
    sameSite: 'lax',
    domain: process.env.COOKIE_DOMAIN || undefined
  },
  name: 'excalidraw.sid' // Nom du cookie
}));

// ============================================
// PAGE DE LOGIN (GET /login)
// ============================================
app.get('/login', (req, res) => {
  const error = req.query.error;
  const blocked = req.query.blocked;

  let errorMessage = '';
  if (error === 'credentials') {
    errorMessage = '<div style="color: #e03131; margin-bottom: 16px;">Email ou mot de passe incorrect</div>';
  } else if (error === 'disabled') {
    errorMessage = '<div style="color: #e03131; margin-bottom: 16px;">Compte désactivé</div>';
  } else if (blocked) {
    errorMessage = `<div style="color: #e03131; margin-bottom: 16px;">Trop de tentatives. Réessayez dans ${blocked} minute(s)</div>`;
  }

  res.send(`
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Connexion - Excalidraw</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-container {
          background: white;
          padding: 48px;
          border-radius: 12px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          width: 100%;
          max-width: 420px;
        }
        h1 {
          margin-bottom: 8px;
          color: #1a1a1a;
          font-size: 28px;
          font-weight: 700;
        }
        .subtitle {
          color: #666;
          margin-bottom: 32px;
          font-size: 14px;
        }
        .form-group {
          margin-bottom: 20px;
        }
        label {
          display: block;
          margin-bottom: 8px;
          color: #333;
          font-size: 14px;
          font-weight: 500;
        }
        input {
          width: 100%;
          padding: 14px 16px;
          border: 2px solid #e1e4e8;
          border-radius: 8px;
          font-size: 15px;
          transition: border-color 0.2s;
        }
        input:focus {
          outline: none;
          border-color: #667eea;
        }
        button {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 16px;
          font-weight: 600;
          margin-top: 24px;
          transition: transform 0.2s;
        }
        button:hover {
          transform: translateY(-2px);
        }
        button:active {
          transform: translateY(0);
        }
        .footer {
          margin-top: 24px;
          text-align: center;
          color: #999;
          font-size: 12px;
        }
      </style>
    </head>
    <body>
      <div class="login-container">
        <h1>Excalidraw</h1>
        <div class="subtitle">Connexion sécurisée</div>

        ${errorMessage}

        <form method="POST" action="/login">
          <div class="form-group">
            <label for="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="votre@email.com"
              required
              autocomplete="username"
              autofocus
            >
          </div>

          <div class="form-group">
            <label for="password">Mot de passe</label>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="••••••••"
              required
              autocomplete="current-password"
            >
          </div>

          <button type="submit">Se connecter</button>
        </form>

        <div class="footer">
          © ${new Date().getFullYear()} AGNI Solution
        </div>
      </div>
    </body>
    </html>
  `);
});

// ============================================
// AUTHENTIFICATION (POST /login)
// ============================================
app.post('/login', async (req, res) => {
  try {
    const ip = req.ip || req.connection.remoteAddress;

    // Vérifier rate limit
    const rateLimit = checkRateLimit(ip);
    if (rateLimit.blocked) {
      console.log(`🚫 Tentative de login bloquée pour IP ${ip} (${rateLimit.remainingMin} min restantes)`);
      return res.redirect(`/login?blocked=${rateLimit.remainingMin}`);
    }

    const { email, password } = req.body;

    if (!email || !password) {
      return res.redirect('/login?error=credentials');
    }

    // Requête SQL pour récupérer l'utilisateur
    const result = await pool.query(
      'SELECT id, email, password_hash, nom, actif FROM utilisateurs WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      recordFailure(ip);
      console.log(`❌ Login échoué : utilisateur ${email} non trouvé (IP: ${ip})`);
      return res.redirect('/login?error=credentials');
    }

    const user = result.rows[0];

    if (!user.actif) {
      recordFailure(ip);
      console.log(`❌ Login échoué : utilisateur ${email} désactivé (IP: ${ip})`);
      return res.redirect('/login?error=disabled');
    }

    // Vérifier le mot de passe
    const passwordMatch = await bcrypt.compare(password, user.password_hash);

    if (!passwordMatch) {
      recordFailure(ip);
      console.log(`❌ Login échoué : mot de passe incorrect pour ${email} (IP: ${ip})`);
      return res.redirect('/login?error=credentials');
    }

    // Succès ! Reset rate limit et créer session
    recordSuccess(ip);

    // Mettre à jour last_login
    await pool.query(
      'UPDATE utilisateurs SET last_login = NOW() WHERE id = $1',
      [user.id]
    );

    // Créer la session
    req.session.userId = user.id;
    req.session.userEmail = user.email;
    req.session.userName = user.nom;

    console.log(`✅ Login réussi : ${user.email} (ID: ${user.id}, IP: ${ip})`);

    // Redirection vers la page d'origine ou Excalidraw
    const redirectTo = req.query.redirect || 'https://excalidraw.agnisolution.fr';
    res.redirect(redirectTo);

  } catch (error) {
    console.error('❌ Erreur interne lors du login:', error);
    res.redirect('/login?error=server');
  }
});

// ============================================
// LOGOUT
// ============================================
app.get('/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      console.error('❌ Erreur lors du logout:', err);
    }
    res.clearCookie('excalidraw.sid');
    res.redirect('/login');
  });
});

// ============================================
// ENDPOINT FORWARDAUTH (GET /auth)
// ============================================
app.get('/auth', async (req, res) => {
  try {
    // Vérifier si l'utilisateur a une session active
    if (!req.session.userId) {
      console.log('❌ Auth échouée : pas de session active');

      // Rediriger vers /login avec l'URL d'origine
      const originalUrl = req.headers['x-forwarded-uri'] || '/';
      const host = req.headers['x-forwarded-host'] || 'excalidraw.agnisolution.fr';
      const redirectUrl = `https://exca-auth.agnisolution.fr/login?redirect=https://${host}${originalUrl}`;

      return res.status(302)
        .set('Location', redirectUrl)
        .send();
    }

    // Session valide, vérifier que l'utilisateur existe toujours
    const result = await pool.query(
      'SELECT id, email, nom, actif FROM utilisateurs WHERE id = $1',
      [req.session.userId]
    );

    if (result.rows.length === 0 || !result.rows[0].actif) {
      console.log(`❌ Auth échouée : utilisateur ${req.session.userId} n'existe plus ou désactivé`);
      req.session.destroy();
      return res.status(401).send('Utilisateur invalide');
    }

    const user = result.rows[0];

    console.log(`✅ Auth réussie via session : ${user.email} (ID: ${user.id})`);

    // Retourner les headers pour Traefik
    res.status(200)
      .set('X-Forwarded-User', user.id.toString())
      .set('X-Forwarded-Email', user.email)
      .set('X-Forwarded-Name', user.nom || '')
      .send('OK');

  } catch (error) {
    console.error('❌ Erreur interne /auth:', error);
    res.status(500).send('Erreur interne du serveur');
  }
});

// ============================================
// ENDPOINT ADMIN (création utilisateur)
// ============================================
app.post('/admin/create-user', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    const adminToken = process.env.ADMIN_TOKEN;

    if (!adminToken) {
      console.error('❌ ADMIN_TOKEN non configuré');
      return res.status(500).json({ error: 'Configuration serveur incorrecte' });
    }

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Token d\'authentification requis' });
    }

    const token = authHeader.slice(7);

    if (token !== adminToken) {
      console.log('❌ Tentative d\'accès admin avec token invalide');
      return res.status(403).json({ error: 'Token invalide' });
    }

    const { email, password, nom } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email et mot de passe requis' });
    }

    const existingUser = await pool.query(
      'SELECT id FROM utilisateurs WHERE email = $1',
      [email]
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({ error: 'Cet email existe déjà' });
    }

    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

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

// ============================================
// HEALTHCHECK
// ============================================
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'excalidraw-auth-service',
    version: '2.0.0-with-login-page'
  });
});

// ============================================
// TEST (à retirer en prod)
// ============================================
app.get('/test', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT id, email, nom, actif, last_login FROM utilisateurs ORDER BY created_at DESC LIMIT 5'
    );
    res.json({
      status: 'ok',
      users_count: result.rows.length,
      users: result.rows,
      rate_limit_map_size: loginAttempts.size
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// ============================================
// 404 HANDLER
// ============================================
app.use((req, res) => {
  res.status(404).json({
    error: 'Endpoint non trouvé',
    available_endpoints: ['/login', '/auth', '/logout', '/health', '/admin/create-user', '/test']
  });
});

// ============================================
// DÉMARRAGE
// ============================================
app.listen(PORT, () => {
  console.log(`🚀 Service d'authentification démarré sur le port ${PORT}`);
  console.log(`📍 Login page: http://localhost:${PORT}/login`);
  console.log(`📍 ForwardAuth: http://localhost:${PORT}/auth`);
  console.log(`💚 Healthcheck: http://localhost:${PORT}/health`);
  console.log(`🔒 Rate limiting activé : 3 tentatives max / 5 min`);
});

// ============================================
// ARRÊT PROPRE
// ============================================
process.on('SIGTERM', () => {
  console.log('SIGTERM reçu, arrêt en cours...');
  pool.end(() => {
    console.log('Pool PostgreSQL fermé');
    process.exit(0);
  });
});
