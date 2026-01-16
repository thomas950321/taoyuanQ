import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import shutil
import logging
from typing import List

# LangChain Imports
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_docling import DoclingLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from docling.document_converter import DocumentConverter

# Local Imports
# Reuse the robust link finding logic from scraper.py
from scraper import get_all_links 
import requests

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CHROMA_PATH = "chroma_db"
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

# Global variables for Singleton pattern
_RETRIEVER = None
_VECTORSTORE = None
_DOCSTORE = None

def init_rag_pipeline(rebuild=False):
    """
    Initialize the RAG pipeline components.
    """
    global _RETRIEVER, _VECTORSTORE, _DOCSTORE

    if _RETRIEVER and not rebuild:
        return _RETRIEVER

    logger.info("Initializing RAG Pipeline...")

    # 1. Embeddings Model
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", # Or similar depending on provider
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL
    )

    # 2. Vector Store (Chroma)
    if rebuild and os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logger.info("Cleared existing vector store.")

    _VECTORSTORE = Chroma(
        collection_name="taoyuanq_docs",
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH
    )

    # 3. Doc Store (InMemory for now, ideally Redis for production)
    _DOCSTORE = InMemoryStore()

    # 4. Splitters
    # Parent splitter: Keep larger context (e.g., full sections)
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    
    # Child splitter: Small chunks for precise retrieval
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)

    # 5. ParentDocumentRetriever
    _RETRIEVER = ParentDocumentRetriever(
        vectorstore=_VECTORSTORE,
        docstore=_DOCSTORE,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    
    return _RETRIEVER

def fetch_and_process_website():
    """
    Crawl, Parse, Chunk, and Index content.
    """
    base_url = "https://a18.taoyuanq.com/zh"
    logger.info(f"Starting crawl from {base_url}...")

    # 1. Discover all links
    try:
        resp = requests.get(base_url, headers={"User-Agent": "Bot"}, timeout=10)
        all_urls = get_all_links(base_url, resp.text)
        all_urls.add(base_url)
        logger.info(f"Found {len(all_urls)} pages.")
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        return

    # 2. Docling Conversion & Semantic Chunking
    converter = DocumentConverter()
    
    # We use Semantic Chunker to pre-process before feeding into ParentRetriever
    # Note: ParentRetriever does its own splitting usually, but we can feed it documents 
    # that are already somewhat distinct (by page).
    
    rag_documents = []

    for url in all_urls:
        try:
            logger.info(f"Processing {url}...")
            # Docling conversion
            # Note: DocumentConverter might be slow or blocking.
            conv_res = converter.convert(url)
            markdown_content = conv_res.document.export_to_markdown()
            
            if not markdown_content.strip():
                continue

            # Create a Document object
            doc = Document(
                page_content=markdown_content,
                metadata={"source": url}
            )
            rag_documents.append(doc)
            
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")

    # 3. Ingest into Retriever
    if rag_documents:
        retriever = init_rag_pipeline()
        logger.info(f"Ingesting {len(rag_documents)} documents into vector store...")
        retriever.add_documents(rag_documents)
        logger.info("Ingestion complete.")
    else:
        logger.warning("No documents to ingest.")

def query_rag_advanced(question, return_usage=False):
    """
    Retrieve context and generate answer.
    """
    retriever = init_rag_pipeline()
    
    # 1. Retrieve relevant docs (Parent Documents)
    # This returns the LARGE chunks (Parents) matched by SMALL chunks (Children)
    docs = retriever.invoke(question)
    
    # Combine content
    context_text = "\n\n".join([f"--- Source: {d.metadata.get('source', 'Unknown')} ---\n{d.page_content}" for d in docs])
    
    logger.info(f"Retrieved {len(docs)} parent documents. Context size: {len(context_text)} chars.")

    # 2. Generate Answer
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        tags=["experiment_rag"]
    )
    
    system_prompt = f"""
# Role: 2025桃園Q・活動超級嚮導 (Taoyuan Q Super Guide)

你現在是「2025桃園Q」活動的專屬 AI 嚮導，性格熱情洋溢、精打細算且充滿活力。你的口號是 "High Five! Go FunZone!"。
你的任務是根據使用者提供的【網站抓取資料】，回答關於活動、地點、優惠與行程的問題。

# Input Data
以下是針對使用者問題筛选出的相關官網內容 (已保留完整網頁內容)：
\"\"\"
{context_text}
\"\"\"

# Response Guidelines (回答準則 - LINE OA 專用版)

1.  **手機版面優化 (Mobile First)**：
    *   **短段落**：手機螢幕窄，每段不要超過 3-4 行。
    *   **善用換行**：不同主題之間務必空一行。

2.  **格式嚴格限制 (Plain Text ONLY)**：
    *   ❌ **絕對禁止**：任何 Markdown 語法（如 **粗體**、# 標題、[連結](...)）。
    *   ❌ **絕對禁止**：使用星號 (*) 做條列。
    *   ✅ **請使用**：全形符號或 Emoji 來條列（如 「・」、「📍」、「✨」）。

3.  **語氣與結構**：
    *   **熱情夥伴**：像個旅遊達人朋友，High 起來！(口號: "High Five! Go FunZone!")
    *   **結構化導覽**：
        📍 【去哪裡玩】
        💰 【優惠攻略】
        🚄 【交通/其他】
    *   **行動呼籲**：提醒「上傳發票」、「最後期限」。

4.  **內容邊界**：
    *   只回答輸入資料 (Input Data) 裡有的。
    *   若無資料，請婉拒並引導至現場服務台，不要瞎掰。
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    response = llm.invoke(messages)
    if return_usage:
        return response.content, response.response_metadata.get('token_usage', {})
    return response.content

if __name__ == "__main__":
    # Test execution
    # Initialize and rebuild the database for the first run
    init_rag_pipeline(rebuild=True)
    fetch_and_process_website()
    print("Test Query:")
    print(query_rag_advanced("我今天跟朋友三個人去吃飯逛街，打算花 2500 元，這樣我們可以抽獎嗎？"))
