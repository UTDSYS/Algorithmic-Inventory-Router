# Inventory Router

This is a web game where a human player competes against optimization algorithms
at the Inventory Routing Problem (delivering stock from a depot/main hub to
stores under uncertain demand, at the lowest total cost possible). This project has a reusable simulation core
that a reinforcement-learning agent can train on later.


## Development

Backend (Python core + API) — `src/`:

```
cd src
source .venv/bin/activate        # virtualenv with deps installed
pytest                            # once tests exist
uvicorn api.server:app --reload   # once the API is implemented
```

Web (frontend) — `web/`:

```
cd web
npm install
npm run dev
```
