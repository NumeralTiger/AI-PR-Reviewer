import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Persistent client
persist_directory = "./chroma_data"
chroma_client = chromadb.PersistentClient(path=persist_directory)
collection = chroma_client.get_collection("codebase")

def get_similar_chunks(diff_text, k=5):
    """
    Retrieve k most relevant codebase chunks based on the PR diff using Chroma + OpenAI embeddings.
    """
    embedding = openai_client.embeddings.create(
        input=[diff_text],
        model="text-embedding-3-small"
    ).data[0].embedding

    results = collection.query(query_embeddings=[embedding], n_results=k)
    chunks = results.get("documents", [[]])[0]
    return "\n---\n".join(chunks)
