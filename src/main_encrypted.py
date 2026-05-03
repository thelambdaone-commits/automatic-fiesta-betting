import os
import sys
import argparse
import base64
from pathlib import Path
from dotenv import load_dotenv

from session_manager import SessionManager, SessionData
from core.config import Config

def main():
    load_dotenv()

    session_key_b64 = os.getenv("SESSION_KEY")
    if not session_key_b64:
        print("ERREUR: SESSION_KEY non définie dans .env (doit être 32 bytes base64)")
        sys.exit(1)
    try:
        session_key = base64.b64decode(session_key_b64)
        if len(session_key) != 32:
            raise ValueError
    except Exception:
        print("ERREUR: SESSION_KEY invalide (doit être 32 bytes encodés en base64)")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=str, default="default",
                        help="Nom de la session (ex: production, test, default)")
    args = parser.parse_args()

    session_file = Config.CONFIG_DIR / "session" / f"{args.session}.enc"
    if not session_file.exists():
        print(f"Session introuvable : {session_file}")
        print("Sessions disponibles:", SessionManager.list_sessions(str(Config.CONFIG_DIR / "session")))
        sys.exit(1)

    sm = SessionManager(session_key)
    session_data = sm.load(str(session_file))
    Config.from_session(session_data)

    print(f"✅ Configuration chargée depuis la session '{args.session}'")
    print(f"   API Key: {Config.API_KEY[:8]}...")
    print(f"   Host: {Config.HOST}")
    print(f"   Chain ID: {Config.CHAIN_ID}")

    mode = os.getenv('MODE', 'prod')
    print(f"   Mode: {mode}")

    from main_copy_trade import main as copy_trade_main
    import asyncio
    asyncio.run(copy_trade_main())

if __name__ == "__main__":
    main()
