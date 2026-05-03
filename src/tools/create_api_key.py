import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from _py_clob_client.client import ClobClient
from core.config import Config


def main():
    host = Config.HOST
    key = Config.PRIVATE_KEY
    chain_id = Config.CHAIN_ID
    funder = Config.PRIVATE_KEY
    client = ClobClient(host, key=key, chain_id=chain_id, signature_type=2, funder=funder)

    try:
        api_creds = client.create_or_derive_api_creds()
        print("API Key:", api_creds.api_key)
        print("Secret:", api_creds.api_secret)
        print("Passphrase:", api_creds.api_passphrase)
    except Exception as e:
        print("Error creating API:", e)

if __name__ == "__main__":
    os.environ['HTTP_PROXY'] = Config.HTTP_PROXY or ''
    os.environ['HTTPS_PROXY'] = Config.HTTPS_PROXY or ''
    main()
