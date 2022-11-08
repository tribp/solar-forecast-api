from fastapi import FastAPI, HTTPException


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello wizzkid"}

