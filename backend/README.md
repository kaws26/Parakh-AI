# Viva Voce Backend

FastAPI backend service for AI-Based Viva Voce System.

## Tests

Run the default suite with `python -m pytest`. The live Groq check is skipped unless explicitly enabled, so configured API credentials do not cause the normal suite to make network requests.

To run the live check deliberately, set `RUN_GROQ_INTEGRATION=1` and run the integration test:

```powershell
$env:RUN_GROQ_INTEGRATION = "1"
python -m pytest -m integration tests/test_groq.py
```

```sh
RUN_GROQ_INTEGRATION=1 python -m pytest -m integration tests/test_groq.py
```

The integration test skips with a clear reason if `GROQ_API_KEY` is not configured.
