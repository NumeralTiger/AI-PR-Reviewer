import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("codebase")

def get_files(path):
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith((".js", ".ts", ".py", ".java")):
                yield os.path.join(root, f)

def chunk_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

def embed(texts):
    return openai_client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    ).data

print("Indexing codebase...")
for file in get_files("your_repo_path_here"):
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        chunks = chunk_text(f.read())
        embeddings = embed(chunks)
        for chunk, emb in zip(chunks, embeddings):
            collection.add(
                documents=[chunk],
                embeddings=[emb.embedding],
                ids=[f"{file}-{chunks.index(chunk)}"]
            )
print("Done.")
