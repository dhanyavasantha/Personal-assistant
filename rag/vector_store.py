from dotenv import load_dotenv
load_dotenv()
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

VECTOR_DB_PATH = "rag/faiss_index"

_embeddings = None
_vectorstore = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings()
    return _embeddings


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = FAISS.load_local(
            VECTOR_DB_PATH,
            get_embeddings(),
            allow_dangerous_deserialization=True
        )
    return _vectorstore
