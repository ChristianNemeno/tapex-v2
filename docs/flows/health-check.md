# Sequence Diagrams: GET /health and GET /models

## GET /health

Verifies that the Ollama server is reachable and the configured model is loaded.

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Router as ExtractRouter
    participant OC as OllamaClient
    participant Ollama as Ollama Server

    Client->>Router: GET /health
    Router->>OC: health_check()

    alt Ollama reachable
        OC->>Ollama: client.list() → list all models
        Ollama-->>OC: model list
        OC->>OC: check if MODEL_NAME in available models
        OC-->>Router: {ollama: "ok", model: "gemma4:e4b", model_available: true, available_models: [...]}
        Router-->>Client: 200 OK — health dict
    else Ollama unreachable
        OC->>Ollama: client.list()
        Ollama-->>OC: ConnectionError
        OC-->>Router: {ollama: "error", model_available: false, detail: "..."}
        Router-->>Client: 200 OK — error health dict
    end
```

---

## GET /models

Lists all models currently available in the Ollama instance.

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Router as ExtractRouter
    participant OC as OllamaClient
    participant Ollama as Ollama Server

    Client->>Router: GET /models
    Router->>OC: list_models()

    alt Ollama reachable
        OC->>Ollama: client.list()
        Ollama-->>OC: [{name: "gemma4:e4b"}, ...]
        OC->>OC: extract model names
        OC-->>Router: ["gemma4:e4b", ...]
        Router-->>Client: 200 OK — {models: ["gemma4:e4b", ...]}
    else Ollama unreachable
        OC->>Ollama: client.list()
        Ollama-->>OC: ConnectionError / Exception
        OC-->>Router: raises exception
        Router-->>Client: 503 Service Unavailable
    end
```

## Response Comparison

| Endpoint | Success | Failure |
|----------|---------|---------|
| `GET /health` | Always `200` — health status in body indicates ok/error | `200` with `ollama: "error"` |
| `GET /models` | `200` with models list | `503 Service Unavailable` |
