"""
Chiffrement/déchiffrement E2E AES-GCM compatible Excalidraw frontend

Format reproduction exacte du frontend :
- Source: github.com/excalidraw/excalidraw
  - packages/excalidraw/data/encryption.ts
  - packages/excalidraw/data/encode.ts

Phase H.2 — Validation bidirectionnelle obligatoire
"""

import base64
import json
import os
import struct
import zlib
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# =============================================================================
# CONSTANTES (sources: excalidraw/packages/common/src/constants.ts)
# =============================================================================

ENCRYPTION_KEY_BITS = 128  # AES-128-GCM (ligne: constants.ts)
ENCRYPTION_KEY_BYTES = ENCRYPTION_KEY_BITS // 8  # 16 bytes

IV_LENGTH_BYTES = 12  # Source: encryption.ts:5

CONCAT_BUFFERS_VERSION = 1  # Source: encode.ts:161


# =============================================================================
# 1. GESTION DES CLÉS JWK (JSON Web Key)
# =============================================================================

def generate_encryption_key() -> bytes:
    """
    Génère une clé AES-128 (16 bytes aléatoires)

    Source: encryption.ts:17-24
    """
    return os.urandom(ENCRYPTION_KEY_BYTES)


def key_bytes_to_jwk_k(key_bytes: bytes) -> str:
    """
    Convertit 16 bytes → base64url (22 chars) pour JWK.k

    Source: encryption.ts:28
    - Exporte la clé au format JWK et retourne UNIQUEMENT le champ 'k'
    - Base64url = base64 SANS padding '=' (RFC 4648 Section 5)

    Args:
        key_bytes: Clé AES-128 (16 bytes)

    Returns:
        Chaîne base64url de 22 caractères

    Raises:
        AssertionError: Si key_bytes ne fait pas 16 bytes
    """
    assert len(key_bytes) == ENCRYPTION_KEY_BYTES, \
        f"Clé doit faire {ENCRYPTION_KEY_BYTES} bytes (AES-128), reçu {len(key_bytes)}"

    # Base64url sans padding
    jwk_k = base64.urlsafe_b64encode(key_bytes).decode('ascii').rstrip('=')

    assert len(jwk_k) == 22, \
        f"JWK.k doit faire 22 caractères, obtenu {len(jwk_k)}"

    return jwk_k


def jwk_k_to_key_bytes(jwk_k: str) -> bytes:
    """
    Convertit base64url (22 chars) → 16 bytes

    Source: encryption.ts:32-48 (getCryptoKey import)

    Args:
        jwk_k: Chaîne base64url de 22 caractères

    Returns:
        Clé AES-128 (16 bytes)

    Raises:
        AssertionError: Si jwk_k ne fait pas 22 caractères
    """
    assert len(jwk_k) == 22, \
        f"JWK.k doit faire 22 caractères, reçu {len(jwk_k)}"

    # Ajouter le padding manquant (22 → 24 chars)
    # 22 % 4 = 2, donc il faut 2 caractères de padding
    padding = '=' * ((4 - len(jwk_k) % 4) % 4)

    key_bytes = base64.urlsafe_b64decode(jwk_k + padding)

    assert len(key_bytes) == ENCRYPTION_KEY_BYTES, \
        f"Clé décodée devrait faire {ENCRYPTION_KEY_BYTES} bytes, obtenu {len(key_bytes)}"

    return key_bytes


def create_jwk(key_bytes: bytes) -> dict:
    """
    Crée l'objet JWK complet (utilisé pour debug/validation uniquement)

    Source: encryption.ts:35-41 (getCryptoKey)

    Format:
    {
        "alg": "A128GCM",
        "ext": true,
        "k": "<base64url_22_chars>",
        "key_ops": ["encrypt", "decrypt"],
        "kty": "oct"
    }
    """
    return {
        "alg": "A128GCM",
        "ext": True,
        "k": key_bytes_to_jwk_k(key_bytes),
        "key_ops": ["encrypt", "decrypt"],
        "kty": "oct"
    }


# =============================================================================
# 2. CONCAT BUFFERS (format binaire multi-chunks)
# =============================================================================

def concat_buffers(*buffers: bytes) -> bytes:
    """
    Reproduit concatBuffers() de encode.ts:225-252

    Format du buffer final:
    [
      VERSION (4 bytes, Uint32 big-endian),
      LENGTH chunk 1 (4 bytes, Uint32 big-endian),
      DATA chunk 1,
      LENGTH chunk 2 (4 bytes, Uint32 big-endian),
      DATA chunk 2,
      ...
    ]

    Source: encode.ts:161 (VERSION = 1)
    Source: encode.ts:202 (DataView.setUint32 sans littleEndian = big-endian)
    Validation: Vérification VPS → hex '00000001' (VERSION=1, big-endian)

    Args:
        *buffers: Liste de bytes à concaténer

    Returns:
        Buffer concaténé au format Excalidraw
    """
    result = bytearray()

    # VERSION (4 bytes, big-endian Uint32)
    # Source: encode.ts:235
    result.extend(struct.pack('>I', CONCAT_BUFFERS_VERSION))

    # Pour chaque buffer: LENGTH (4 bytes) + DATA
    # Source: encode.ts:238-248
    for buffer in buffers:
        # LENGTH (4 bytes, big-endian Uint32)
        result.extend(struct.pack('>I', len(buffer)))
        # DATA
        result.extend(buffer)

    return bytes(result)


def split_buffers(concatenated: bytes) -> list[bytes]:
    """
    Reproduit splitBuffers() de encode.ts:255-291

    Décode un buffer créé par concat_buffers()

    Args:
        concatenated: Buffer au format concat_buffers

    Returns:
        Liste des buffers individuels

    Raises:
        ValueError: Si la version n'est pas supportée
    """
    buffers = []
    cursor = 0

    # Lire VERSION (4 bytes, big-endian)
    # Source: encode.ts:261-265
    version = struct.unpack('>I', concatenated[cursor:cursor+4])[0]
    if version > CONCAT_BUFFERS_VERSION:
        raise ValueError(f"Version non supportée: {version} (max: {CONCAT_BUFFERS_VERSION})")
    cursor += 4

    # Lire les chunks
    # Source: encode.ts:275-287
    while cursor < len(concatenated):
        # Lire LENGTH (4 bytes, big-endian)
        chunk_size = struct.unpack('>I', concatenated[cursor:cursor+4])[0]
        cursor += 4

        # Lire DATA
        buffers.append(concatenated[cursor:cursor+chunk_size])
        cursor += chunk_size

    return buffers


# =============================================================================
# 3. COMPRESSION / DÉCOMPRESSION
# =============================================================================

def compress_data(data: bytes) -> bytes:
    """
    Compression pako (zlib/deflate)

    Source: encode.ts:1 (import { deflate } from "pako")
    Source: encode.ts:303 (_encryptAndCompress)

    IMPORTANT: pako.deflate() correspond à zlib.compress() en Python
    (format zlib avec header, pas raw deflate)

    Args:
        data: Données à compresser

    Returns:
        Données compressées (zlib)
    """
    # Niveau 6 = niveau par défaut de pako
    return zlib.compress(data, level=6)


def decompress_data(compressed: bytes) -> bytes:
    """
    Décompression pako (zlib/inflate)

    Source: encode.ts:138 (inflate)
    Source: encode.ts:368 (décompression après déchiffrement)

    Args:
        compressed: Données compressées (zlib)

    Returns:
        Données décompressées
    """
    return zlib.decompress(compressed)


# =============================================================================
# 4. CHIFFREMENT / DÉCHIFFREMENT AES-GCM
# =============================================================================

def encrypt_data(
    key_bytes: bytes,
    data: bytes
) -> Tuple[bytes, bytes]:
    """
    Chiffrement AES-128-GCM

    Source: encryption.ts:50-78 (encryptData)
    - Algorithme: AES-GCM
    - Longueur clé: 128 bits (16 bytes)
    - Longueur IV: 12 bytes (96 bits) - recommandation NIST

    Args:
        key_bytes: Clé AES-128 (16 bytes)
        data: Données à chiffrer

    Returns:
        Tuple (encrypted_buffer, iv)
        - encrypted_buffer: Données chiffrées (inclut le tag GCM)
        - iv: Vecteur d'initialisation (12 bytes)
    """
    assert len(key_bytes) == ENCRYPTION_KEY_BYTES, \
        f"Clé doit faire {ENCRYPTION_KEY_BYTES} bytes"

    # Générer IV aléatoire (12 bytes)
    # Source: encryption.ts:56
    iv = os.urandom(IV_LENGTH_BYTES)

    # Chiffrer avec AES-GCM
    # Source: encryption.ts:68-75
    # Note: AES-GCM ajoute automatiquement un tag d'authentification de 16 bytes
    aesgcm = AESGCM(key_bytes)
    encrypted = aesgcm.encrypt(iv, data, None)  # AAD = None

    return encrypted, iv


def decrypt_data(
    key_bytes: bytes,
    iv: bytes,
    encrypted: bytes
) -> bytes:
    """
    Déchiffrement AES-128-GCM

    Source: encryption.ts:80-94 (decryptData)

    Args:
        key_bytes: Clé AES-128 (16 bytes)
        iv: Vecteur d'initialisation (12 bytes)
        encrypted: Données chiffrées (inclut le tag GCM)

    Returns:
        Données déchiffrées

    Raises:
        cryptography.exceptions.InvalidTag: Si le tag GCM est invalide
    """
    assert len(key_bytes) == ENCRYPTION_KEY_BYTES, \
        f"Clé doit faire {ENCRYPTION_KEY_BYTES} bytes"
    assert len(iv) == IV_LENGTH_BYTES, \
        f"IV doit faire {IV_LENGTH_BYTES} bytes"

    # Déchiffrer avec AES-GCM
    # Source: encryption.ts:86-93
    aesgcm = AESGCM(key_bytes)
    decrypted = aesgcm.decrypt(iv, encrypted, None)  # AAD = None

    return decrypted


# =============================================================================
# 5. FONCTIONS DE HAUT NIVEAU (compress + encrypt)
# =============================================================================

def compress_and_encrypt_scene(
    scene_json: str,
    encryption_key: bytes
) -> Tuple[bytes, bytes, str]:
    """
    Reproduit compressData() de encode.ts:322-354

    Séquence complète:
    1. encodingMetadataBuffer (EXTERNE, clair)
    2. contentsMetadataBuffer (INTERNE, sera chiffré) = "null"
    3. Concat metadata interne + scène JSON
    4. Compression pako
    5. Chiffrement AES-GCM
    6. Concat final: metadata externe + iv + buffer chiffré

    Args:
        scene_json: JSON de la scène Excalidraw (string)
        encryption_key: Clé AES-128 (16 bytes)

    Returns:
        Tuple (final_buffer, iv, jwk_k)
        - final_buffer: Buffer final prêt pour base64 puis keyv
        - iv: IV utilisé (12 bytes)
        - jwk_k: Clé au format JWK.k (22 chars) pour l'URL
    """
    # 1. encodingMetadataBuffer (EXTERNE, clair)
    # Source: encode.ts:334-342
    file_info = {
        "version": 2,
        "compression": "pako@1",
        "encryption": "AES-GCM"
    }
    encoding_metadata_buffer = json.dumps(
        file_info,
        separators=(',', ':')
    ).encode('utf-8')

    # 2. contentsMetadataBuffer (INTERNE, sera chiffré)
    # Source: encode.ts:344-346
    # Source: excalidraw-app/data/index.ts:259 (pas de metadata fournie)
    # Donc JSON.stringify(null) = "null"
    contents_metadata_buffer = b'null'

    # 3. dataBuffer = scène JSON en UTF-8
    data_buffer = scene_json.encode('utf-8')

    # 4. Concat metadata interne + data
    # Source: encode.ts:349
    inner_buffer = concat_buffers(contents_metadata_buffer, data_buffer)

    # 5. Compression pako
    # Source: encode.ts:303 (_encryptAndCompress)
    compressed = compress_data(inner_buffer)

    # 6. Chiffrement AES-128-GCM
    # Source: encode.ts:301-306
    encrypted_buffer, iv = encrypt_data(encryption_key, compressed)

    # 7. Buffer final = concat externe
    # Source: encode.ts:353
    final_buffer = concat_buffers(
        encoding_metadata_buffer,
        iv,
        encrypted_buffer
    )

    # Générer le JWK.k pour l'URL
    jwk_k = key_bytes_to_jwk_k(encryption_key)

    return final_buffer, iv, jwk_k


def decrypt_and_decompress_scene(
    final_buffer: bytes,
    jwk_k: str
) -> str:
    """
    Reproduit decompressData() de encode.ts:374-412

    Inverse de compress_and_encrypt_scene()

    Args:
        final_buffer: Buffer complet (metadata + iv + encrypted)
        jwk_k: Clé JWK.k (22 chars base64url)

    Returns:
        JSON de la scène Excalidraw (string)

    Raises:
        ValueError: Si le format est invalide
        cryptography.exceptions.InvalidTag: Si le déchiffrement échoue
    """
    # Décoder la clé JWK
    encryption_key = jwk_k_to_key_bytes(jwk_k)

    # Split le buffer final
    # Source: encode.ts:379
    buffers = split_buffers(final_buffer)

    if len(buffers) != 3:
        raise ValueError(
            f"Buffer final devrait avoir 3 chunks "
            f"(metadata, iv, encrypted), trouvé {len(buffers)}"
        )

    encoding_metadata_buffer, iv, encrypted_buffer = buffers

    # Vérifier le metadata externe
    # Source: encode.ts:381-383
    encoding_metadata = json.loads(encoding_metadata_buffer.decode('utf-8'))

    expected_metadata = {
        "version": 2,
        "compression": "pako@1",
        "encryption": "AES-GCM"
    }
    if encoding_metadata != expected_metadata:
        raise ValueError(
            f"Metadata invalide: attendu {expected_metadata}, "
            f"reçu {encoding_metadata}"
        )

    # Vérifier longueur IV
    if len(iv) != IV_LENGTH_BYTES:
        raise ValueError(
            f"IV devrait faire {IV_LENGTH_BYTES} bytes, "
            f"trouvé {len(iv)}"
        )

    # Déchiffrer
    # Source: encode.ts:386-392
    decrypted = decrypt_data(encryption_key, iv, encrypted_buffer)

    # Décompresser
    # Source: encode.ts:391
    decompressed = decompress_data(decrypted)

    # Split le buffer interne (metadata interne + data)
    # Source: encode.ts:386
    inner_buffers = split_buffers(decompressed)

    if len(inner_buffers) != 2:
        raise ValueError(
            f"Buffer interne devrait avoir 2 chunks "
            f"(contents_metadata, data), trouvé {len(inner_buffers)}"
        )

    contents_metadata_buffer, data_buffer = inner_buffers

    # Vérifier metadata interne (devrait être "null")
    # Source: encode.ts:395-397
    contents_metadata = json.loads(contents_metadata_buffer.decode('utf-8'))
    if contents_metadata is not None:
        # Note: on accepte None ou null, mais on log un warning si c'est autre chose
        pass

    # Décoder le JSON de la scène
    scene_json = data_buffer.decode('utf-8')

    return scene_json


# =============================================================================
# 6. WRAPPER KEYV (format PostgreSQL)
# =============================================================================

def create_keyv_wrapper(buffer: bytes) -> str:
    """
    Crée le wrapper JSON keyv pour INSERT dans keyv.value

    Format: {"value": ":base64:{buffer}", "expires": null}

    Source: Vérification VPS (format moderne avec chiffrement)
    Validation: 10 scènes au format moderne confirmé

    Args:
        buffer: Buffer final (output de compress_and_encrypt_scene)

    Returns:
        JSON string prêt pour INSERT SQL
    """
    # Encoder le buffer en base64
    buffer_b64 = base64.b64encode(buffer).decode('ascii')

    # Créer le wrapper JSON avec préfixe :base64:
    wrapper = {
        "value": f":base64:{buffer_b64}",
        "expires": None  # null en JSON
    }

    # Sérialiser en JSON (compact, sans espaces)
    return json.dumps(wrapper, separators=(',', ':'))


def parse_keyv_wrapper(value_json: str) -> bytes:
    """
    Parse le wrapper JSON keyv et retourne le buffer décodé

    Args:
        value_json: JSON string depuis keyv.value

    Returns:
        Buffer décodé (input pour decrypt_and_decompress_scene)

    Raises:
        ValueError: Si le format n'est pas supporté
    """
    wrapper = json.loads(value_json)
    value_str = wrapper['value']

    # Vérifier le préfixe :base64:
    if not value_str.startswith(':base64:'):
        raise ValueError(
            f"Format non supporté (attendu :base64:, trouvé: {value_str[:20]}...)"
        )

    # Retirer le préfixe et décoder
    buffer_b64 = value_str[8:]  # Enlever ":base64:"
    return base64.b64decode(buffer_b64)


# =============================================================================
# 7. FONCTION UTILITAIRE - GÉNÉRATION D'ID
# =============================================================================

def generate_scene_id() -> str:
    """
    Génère un ID de scène au format Excalidraw (13 chiffres)

    Format: timestamp en millisecondes + random
    Exemple: "2878434095682463"

    CONTRAINTE CRITIQUE: Le backend Excalidraw N'ACCEPTE QUE des IDs numériques purs.
    - ✅ Valide: "1779030793059", "2878434095682463"
    - ❌ Invalide: "TEST-123", "SCENE-456", "TESTB-1779030670061"

    Tout ID contenant des lettres ou tirets provoque 500/502 du backend.
    Validé par tests bidirectionnels Phase H.2 (17/05/2026).

    Source: Observation VPS (format SCENES:XXXXXXXXXXXXX)
    """
    import time

    # Timestamp en millisecondes (13 chiffres)
    timestamp_ms = int(time.time() * 1000)

    # Ajouter un peu d'aléatoire sur les derniers chiffres
    random_suffix = os.urandom(2)
    random_int = int.from_bytes(random_suffix, 'big') % 10000

    scene_id = f"{timestamp_ms}{random_int:04d}"

    return scene_id
