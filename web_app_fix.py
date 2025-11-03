"""
Quick fix for web_app.py SocketIO error
Replace line 35 in web_app.py with this:
"""

# OLD (line 35):
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# NEW - Use threading instead:
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Or even simpler - let it auto-detect:
# socketio = SocketIO(app, cors_allowed_origins="*")
