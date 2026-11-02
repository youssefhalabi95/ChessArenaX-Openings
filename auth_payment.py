"""Account sign-in and Lemon Squeezy one-time-payment integration for Flask.

Configure all required values as environment variables. Never commit secrets.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

account_bp = Blueprint("account", __name__)
DB_PATH = Path(__file__).resolve().parent / "chessarenax_accounts.sqlite3"
LEMON_API = "https://api.lemonsqueezy.com/v1/checkouts"


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS premium_orders (
        order_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        variant_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        identity_key TEXT NOT NULL,
        attempted_at INTEGER NOT NULL
    )""")
    conn.commit()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_account_db():
    with _db() as conn:
        pass


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _csrf_ok():
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    saved = session.get("csrf_token", "")
    return bool(sent and saved and hmac.compare_digest(sent, saved))


def require_csrf(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _csrf_ok():
            abort(400, description="The form expired or could not be verified. Refresh and try again.")
        return view(*args, **kwargs)
    return wrapped


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in first.", "info")
            return redirect(url_for("account.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with _db() as conn:
        row = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        session.clear()
        return None
    return dict(row)


def has_premium_access(user_id):
    if not user_id:
        return False
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM premium_orders WHERE user_id = ? AND status = 'paid' LIMIT 1",
            (user_id,)
        ).fetchone()
    return row is not None


def _safe_next(value):
    if not value:
        return url_for("account.account_home")
    # Only permit local relative paths; never redirect to an attacker-controlled host.
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return url_for("account.account_home")
    return value


@account_bp.app_context_processor
def inject_account_context():
    return {"current_user": current_user, "csrf_token": csrf_token}


@account_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if not _csrf_ok():
            abort(400, description="The form expired. Refresh and try again.")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(email) > 254 or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Enter a valid email address.", "error")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.", "error")
        else:
            try:
                with _db() as conn:
                    cur = conn.execute(
                        "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                        (email, generate_password_hash(password))
                    )
                    user_id = cur.lastrowid
                session.clear()
                session["user_id"] = user_id
                session["csrf_token"] = secrets.token_urlsafe(32)
                flash("Your account has been created.", "success")
                return redirect(_safe_next(request.form.get("next")))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists. Sign in instead.", "error")
    return render_template("account_auth.html", page="signup", next_url=_safe_next(request.args.get("next")))


@account_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not _csrf_ok():
            abort(400, description="The form expired. Refresh and try again.")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        identity_key = hashlib.sha256((str(request.remote_addr) + "|" + email).encode("utf-8")).hexdigest()
        with _db() as conn:
            # Basic persistent throttling: at most 10 failed attempts per IP/email pair per 15 minutes.
            conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (time.time() - 86400,))
            recent = conn.execute(
                "SELECT COUNT(*) AS n FROM login_attempts WHERE identity_key = ? AND attempted_at > ?",
                (identity_key, time.time() - 900)
            ).fetchone()["n"]
            user = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if recent >= 10:
            flash("Too many sign-in attempts. Please wait 15 minutes before trying again.", "error")
        elif user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(_safe_next(request.args.get("next") or request.form.get("next")))
        else:
            with _db() as conn:
                conn.execute("INSERT INTO login_attempts(identity_key, attempted_at) VALUES (?, ?)", (identity_key, int(time.time())))
            # Do not reveal whether an email address exists.
            flash("Email or password was incorrect.", "error")
    return render_template("account_auth.html", page="login", next_url=_safe_next(request.args.get("next")))


@account_bp.route("/logout", methods=["POST"])
@require_csrf
def logout():
    session.clear()
    return redirect(url_for("home"))


@account_bp.route("/account")
@login_required
def account_home():
    user = current_user()
    premium = has_premium_access(user["id"])
    with _db() as conn:
        orders = conn.execute(
            "SELECT order_id, status, created_at FROM premium_orders WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()
    return render_template("account_home.html", user=user, premium=premium, orders=orders)


@account_bp.route("/buy-strategy", methods=["POST"])
@login_required
@require_csrf
def buy_strategy():
    user = current_user()
    if has_premium_access(user["id"]):
        flash("Strategy Lab Premium is already active on your account.", "success")
        return redirect(url_for("strategy.strategy_home"))

    api_key = os.environ.get("LEMONSQUEEZY_API_KEY", "")
    store_id = os.environ.get("LEMONSQUEEZY_STORE_ID", "")
    variant_id = os.environ.get("LEMONSQUEEZY_STRATEGY_VARIANT_ID", "")
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    if not all((api_key, store_id, variant_id, site_url)):
        current_app.logger.error("Lemon Squeezy environment configuration is incomplete.")
        flash("Checkout is not configured yet. Please try again later.", "error")
        return redirect(url_for("strategy.strategy_home"))

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user["email"],
                    "custom": {"user_id": str(user["id"]), "product_key": "strategy_lab_lifetime"}
                },
                "product_options": {
                    "redirect_url": site_url + url_for("account.account_home"),
                    "receipt_button_text": "Return to ChessArenaX",
                    "receipt_thank_you_note": "Thank you for supporting ChessArenaX. Premium access will activate after payment confirmation."
                }
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(store_id)}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}}
            }
        }
    }
    try:
        response = requests.post(
            LEMON_API,
            headers={
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
                "Authorization": "Bearer " + api_key,
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        checkout_url = response.json()["data"]["attributes"]["url"]
        # Accept only Lemon Squeezy checkout URLs returned by its API.
        parsed = urlparse(checkout_url)
        if parsed.scheme != "https" or not parsed.netloc.endswith("lemonsqueezy.com"):
            raise ValueError("Unexpected checkout host returned by provider")
        return redirect(checkout_url, code=303)
    except (requests.RequestException, KeyError, ValueError) as exc:
        current_app.logger.exception("Could not create Lemon Squeezy checkout: %s", exc)
        flash("We could not start checkout. Please try again later.", "error")
        return redirect(url_for("strategy.strategy_home"))


@account_bp.route("/webhooks/lemonsqueezy", methods=["POST"])
def lemonsqueezy_webhook():
    secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Signature", "")
    raw_body = request.get_data(cache=False)
    if not secret or not signature:
        abort(401)
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        abort(401)

    try:
        event = request.get_json(force=True)
        event_name = event.get("meta", {}).get("event_name", "")
        custom = event.get("meta", {}).get("custom_data") or {}
        data = event.get("data", {})
        attrs = data.get("attributes", {})
        order_id = str(data.get("id", ""))
        user_id = int(custom.get("user_id", 0))
        variant_id = str(attrs.get("variant_id", ""))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "Malformed webhook payload"}), 400

    configured_variant = os.environ.get("LEMONSQUEEZY_STRATEGY_VARIANT_ID", "")
    if not order_id:
        return jsonify({"ok": True, "ignored": "no order id"})

    if event_name == "order_created":
        if (str(user_id) == "0" or variant_id != configured_variant
                or str(attrs.get("status", "")).lower() != "paid"):
            current_app.logger.warning("Ignoring non-matching or unpaid Lemon Squeezy order %s", order_id)
            return jsonify({"ok": True, "ignored": "unpaid or non-matching order"})
        with _db() as conn:
            user_exists = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_exists:
                conn.execute("""INSERT INTO premium_orders(order_id, user_id, variant_id, status)
                    VALUES (?, ?, ?, 'paid')
                    ON CONFLICT(order_id) DO UPDATE SET status = 'paid'""",
                    (order_id, user_id, variant_id))
        return jsonify({"ok": True})

    if event_name == "order_refunded":
        with _db() as conn:
            conn.execute("UPDATE premium_orders SET status = 'refunded' WHERE order_id = ?", (order_id,))
        return jsonify({"ok": True})

    # Acknowledge events that are not relevant to the one-time purchase product.
    return jsonify({"ok": True, "ignored": event_name})


@account_bp.route("/payment/success")
def payment_success():
    # A return URL is not proof of payment; the webhook grants access.
    if session.get("user_id"):
        flash("Thanks! Your payment is being confirmed. Refresh your account in a moment.", "info")
        return redirect(url_for("account.account_home"))
    return redirect(url_for("account.login"))


init_account_db()
