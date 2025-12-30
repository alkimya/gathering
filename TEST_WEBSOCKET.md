# Guide de Test WebSocket - GatheRing

Guide rapide pour tester le WebSocket qui vient d'être intégré.

## Option 1: Test avec le Dashboard HTML (Recommandé)

### Étape 1: Démarrer le serveur

```bash
# Terminal 1
source venv/bin/activate
uvicorn gathering.api:app --reload
```

Vous devriez voir:
```
[WebSocket] Broadcasting enabled for 13 event types
WebSocket broadcasting enabled
```

### Étape 2: Ouvrir le dashboard

```bash
# Terminal 2
cd dashboard
python3 -m http.server 8080
```

Puis ouvrez dans votre navigateur:
```
http://localhost:8080/websocket_test.html
```

### Étape 3: Connecter

1. Cliquez sur le bouton **"Connect"**
2. Vous devriez voir "✅ Connected to GatheRing WebSocket"
3. Le statut passe à "Connected" (vert)

### Étape 4: Générer des événements

```bash
# Terminal 3
source venv/bin/activate
python3 test_websocket_integration.py server
```

Vous devriez voir les événements apparaître en temps réel dans le dashboard !

---

## Option 2: Test Programmatique (Python)

### Test simple

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws/dashboard?client_id=test"

    async with websockets.connect(uri) as ws:
        # Connexion
        msg = await ws.recv()
        print(f"Connecté: {json.loads(msg)}")

        # Ping
        await ws.send(json.dumps({"type": "ping"}))
        pong = await ws.recv()
        print(f"Pong: {json.loads(pong)}")

        # Écouter événements (10 sec)
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(msg)
                print(f"Event: {data['type']}")
        except asyncio.TimeoutError:
            print("Timeout")

asyncio.run(test())
```

---

## Option 3: Test avec websocat (CLI)

### Installer websocat

```bash
# macOS
brew install websocat

# Linux
cargo install websocat
```

### Connecter

```bash
websocat ws://localhost:8000/ws/dashboard?client_id=cli-test
```

Vous devriez recevoir:
```json
{
  "type": "connection.established",
  "data": {
    "client_id": "cli-test",
    "message": "Connected to GatheRing WebSocket"
  },
  "timestamp": "..."
}
```

### Envoyer ping

Tapez:
```json
{"type": "ping"}
```

Vous devriez recevoir:
```json
{
  "type": "pong",
  "timestamp": "..."
}
```

---

## Générer des événements de test

### Via Python

```python
from gathering.events import event_bus, Event, EventType
import asyncio

async def publish_events():
    # Agent started
    await event_bus.publish(Event(
        type=EventType.AGENT_STARTED,
        data={"agent_id": 1, "name": "Alice"},
        source_agent_id=1,
    ))

    # Task completed
    await event_bus.publish(Event(
        type=EventType.TASK_COMPLETED,
        data={"task_id": 123, "status": "success"},
        circle_id=1,
    ))

    # Memory created
    await event_bus.publish(Event(
        type=EventType.MEMORY_CREATED,
        data={"content": "Test memory"},
        source_agent_id=1,
    ))

asyncio.run(publish_events())
```

### Via Script automatique

```bash
python3 test_websocket_integration.py server
```

Ce script:
1. Connecte un client WebSocket
2. Publie 5 événements différents
3. Vérifie que le client les reçoit

---

## Vérification

### ✅ Le WebSocket fonctionne si:

1. **Serveur démarre** - Vous voyez "WebSocket broadcasting enabled"
2. **Client connecte** - Message "connection.established" reçu
3. **Ping/Pong fonctionne** - Réponse immédiate au ping
4. **Événements reçus** - Les events publiés arrivent au client
5. **Dashboard réactif** - Les événements apparaissent en temps réel

### ❌ Problèmes potentiels:

**"Connection refused"**
- Le serveur n'est pas démarré
- Solution: `uvicorn gathering.api:app --reload`

**"No events received"**
- Broadcasting pas activé
- Vérifier logs: doit contenir "WebSocket broadcasting enabled"

**"TypeError: ... not JSON serializable"**
- Event data contient objets non sérialisables
- Vérifier que data est dict/list/str/int/float

---

## Prochaines étapes

Une fois le test réussi:

1. **Intégrer au dashboard React** - [QUICKSTART_WEBSOCKET.md](docs/QUICKSTART_WEBSOCKET.md)
2. **Ajouter authentification** - JWT dans query params
3. **Filtrer événements** - Par circle_id, project_id
4. **Monitoring** - Endpoint `/admin/websocket/stats`

---

## Ressources

- [docs/WEBSOCKET.md](docs/WEBSOCKET.md) - Documentation complète
- [docs/QUICKSTART_WEBSOCKET.md](docs/QUICKSTART_WEBSOCKET.md) - Guide détaillé
- [tests/test_websocket.py](tests/test_websocket.py) - Tests de référence

---

**Le WebSocket est prêt à être testé !** 🚀

Bon test !
