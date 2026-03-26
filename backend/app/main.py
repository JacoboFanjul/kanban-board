from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def root():
    return """<!doctype html>
<html>
<head><title>Project Manager</title></head>
<body><h1>Hello World</h1></body>
</html>"""


@app.get("/api/health")
def health():
    return {"status": "ok"}
