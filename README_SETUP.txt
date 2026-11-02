ChessArenaX Academy — Lemon Squeezy + account sign-in integration
===============================================================

WHAT THIS CHANGES
- Adds email/password account creation, sign-in and sign-out.
- Passwords are stored as Werkzeug password hashes, never plaintext.
- Adds CSRF tokens to account forms and the checkout POST.
- Adds basic failed-login throttling (per IP/email pair).
- Sends customers to a Lemon Squeezy-hosted checkout; card data never passes through ChessArenaX.
- Activates Strategy Lab Premium only after a valid signed Lemon Squeezy webhook reports a paid order for the configured variant.
- Stores purchases by user ID, so access is account-based rather than browser-session-based.
- Handles the order_refunded event by marking that order refunded.
- Keeps lesson 1 free. Other lessons require verified purchase.

FILES
1. auth_payment.py                  -> project root, next to app.py
2. strategy_room.py                 -> replace the earlier Strategy Lab starter version
3. templates/account_auth.html      -> templates folder
4. templates/account_home.html      -> templates folder
5. templates/strategy.html          -> replace the earlier Strategy Lab template
6. requirements-additions.txt      -> add requests to your requirements.txt

IMPORTANT: Do not replace app.py with a new file. Merge the small app.py changes below into your existing app.py so you preserve the Opening and Tactics rooms.

1) INSTALL DEPENDENCY
Run in the VS Code terminal, from your project folder:
    python -m pip install requests
Add this line to your existing requirements.txt if it is not already there:
    requests>=2.31.0

2) REGISTER BOTH BLUEPRINTS IN app.py
Near the top of app.py, add `import os` if it is not already there.
After your existing `app = Flask(__name__)` line and before the app starts, add:

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Set the SECRET_KEY environment variable before starting ChessArenaX.")

Then, after `app = Flask(__name__)` and after the config above, add:

    from auth_payment import account_bp
    from strategy_room import strategy_bp
    app.register_blueprint(account_bp)
    app.register_blueprint(strategy_bp)

If you already registered `strategy_bp`, do not register it a second time. Ensure `account_bp` is registered too.

3) SET LOCAL ENVIRONMENT VARIABLES (PowerShell)
Generate a long random secret. For a quick local test, in the VS Code PowerShell terminal:

    $env:SECRET_KEY = "replace-this-with-a-long-random-secret"
    $env:COOKIE_SECURE = "0"
    $env:SITE_URL = "http://127.0.0.1:5000"
    python app.py

Do not use that example secret in production. For production, generate a unique random SECRET_KEY (at least 32 random bytes) and keep it private. Set COOKIE_SECURE=1 only when the site is served over HTTPS. Environment variables entered in PowerShell apply only to that terminal session.

4) CREATE YOUR LEMON SQUEEZY PRODUCT
In your Lemon Squeezy dashboard:
- Complete merchant/store approval and payout setup first.
- Create a one-time product such as “ChessArenaX Strategy Lab Premium — Lifetime Access”.
- Set the price and currency you want customers to pay.
- Copy the Store ID and the Variant ID for that one-time product variant.
- Create an API key with the access needed to create checkouts.

Set these environment variables on your local machine/production host:
    LEMONSQUEEZY_API_KEY=your_private_api_key
    LEMONSQUEEZY_STORE_ID=your_store_id
    LEMONSQUEEZY_STRATEGY_VARIANT_ID=your_variant_id
    LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_signing_secret
    SITE_URL=https://your-real-domain.example
    SECRET_KEY=your_long_random_flask_secret
    COOKIE_SECURE=1

Never put the API key, webhook secret, or SECRET_KEY in app.py, HTML, JavaScript, GitHub, or a public repository. Do not send them to ChatGPT.

5) CREATE THE WEBHOOK
In Lemon Squeezy dashboard > Settings > Webhooks, add this callback URL:
    https://YOUR-REAL-DOMAIN/webhooks/lemonsqueezy
Subscribe to at least:
- order_created
- order_refunded
Copy the signing secret shown for this webhook into LEMONSQUEEZY_WEBHOOK_SECRET.
The endpoint validates the X-Signature HMAC against the raw request body. Do not disable that validation.

6) TEST BEFORE SELLING
- Use Lemon Squeezy test mode and test products/transactions first.
- Create an account, sign in, open Strategy Lab, and start checkout.
- Confirm that returning to the site alone does NOT unlock premium.
- Confirm that a correctly signed order_created event for the configured variant with status=paid unlocks premium for that user.
- Confirm invalid webhook signatures are rejected (HTTP 401).
- Confirm a refund event removes active access.
- Test on HTTPS after deploying; then set COOKIE_SECURE=1.

HOW THE ACCESS CHECK WORKS
The checkout sends the logged-in user's numeric ID as Lemon Squeezy custom data. The server does not grant access based on the browser's return URL. It grants access only after validating the webhook signature and checking the product variant and paid status. A user can never unlock premium merely by editing a URL or setting a browser variable.

LIMITATIONS / BEFORE A PUBLIC LAUNCH
- This is a starter implementation for a one-time/lifetime purchase, not subscriptions.
- It does not yet include email verification, password-reset emails, two-factor authentication, a user-deletion workflow, or a privacy/terms/refund policy. Add these before a serious public launch.
- The basic login throttle is per IP/email pair. If you use a reverse proxy, configure trusted proxy handling carefully; do not blindly trust client-supplied forwarded IP headers.
- SQLite is suitable for a small prototype. Ensure the database files live on persistent storage and are backed up. On a multi-worker/production deployment, consider a managed database.
- Keep Python dependencies current and run the site behind HTTPS. Never run Flask's debug server in production.
- If the Lemon Squeezy webhook is configured to send different event names or the payload shape changes, verify it against the current provider docs and test events before launch.
