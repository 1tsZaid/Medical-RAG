from google import genai
from sentence_transformers import SentenceTransformer
from pinecone_text.sparse import BM25Encoder
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECON_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = "medical-rag"

model = SentenceTransformer('all-MiniLM-L6-v2')

bm25 = BM25Encoder()
bm25.load("bm25_params.json")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

ai_client = genai.Client(api_key=GEMINI_API_KEY)

def request(question: str, alpha: float = 0.8) -> str:

    dense_vector = model.encode(question)
    sparse_vector = bm25.encode_queries(question)

    res = index.query(
        vector=[v * alpha for v in dense_vector],
        top_k=10,
        include_metadata=True,
        sparse_vector={
            "indices": sparse_vector["indices"],
            "values": [v * (1 - alpha) for v in sparse_vector['values']]
        }
    )

    contexts = [
        x['metadata']['text'] for x in res['matches']
    ]

    prompt = f"""
        You are an assistant for diagnosing and treating medical conditions
        Answer the question based only on the following context:
        {contexts}
        You are allowed to rephrase the answer based on the context.
        If the answer isn't contained here, say you don't know.
        Question: {question}
    """

    response = ai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return response.text