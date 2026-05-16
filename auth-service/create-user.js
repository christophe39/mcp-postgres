/**
 * Script pour créer un utilisateur dans la table utilisateurs
 * Usage: node create-user.js <email> <password> [nom]
 */

const bcrypt = require('bcrypt');
const { Pool } = require('pg');
require('dotenv').config();

const args = process.argv.slice(2);

if (args.length < 2) {
  console.error('Usage: node create-user.js <email> <password> [nom]');
  console.error('Exemple: node create-user.js cmartin@agniconsult.fr monPassword123 "Christophe Martin"');
  process.exit(1);
}

const [email, password, nom] = args;

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.DATABASE_SSL === 'true' ? { rejectUnauthorized: false } : false
  });

  try {
    console.log('🔐 Hashing du mot de passe...');
    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    console.log(`📧 Création de l'utilisateur : ${email}`);

    const result = await pool.query(
      `INSERT INTO utilisateurs (email, password_hash, nom, actif)
       VALUES ($1, $2, $3, true)
       RETURNING id, email, nom, created_at`,
      [email, passwordHash, nom || null]
    );

    const user = result.rows[0];

    console.log('✅ Utilisateur créé avec succès !');
    console.log('ID:', user.id);
    console.log('Email:', user.email);
    console.log('Nom:', user.nom);
    console.log('Créé le:', user.created_at);

    // Test immédiat du mot de passe
    console.log('\n🔍 Test de vérification du mot de passe...');
    const isMatch = await bcrypt.compare(password, passwordHash);
    console.log(isMatch ? '✅ Vérification OK' : '❌ Erreur de vérification');

  } catch (error) {
    if (error.code === '23505') {
      console.error('❌ Erreur : Cet email existe déjà dans la base');
    } else {
      console.error('❌ Erreur:', error.message);
    }
    process.exit(1);
  } finally {
    await pool.end();
  }
})();
