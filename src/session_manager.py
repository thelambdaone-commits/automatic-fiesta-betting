import os
import json
import base64
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class SessionData:
    """Données de session Polymarket"""
    alchemy_ws_url: str
    tracked_wallets: List[str]
    private_key: str
    funder_address: Optional[str]
    polymarket_api_key: str
    polymarket_api_secret: str
    polymarket_api_passphrase: str
    rpc_url: str
    host: str
    chain_id: int
    min_order_size: float
    max_order_size: float
    slippage_tolerance: float
    follow_delay: float
    match_orders_signature: str


class SessionManager:
    """Charge et sauvegarde des sessions chiffrées avec AES-256-GCM"""

    def __init__(self, encryption_key: bytes):
        if len(encryption_key) != 32:
            raise ValueError("La clé doit faire 32 bytes (256 bits)")
        self._key = encryption_key

    def _encrypt(self, plaintext: bytes) -> str:
        """Chiffre et retourne base64 (nonce + ciphertext + tag)"""
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, b"")
        encrypted = nonce + ciphertext
        return base64.b64encode(encrypted).decode('utf-8')

    def _decrypt(self, encrypted_b64: str) -> bytes:
        """Déchiffre depuis une chaîne base64"""
        data = base64.b64decode(encrypted_b64)
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, b"")
        return plaintext

    def save(self, session: SessionData, path: str):
        """Chiffre et sauvegarde la session dans un fichier .enc"""
        session_dict = asdict(session)
        json_str = json.dumps(session_dict, indent=2)
        encrypted = self._encrypt(json_str.encode('utf-8'))
        Path(path).write_text(encrypted)

    def load(self, path: str) -> SessionData:
        """Charge et déchiffre un fichier .enc, retourne SessionData"""
        encrypted_b64 = Path(path).read_text()
        plaintext = self._decrypt(encrypted_b64)
        data = json.loads(plaintext.decode('utf-8'))
        return SessionData(
            alchemy_ws_url=data.get('alchemy_ws_url', 'wss://polygon-rpc.com'),
            tracked_wallets=data.get('tracked_wallets', []),
            private_key=data['private_key'],
            funder_address=data.get('funder_address'),
            polymarket_api_key=data['polymarket_api_key'],
            polymarket_api_secret=data['polymarket_api_secret'],
            polymarket_api_passphrase=data['polymarket_api_passphrase'],
            rpc_url=data.get('rpc_url', 'https://polygon-rpc.com'),
            host=data.get('host', 'https://clob.polymarket.com'),
            chain_id=data.get('chain_id', 137),
            min_order_size=data.get('min_order_size', 10.0),
            max_order_size=data.get('max_order_size', 1000.0),
            slippage_tolerance=data.get('slippage_tolerance', 0.01),
            follow_delay=data.get('follow_delay', 1.0),
            match_orders_signature=data.get('match_orders_signature', 'd2539b37')
        )

    @staticmethod
    def list_sessions(directory: str = "config/session") -> List[str]:
        """Liste les fichiers .enc dans le dossier config/session"""
        session_dir = Path(directory)
        if not session_dir.exists():
            return []
        return [f.stem for f in session_dir.glob("*.enc")]
