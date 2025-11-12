# GenAI Car Assistant – Backend (WIP)

This is the backend for our GenAI car assistant capstone project.

Right now, it:

- Takes a **VIN** as input.
- Uses **Auto.dev** to decode the VIN (year, make, model, type, origin, etc.).
- Uses **NHTSA vPIC** to get extra specs (engine displacement, HP, cylinders, etc.).
- Uses **CarQuery** to get trims and fuel economy data and converts it to **MPG**.
- Combines everything into a normalized **car profile**.
- Exposes this via a small **FastAPI** service.

This backend will later be used by our LLM and frontend to answer questions about specific cars.

---

## Project structure (current)

```text
GenAI---Capstone-Project/
  external_apis.py   # All external API calls + helpers + profile builder
  main.py            # FastAPI app (health, /cars/{vin}, /cars/{vin}/summary)
  schemas.py         # Pydantic models for CarProfile (used by FastAPI)
  test_apis.py       # Small script to test external APIs + profile builder
  .env               # Holds AUTO_DEV_API_KEY (NOT committed to git)
  .venv/             # Python virtual environment (NOT committed)
  README.md



Setup
1. Create and activate virtualenv

From the project root:

python -m venv .venv


Windows (PowerShell):

.\.venv\Scripts\Activate.ps1


If that gives an execution policy error, either use Command Prompt:

.\.venv\Scripts\activate.bat


or change execution policy (once):

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned


macOS / Linux:

source .venv/bin/activate


You should see (.venv) at the start of your terminal prompt.

2. Install dependencies

With the virtualenv active:

pip install fastapi uvicorn requests python-dotenv

Environment variables

Create a file named .env in the project root (same level as main.py):

AUTO_DEV_API_KEY=sk_ad_...your_real_key_here...


This key is used by external_apis.py to call the Auto.dev VIN API.

Important: .env should NOT be committed to git. It should be in .gitignore.

How to run the tests (check the APIs)

test_apis.py is a simple script to verify that:

Auto.dev VIN decode works

NHTSA VIN decode works

CarQuery trims and MPG helper work

get_car_profile_from_vin builds a combined profile

Run:

python test_apis.py


You should see output similar to:

=== Auto.dev VIN decode ===
2019 Porsche 911

=== NHTSA decode ===
2019 PORSCHE 911

=== CarQuery trims example (from decoded VIN) ===
[ {...}, {...} ]

=== CarQuery fuel economy via helper ===
{ 'fuel_type': '...', 'city_mpg': ..., ... }

=== Full car profile from VIN ===
{ 'vin': '...', 'year': ..., 'make': '...', 'engine': {...}, 'economy': {...} }


If that works, our external API layer and profile builder are working.

How to run the API server

From the project root (with .venv active):

uvicorn main:app --reload


You should see something like:

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)


Then you can hit these URLs in a browser:

Health check:
http://127.0.0.1:8000/health

Full car profile for a VIN:
http://127.0.0.1:8000/cars/WP0AF2A99KS165242

Short text summary for LLM / UI:
http://127.0.0.1:8000/cars/WP0AF2A99KS165242/summary

Auto-generated docs (Swagger UI):
http://127.0.0.1:8000/docs

To stop the server: Ctrl + C in the terminal running uvicorn.