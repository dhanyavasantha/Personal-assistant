import os
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "data"
VECTOR_DB_PATH = "rag/faiss_index"


def load_documents():
    documents = []

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={"source": path}
                        )
                    )
    return documents


def ingest():
    docs = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    vectorstore.save_local(VECTOR_DB_PATH)
    print("✅ FAISS index created.")


if __name__ == "__main__":
    ingest()
