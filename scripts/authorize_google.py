"""Google OAuth 2.0 Authorization Script.

One-time script to obtain OAuth tokens for the Blogger API.
Opens a browser for Google login and stores the refresh token
locally for automated pipeline use.

Usage:
    python scripts/authorize_google.py

This creates: credentials/blogger_token.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the backend directory to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
TOKEN_FILE = CREDENTIALS_DIR / "blogger_token.json"

# Scopes required for Blogger API
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def main() -> None:
    """Run the OAuth authorization flow."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib is not installed.")
        print("Run: pip install google-auth-oauthlib")
        sys.exit(1)

    print("=" * 60)
    print("  AI Blogger — Google OAuth 2.0 Authorization")
    print("=" * 60)
    print()

    # Load environment config
    try:
        from dotenv import load_dotenv
        import os

        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"  ✓ Loaded .env from {env_file}")
        else:
            print(f"  ⚠ No .env file found at {env_file}")
            print("    Create one from .env.example first.")
            sys.exit(1)

        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            print()
            print("  ✗ GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env")
            print()
            print("  To get these:")
            print("  1. Go to https://console.cloud.google.com")
            print("  2. Create OAuth 2.0 credentials (Desktop App type)")
            print("  3. Copy the Client ID and Client Secret to .env")
            sys.exit(1)

    except ImportError:
        print("  ⚠ python-dotenv not installed, reading env vars directly")
        import os
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Build OAuth client config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print()
    print("  Starting OAuth flow...")
    print("  A browser window will open for Google login.")
    print("  Grant access to the Blogger API when prompted.")
    print()

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    # Save token
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }

    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))

    print()
    print("  ✓ Authorization successful!")
    print(f"  ✓ Token saved to: {TOKEN_FILE}")
    print()
    print("  You can now run the pipeline:")
    print("    python -m app.pipeline.orchestrator --blog-id=<YOUR_BLOG_UUID>")
    print()

    # Test the token by listing blogs
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        test_creds = Credentials(
            token=creds.token,
            refresh_token=creds.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        service = build("blogger", "v3", credentials=test_creds)
        blogs = service.blogs().listByUser(userId="self").execute()

        print("  Your Blogger blogs:")
        for blog in blogs.get("items", []):
            print(f"    • {blog['name']}")
            print(f"      ID: {blog['id']}")
            print(f"      URL: {blog['url']}")
            print()

        print("  Set PRIMARY_BLOG_ID in .env to the blog ID above.")

    except Exception as exc:
        print(f"  ⚠ Could not list blogs: {exc}")
        print("    The token is saved — you can still use it.")


if __name__ == "__main__":
    main()
