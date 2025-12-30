# WebSocket Quick Start Guide

Guide rapide pour tester et intégrer le WebSocket dans GatheRing.

## 1. Démarrage Rapide (5 minutes)

### Étape 1: Démarrer le serveur

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Démarrer FastAPI avec WebSocket
uvicorn gathering.api:app --reload
```

Le serveur démarre sur `http://localhost:8000`.

### Étape 2: Ouvrir le dashboard test

Ouvrez dans votre navigateur:
```
file:///path/to/gathering/dashboard/websocket_test.html
```

Ou utilisez un serveur HTTP local:
```bash
cd dashboard
python3 -m http.server 8080
```

Puis ouvrez: `http://localhost:8080/websocket_test.html`

### Étape 3: Connecter

1. Cliquez sur **"Connect"** dans le dashboard
2. Vous devriez voir: `✅ Connected to GatheRing WebSocket`

### Étape 4: Générer des événements

Dans un autre terminal, exécutez le script de test:

```bash
source venv/bin/activate
python test_websocket_integration.py server
```

Vous devriez voir les événements apparaître en temps réel dans le dashboard !

## 2. Test Manuel avec curl/websocat

### Installation de websocat (alternative à curl)

```bash
# macOS
brew install websocat

# Linux
cargo install websocat
```

### Connexion WebSocket

```bash
websocat ws://localhost:8000/ws/dashboard?client_id=test-cli
```

Vous devriez recevoir:
```json
{
  "type": "connection.established",
  "data": {
    "client_id": "test-cli",
    "message": "Connected to GatheRing WebSocket"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Envoyer un ping

Dans websocat, tapez:
```json
{"type": "ping"}
```

Vous devriez recevoir:
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

## 3. Test Programmatique (Python)

### Test simple

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/dashboard?client_id=python-test"

    async with websockets.connect(uri) as ws:
        # Receive connection confirmation
        message = await ws.recv()
        print(f"Connected: {json.loads(message)}")

        # Send ping
        await ws.send(json.dumps({"type": "ping"}))

        # Receive pong
        pong = await ws.recv()
        print(f"Pong: {json.loads(pong)}")

        # Listen for events (10 seconds)
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(message)
                print(f"Event: {data['type']} - {data.get('data')}")
        except asyncio.TimeoutError:
            print("Timeout - no more events")

asyncio.run(test_websocket())
```

### Générer des événements de test

```python
from gathering.events import event_bus, Event, EventType

# Publier un événement
await event_bus.publish(Event(
    type=EventType.AGENT_STARTED,
    data={
        "agent_id": 1,
        "name": "Alice",
        "competencies": ["python", "react"]
    },
    source_agent_id=1,
))
```

Le WebSocket client devrait recevoir:
```json
{
  "type": "agent.started",
  "data": {
    "agent_id": 1,
    "name": "Alice",
    "competencies": ["python", "react"]
  },
  "source_agent_id": 1,
  "circle_id": null,
  "project_id": null,
  "event_id": "evt_...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 4. Intégration dans Application Startup

Pour activer le WebSocket broadcasting au démarrage de l'application:

### Option 1: Via gathering/api.py (recommandé)

Vérifiez que `gathering/api.py` contient:

```python
from gathering.websocket.integration import setup_websocket_broadcasting

@app.on_event("startup")
async def startup():
    # Enable WebSocket broadcasting
    setup_websocket_broadcasting()
    print("[WebSocket] Broadcasting enabled")
```

### Option 2: Configuration personnalisée

Pour broadcaster uniquement certains événements:

```python
from gathering.websocket.integration import setup_websocket_broadcasting
from gathering.events import EventType

@app.on_event("startup")
async def startup():
    # Only broadcast task and agent events
    setup_websocket_broadcasting(event_types=[
        EventType.AGENT_STARTED,
        EventType.TASK_CREATED,
        EventType.TASK_COMPLETED,
    ])
```

### Option 3: Broadcasting avec filtre

```python
from gathering.websocket.integration import setup_custom_broadcasting
from gathering.events import EventType

@app.on_event("startup")
async def startup():
    # Only broadcast events for circle_id == 1
    setup_custom_broadcasting(
        EventType.TASK_COMPLETED,
        filter_fn=lambda e: e.circle_id == 1
    )
```

## 5. Intégration Dashboard React

### Installation

```bash
cd dashboard
npm install --save-dev websocket
```

### Hook React personnalisé

```javascript
// hooks/useWebSocket.js
import { useEffect, useState, useCallback } from 'react';

export function useWebSocket(url) {
    const [ws, setWs] = useState(null);
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState(null);

    useEffect(() => {
        const websocket = new WebSocket(url);

        websocket.onopen = () => {
            console.log('WebSocket connected');
            setConnected(true);
        };

        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            setLastEvent(message);
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        websocket.onclose = () => {
            console.log('WebSocket disconnected');
            setConnected(false);
        };

        setWs(websocket);

        return () => {
            websocket.close();
        };
    }, [url]);

    const sendMessage = useCallback((message) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }, [ws]);

    return { connected, lastEvent, sendMessage };
}
```

### Utilisation dans composant

```javascript
// components/Dashboard.jsx
import { useWebSocket } from '../hooks/useWebSocket';
import { useEffect, useState } from 'react';

export function Dashboard() {
    const { connected, lastEvent } = useWebSocket('ws://localhost:8000/ws/dashboard?client_id=react-dashboard');
    const [events, setEvents] = useState([]);

    useEffect(() => {
        if (lastEvent && lastEvent.type !== 'connection.established') {
            setEvents(prev => [lastEvent, ...prev].slice(0, 50));
        }
    }, [lastEvent]);

    return (
        <div>
            <h1>GatheRing Dashboard</h1>
            <div className={`status ${connected ? 'connected' : 'disconnected'}`}>
                {connected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>

            <div className="events">
                <h2>Live Events</h2>
                {events.map((event, idx) => (
                    <div key={idx} className="event">
                        <div className="event-type">{event.type}</div>
                        <div className="event-data">
                            {JSON.stringify(event.data, null, 2)}
                        </div>
                        <div className="event-time">{event.timestamp}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

## 6. Production Readiness

### 1. Activer HTTPS/WSS

En production, utilisez WSS (WebSocket Secure):

```javascript
const wsUrl = process.env.NODE_ENV === 'production'
    ? 'wss://api.gathering.example.com/ws/dashboard'
    : 'ws://localhost:8000/ws/dashboard';
```

### 2. Reconnexion automatique

```javascript
function connectWithRetry(url, maxRetries = 5) {
    let retries = 0;
    let ws = null;

    function connect() {
        ws = new WebSocket(url);

        ws.onopen = () => {
            console.log('Connected');
            retries = 0; // Reset on successful connection
        };

        ws.onclose = () => {
            if (retries < maxRetries) {
                retries++;
                const delay = Math.min(1000 * Math.pow(2, retries), 30000);
                console.log(`Reconnecting in ${delay}ms... (attempt ${retries})`);
                setTimeout(connect, delay);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    connect();
    return ws;
}

// Usage
const ws = connectWithRetry('ws://localhost:8000/ws/dashboard');
```

### 3. Heartbeat (keep-alive)

```javascript
let heartbeatInterval = null;

ws.onopen = () => {
    // Send ping every 30 seconds
    heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
};

ws.onclose = () => {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
};
```

### 4. Configuration Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name api.gathering.example.com;

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Monitoring

Ajoutez un endpoint pour monitorer les connexions:

```python
# gathering/api.py
from gathering.websocket import get_connection_manager

@app.get("/admin/websocket/stats")
async def websocket_stats():
    manager = get_connection_manager()
    return manager.get_stats()
```

Testez:
```bash
curl http://localhost:8000/admin/websocket/stats
```

Réponse:
```json
{
  "active_connections": 3,
  "total_connections": 15,
  "total_messages_sent": 234,
  "total_broadcasts": 45,
  "clients": [
    {
      "client_id": "dashboard-1",
      "connected_at": "2024-01-15T10:00:00Z",
      "messages_sent": 78
    }
  ]
}
```

## 7. Troubleshooting

### Problème: "Connection refused"

**Cause:** Serveur FastAPI n'est pas démarré

**Solution:**
```bash
uvicorn gathering.api:app --reload
```

### Problème: "404 Not Found"

**Cause:** Route WebSocket pas incluse dans l'application

**Solution:** Vérifier que `gathering/api.py` inclut le router:
```python
from gathering.api.routers import websocket
app.include_router(websocket.router)
```

### Problème: Events ne sont pas reçus

**Cause:** Broadcasting pas activé

**Solution:** Ajouter dans startup:
```python
from gathering.websocket.integration import setup_websocket_broadcasting

@app.on_event("startup")
async def startup():
    setup_websocket_broadcasting()
```

### Problème: Connection se ferme après quelques secondes

**Cause:** Pas de heartbeat

**Solution:** Implémenter ping/pong (voir section Production)

### Problème: "CORS error" dans le navigateur

**Cause:** CORS pas configuré pour WebSocket

**Solution:** CORS ne s'applique pas aux WebSockets (pas de preflight), mais vérifier l'origine:
```python
@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    # Accept connections from specific origins
    origin = websocket.headers.get("origin")
    if origin not in ["http://localhost:3000", "https://app.gathering.example.com"]:
        await websocket.close(code=1008, reason="Unauthorized origin")
        return

    # Continue normally
    await manager.connect(websocket)
    # ...
```

## 8. Next Steps

Une fois le WebSocket fonctionnel:

1. **Intégrer dans dashboard React** - Créer composants réactifs
2. **Ajouter authentification** - JWT dans query params ou headers
3. **Filtrer événements** - Par circle_id, project_id, user permissions
4. **Ajouter notifications** - Toast/snackbar pour événements importants
5. **Optimiser payload** - Compresser gros messages
6. **Load testing** - Tester avec 100+ clients concurrents

## Ressources

- [docs/WEBSOCKET.md](./WEBSOCKET.md) - Documentation complète
- [docs/EVENT_BUS.md](./EVENT_BUS.md) - Documentation Event Bus
- [tests/test_websocket.py](../tests/test_websocket.py) - Tests de référence
- [FastAPI WebSocket Docs](https://fastapi.tiangolo.com/advanced/websockets/)

## Support

Si vous rencontrez des problèmes:
1. Vérifier les logs du serveur (`uvicorn`)
2. Vérifier la console du navigateur (F12)
3. Tester avec `websocat` pour isoler le problème
4. Consulter [docs/WEBSOCKET.md](./WEBSOCKET.md) section Troubleshooting
