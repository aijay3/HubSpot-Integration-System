"""
RAG (Retrieval-Augmented Generation) System using Supabase
This module provides vector storage and retrieval capabilities using Supabase pgvector.
"""
import os
from typing import List, Dict, Optional, Any
from loguru import logger
import openai
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import hashlib


class SupabaseVectorStore:
    """Vector store using Supabase pgvector extension"""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        table_name: str = "documents",
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize Supabase vector store

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            openai_api_key: OpenAI API key for embeddings
            table_name: Name of the table to store documents
            embedding_model: OpenAI embedding model to use
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.table_name = table_name
        self.embedding_model = embedding_model

        # Initialize Supabase client
        self.client: Client = create_client(supabase_url, supabase_key)

        # Initialize OpenAI client
        openai.api_key = openai_api_key

        logger.info(f"Initialized Supabase vector store with table: {table_name}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding
        """
        try:
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def _generate_doc_id(self, content: str, metadata: Dict) -> str:
        """Generate unique document ID based on content and metadata"""
        hash_input = f"{content}{json.dumps(metadata, sort_keys=True)}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[str]:
        """
        Add documents to the vector store

        Args:
            documents: List of documents with 'content' and 'metadata' keys
            batch_size: Number of documents to process in each batch

        Returns:
            List of document IDs that were added
        """
        added_ids = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            for doc in batch:
                try:
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})

                    # Generate embedding
                    embedding = self._generate_embedding(content)

                    # Generate document ID
                    doc_id = self._generate_doc_id(content, metadata)

                    # Insert into Supabase
                    data = {
                        "id": doc_id,
                        "content": content,
                        "metadata": metadata,
                        "embedding": embedding
                    }

                    # Upsert (insert or update)
                    self.client.table(self.table_name).upsert(data).execute()
                    added_ids.append(doc_id)

                except Exception as e:
                    logger.error(f"Error adding document: {e}")
                    continue

            logger.info(f"Added batch of {len(batch)} documents")

        logger.info(f"Successfully added {len(added_ids)} documents to vector store")
        return added_ids

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity

        Args:
            query: Query text
            k: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of documents with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Use Supabase RPC function for vector similarity search
            # This requires a custom SQL function to be created in Supabase
            result = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": k,
                    "filter": filter_metadata or {}
                }
            ).execute()

            documents = result.data if result.data else []
            logger.info(f"Found {len(documents)} similar documents")
            return documents

        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            # Fallback to simple retrieval without vector search
            try:
                result = self.client.table(self.table_name).select("*").limit(k).execute()
                return result.data if result.data else []
            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {fallback_error}")
                return []

    def delete_documents(self, doc_ids: List[str]) -> bool:
        """
        Delete documents by IDs

        Args:
            doc_ids: List of document IDs to delete

        Returns:
            True if successful
        """
        try:
            self.client.table(self.table_name).delete().in_("id", doc_ids).execute()
            logger.info(f"Deleted {len(doc_ids)} documents")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    def get_document_count(self) -> int:
        """Get total number of documents in the store"""
        try:
            result = self.client.table(self.table_name).select("id", count="exact").execute()
            return result.count if result.count else 0
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0


class RAGKnowledgeBase:
    """RAG-based knowledge base for HubSpot integration using Supabase"""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        table_name: str = "hubspot_knowledge"
    ):
        """
        Initialize RAG knowledge base

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            openai_api_key: OpenAI API key
            table_name: Table name for storing documents
        """
        self.vector_store = SupabaseVectorStore(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key,
            table_name=table_name
        )
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key

        logger.info("RAG Knowledge Base initialized")

    def load_documents_from_directory(
        self,
        directory: str,
        file_extension: str = ".md"
    ) -> List[Dict[str, Any]]:
        """
        Load documents from a directory

        Args:
            directory: Directory path containing documents
            file_extension: File extension to filter (default: .md)

        Returns:
            List of document dictionaries
        """
        documents = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(file_extension):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Split into chunks if content is too large
                        chunks = self._split_text(content)

                        for i, chunk in enumerate(chunks):
                            documents.append({
                                "content": chunk,
                                "metadata": {
                                    "source": file_path,
                                    "filename": file,
                                    "chunk": i,
                                    "total_chunks": len(chunks)
                                }
                            })
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")

        logger.info(f"Loaded {len(documents)} document chunks from {directory}")
        return documents

    def _split_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - chunk_overlap

        return chunks

    def initialize_knowledge_base(self, docs_directory: str = "./docs"):
        """
        Initialize knowledge base by loading documents

        Args:
            docs_directory: Directory containing documentation files
        """
        logger.info(f"Initializing knowledge base from {docs_directory}")

        # Load documents
        documents = self.load_documents_from_directory(docs_directory)

        # Add to vector store
        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Knowledge base initialized with {len(documents)} documents")
        else:
            logger.warning("No documents found to initialize knowledge base")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def query(
        self,
        question: str,
        k: int = 4,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """
        Query the knowledge base with RAG

        Args:
            question: User's question
            k: Number of similar documents to retrieve
            model: OpenAI model to use for generation

        Returns:
            Dictionary with answer and sources
        """
        try:
            # Retrieve relevant documents
            similar_docs = self.vector_store.similarity_search(question, k=k)

            if not similar_docs:
                return {
                    "answer": "I don't have enough information to answer that question.",
                    "sources": []
                }

            # Build context from retrieved documents
            context = "\n\n".join([
                f"Document {i+1}:\n{doc.get('content', '')}"
                for i, doc in enumerate(similar_docs)
            ])

            # Generate answer using OpenAI
            prompt = f"""You are an expert marketing operations assistant.
You help manage HubSpot integration, CRM attribution, ad platform signaling, and governance.

Use the following context to answer the question. If you don't know the answer based on the context,
just say so. Don't make up information.

Context:
{context}

Question: {question}

Answer:"""

            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful marketing operations assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )

            answer = response.choices[0].message.content

            # Extract sources
            sources = [
                {
                    "filename": doc.get("metadata", {}).get("filename", "unknown"),
                    "source": doc.get("metadata", {}).get("source", "unknown")
                }
                for doc in similar_docs
            ]

            return {
                "answer": answer,
                "sources": sources,
                "retrieved_docs": len(similar_docs)
            }

        except Exception as e:
            logger.error(f"Error querying knowledge base: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "sources": []
            }

    def add_custom_document(self, content: str, metadata: Dict[str, Any]):
        """
        Add a custom document to the knowledge base

        Args:
            content: Document content
            metadata: Document metadata
        """
        document = {
            "content": content,
            "metadata": metadata
        }
        self.vector_store.add_documents([document])
        logger.info("Added custom document to knowledge base")

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return {
            "total_documents": self.vector_store.get_document_count(),
            "table_name": self.vector_store.table_name
        }


# SQL function to create in Supabase for vector similarity search
SUPABASE_VECTOR_SEARCH_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table with vector column
CREATE TABLE IF NOT EXISTS hubspot_knowledge (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),  -- OpenAI text-embedding-3-small produces 1536 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster similarity search
CREATE INDEX IF NOT EXISTS hubspot_knowledge_embedding_idx
ON hubspot_knowledge USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    filter JSONB DEFAULT '{}'
)
RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hubspot_knowledge.id,
        hubspot_knowledge.content,
        hubspot_knowledge.metadata,
        1 - (hubspot_knowledge.embedding <=> query_embedding) AS similarity
    FROM hubspot_knowledge
    WHERE (filter = '{}' OR hubspot_knowledge.metadata @> filter)
    ORDER BY hubspot_knowledge.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
