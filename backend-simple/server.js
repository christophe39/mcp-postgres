const express = require('express');
const { Pool } = require('pg');

const app = express();
const port = process.env.PORT || 8080;

// Configuration PostgreSQL
const pool = new Pool({
  connectionString: process.env.STORAGE_URI
});

// CORS en premier
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.sendStatus(204);
  }

  next();
});

// Parser RAW pour TOUT
app.use(express.raw({ type: '*/*', limit: '10mb' }));

// Générer un ID aléatoire
function generateId() {
  const length = parseInt(process.env.ID_LENGTH) || 12;
  return Math.random().toString().slice(2, 2 + length);
}

// POST - Créer une scène
app.post('/api/v2/scenes', async (req, res) => {
  try {
    const id = generateId();

    // Le body est un Buffer, le convertir en string
    const rawData = req.body ? req.body.toString('utf-8') : '';

    await pool.query(
      'INSERT INTO keyv (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2',
      [`SCENES:${id}`, JSON.stringify({ value: rawData, expires: null })]
    );

    res.json({ id });
  } catch (error) {
    console.error('Error creating scene:', error);
    res.status(500).json({ error: 'Failed to create scene' });
  }
});

// GET - Récupérer une scène
app.get('/api/v2/scenes/:id', async (req, res) => {
  try {
    const { id } = req.params;

    const result = await pool.query(
      'SELECT value FROM keyv WHERE key = $1',
      [`SCENES:${id}`]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Scene not found' });
    }

    const data = JSON.parse(result.rows[0].value);

    // Retourner les données brutes
    res.setHeader('Content-Type', 'application/octet-stream');
    res.send(data.value);
  } catch (error) {
    console.error('Error fetching scene:', error);
    res.status(500).json({ error: 'Failed to fetch scene' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.send('OK');
});

app.listen(port, () => {
  console.log(`Excalidraw backend listening on port ${port}`);
});
