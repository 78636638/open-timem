"""
TiMem Web Interface Router

Provides web interface for chat functionality.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

router = APIRouter(tags=["web"])

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")
TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")
STATIC_DIR = os.path.join(WEB_DIR, "static")


@router.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """
    Serve the chat interface page.

    Returns:
        HTML page for the chat interface
    """
    index_path = os.path.join(TEMPLATES_DIR, "index.html")

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content=content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TiMem Chat</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                h1 { color: #4F46E5; }
                p { color: #6B7280; }
                a { color: #4F46E5; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌲 TiMem Chat</h1>
                <p>聊天界面加载中...</p>
                <p><a href="/">返回首页</a> | <a href="/docs">API 文档</a></p>
            </div>
        </body>
        </html>
        """,
        status_code=200
    )


@router.get("/web/static/{path:path}")
async def serve_static(path: str):
    """
    Serve static files (CSS, JS, images).

    Args:
        path: The path to the static file

    Returns:
        Static file response
    """
    file_path = os.path.join(STATIC_DIR, path)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        response = FileResponse(file_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return {"error": "File not found"}, 404