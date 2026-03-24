from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"message": "Single Document RAG UI çalışıyor"}


@router.get("/health")
def health():
    return {"status": "ok"}