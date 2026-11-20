from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router


app = FastAPI(
    title="Academic Assistant API",
    description="Document-based Question Answering System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4300", "http://127.0.0.1:4300"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)


@app.get("/")
def root():
    return {"message": "Academic Assistant API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
