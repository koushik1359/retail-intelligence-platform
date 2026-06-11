import chromadb
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client     = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
chroma     = chromadb.PersistentClient(path="data/chromadb")
collection = chroma.get_collection("product_catalog")


def answer(question: str, n_results: int = 5) -> str:
    results = collection.query(query_texts=[question], n_results=n_results)
    products = [
        f"- {m['product_name']} ({m['department']}): {doc}"
        for m, doc in zip(results["metadatas"][0], results["documents"][0])
    ]
    context = "\n".join(products)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": f"""You are a helpful retail shopping assistant.
Based on these products from our catalog, answer the customer's question concisely.

Products:
{context}

Customer question: {question}

Answer in 2-3 sentences, mentioning specific products by name."""}],
    )
    return response.content[0].text.strip()


if __name__ == "__main__":
    questions = [
        "What's a good high-protein snack?",
        "I need something for a healthy breakfast",
        "What can I get for a kids lunchbox?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {answer(q)}")
