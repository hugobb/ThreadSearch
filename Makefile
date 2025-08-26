.PHONY: setup dev backend frontend clean

# One-time local setup
setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements.txt
	cd frontend && cp -n .env.example .env || true && npm i && npm run shadcn:setup

# Run both servers (use two terminals if your shell can't multiprocess)
dev:
	( . .venv/bin/activate; cd backend; uvicorn app:app --host 127.0.0.1 --port 8000 --reload ) & \
	( cd frontend; npm run dev )

backend:
	. .venv/bin/activate && cd backend && uvicorn app:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd frontend && npm run dev

clean:
	rm -rf .venv backend/.cache frontend/node_modules frontend/.next
