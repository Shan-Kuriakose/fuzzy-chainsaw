"""The ASGI entrypoint a deployment runs.

Configuration is resolved from the environment here; a missing required
value raises ``ValidationError`` before the server can accept traffic.
"""

from app.main import create_app
from app.settings import Settings

app = create_app(Settings())
