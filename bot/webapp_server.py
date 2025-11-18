"""
Simple web server to serve the Mini App and proxy API requests
This should be integrated into telegram_bot.py or run as a separate service
"""
import os
import asyncio
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from pathlib import Path

import aiohttp
from aiohttp import web

# Configuration
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
WEBAPP_DIR = Path(__file__).parent / "webapp"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

logger = logging.getLogger(__name__)


def verify_telegram_webapp_data(init_data: str) -> tuple[bool, int | None]:
    """
    Verify Telegram Web App init data using HMAC-SHA-256
    Returns (is_valid, user_id)
    """
    if not init_data or not TELEGRAM_BOT_TOKEN:
        logger.warning("Missing init_data or bot token")
        return False, None

    try:
        # Parse init data
        parsed_data = dict(parse_qsl(init_data))

        # Extract hash and user data
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            logger.warning("No hash in init_data")
            return False, None

        # Get user ID from parsed data
        user_id = None
        if 'user' in parsed_data:
            import json
            user_data = json.loads(parsed_data['user'])
            user_id = user_data.get('id')

        # Create data check string
        data_check_items = sorted(
            [f"{k}={v}" for k, v in parsed_data.items()],
            key=lambda x: x.split('=')[0]
        )
        data_check_string = '\n'.join(data_check_items)

        # Create secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Verify hash
        is_valid = hmac.compare_digest(calculated_hash, received_hash)

        if not is_valid:
            logger.warning("Invalid HMAC signature")

        return is_valid, user_id

    except Exception as e:
        logger.error(f"Error verifying webapp data: {e}")
        return False, None


def check_user_authorized(user_id: int | None) -> bool:
    """Check if user is authorized to access the webapp"""
    if not user_id:
        logger.warning("No user_id provided")
        return False

    if ALLOWED_USER_ID == 0:
        logger.warning("TELEGRAM_USER_ID not configured in environment")
        return False

    is_authorized = user_id == ALLOWED_USER_ID

    if not is_authorized:
        logger.warning(f"Unauthorized user attempted access: {user_id}")

    return is_authorized


async def serve_webapp(request):
    """Serve the Mini App HTML - only accessible from Telegram"""
    # Check if accessed from Telegram Web App
    init_data = request.query.get('tgWebAppData') or request.headers.get('X-Telegram-Init-Data', '')

    if not init_data:
        # No Telegram data - accessed directly from browser
        return web.Response(
            text='<html><body style="font-family: sans-serif; text-align: center; padding: 50px;">'
                 '<h1>🔒 Acceso Denegado</h1>'
                 '<p>Esta aplicación solo puede ser accedida desde Telegram.</p>'
                 '<p>Por favor, abre la Mini App desde el bot de Telegram.</p>'
                 '</body></html>',
            content_type='text/html',
            status=403
        )

    is_valid, user_id = verify_telegram_webapp_data(init_data)

    if not is_valid:
        return web.Response(
            text='<html><body style="font-family: sans-serif; text-align: center; padding: 50px;">'
                 '<h1>❌ Datos Inválidos</h1>'
                 '<p>Los datos de Telegram no son válidos.</p>'
                 '</body></html>',
            content_type='text/html',
            status=401
        )

    if not check_user_authorized(user_id):
        return web.Response(
            text='<html><body style="font-family: sans-serif; text-align: center; padding: 50px;">'
                 '<h1>⛔ Acceso No Autorizado</h1>'
                 '<p>No tienes permiso para acceder a esta aplicación.</p>'
                 '</body></html>',
            content_type='text/html',
            status=403
        )

    # User is authorized - serve the app
    index_path = WEBAPP_DIR / "index.html"
    return web.FileResponse(index_path)


async def serve_static(request):
    """Serve static files (CSS, JS) - only for authorized users"""
    # Check Telegram data from referer or session
    # Static files are loaded after HTML, so we check the referer
    referer = request.headers.get('Referer', '')

    # If no valid referer, require auth header
    if not referer or '/webapp' not in referer:
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        if init_data:
            is_valid, user_id = verify_telegram_webapp_data(init_data)
            if not is_valid or not check_user_authorized(user_id):
                raise web.HTTPForbidden(text="Access denied")

    filename = request.match_info['filename']
    file_path = WEBAPP_DIR / filename

    if not file_path.exists():
        raise web.HTTPNotFound()

    # Don't allow directory traversal
    if not file_path.resolve().is_relative_to(WEBAPP_DIR.resolve()):
        raise web.HTTPForbidden()

    return web.FileResponse(file_path)


async def proxy_api_request(request):
    """Proxy API requests to backend"""
    # Verify Telegram Web App data
    init_data = request.headers.get('X-Telegram-Init-Data', '')

    is_valid, user_id = verify_telegram_webapp_data(init_data)

    if not is_valid:
        raise web.HTTPUnauthorized(text="Invalid Telegram data")

    # Check if user is authorized
    if not check_user_authorized(user_id):
        raise web.HTTPForbidden(text="Access denied")

    # Get path after /api/
    path = request.match_info['path']

    # Build backend URL
    backend_url = f"{BACKEND_API_URL}/{path}"

    # Forward query parameters
    if request.query_string:
        backend_url += f"?{request.query_string}"

    async with aiohttp.ClientSession() as session:
        # Prepare request kwargs
        kwargs = {
            'headers': dict(request.headers),
        }

        # Add body for POST/PUT/PATCH requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            kwargs['json'] = await request.json()

        # Make request to backend
        async with session.request(request.method, backend_url, **kwargs) as resp:
            body = await resp.json()
            return web.json_response(body, status=resp.status)


async def health_check(request):
    """Health check endpoint"""
    return web.json_response({"status": "ok", "service": "webapp-server"})


def create_app():
    """Create web application"""
    app = web.Application()

    # Routes
    app.router.add_get('/webapp', serve_webapp)
    app.router.add_get('/webapp/', serve_webapp)
    app.router.add_get('/static/{filename}', serve_static)
    app.router.add_route('*', '/api/{path:.*}', proxy_api_request)
    app.router.add_get('/health', health_check)

    return app


async def run_server(host='0.0.0.0', port=8443):
    """Run the web server"""
    app = create_app()

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"Web App server started on http://{host}:{port}")
    logger.info(f"Mini App URL: http://{host}:{port}/webapp")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(run_server())
