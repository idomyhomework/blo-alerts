from fastapi import FastAPI

app = FastAPI(
    title="Sistema de Avisos Municipales",
    version="0.1.0",
)


@app.get("/healthz")
async def health():
    return {"status": "ok"}
