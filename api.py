from fastapi import FastAPI

app = FastAPI()


@app.get("/test")
def test():
    return {"testing": "OK"}


@app.get("/")
def hello():
    return "HELLO"
