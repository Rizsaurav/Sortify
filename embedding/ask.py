#!/usr/bin/env python3
"""
Simple CLI client to ask questions to the Sortify RAG system.
Works with the running API service.

Usage:
    python ask.py "What is machine learning?"
    python ask.py --interactive
"""

import sys
import argparse
import requests
from typing import Dict, Optional
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"

class RAGClient:
    """Client for interacting with the RAG API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        """Initialize the client."""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def check_health(self) -> Dict:
        """Check if the API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot connect to API at {self.base_url}. Is the server running?")
        except Exception as e:
            raise Exception(f"Health check failed: {e}")
    
    def ask_question(self, question: str, top_k: Optional[int] = None) -> Dict:
        """Ask a question to the RAG system."""
        payload = {"question": question}
        if top_k:
            payload["top_k"] = top_k
        
        response = self.session.post(
            f"{self.base_url}/ask",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def search_documents(self, query: str, top_k: Optional[int] = None) -> Dict:
        """Search for similar document chunks."""
        payload = {"query": query}
        if top_k:
            payload["top_k"] = top_k
        
        response = self.session.post(
            f"{self.base_url}/search",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict:
        """Get processing status."""
        response = self.session.get(f"{self.base_url}/status", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def list_documents(self) -> Dict:
        """List all available documents."""
        response = self.session.get(f"{self.base_url}/documents", timeout=5)
        response.raise_for_status()
        return response.json()

def print_section(title: str, char: str = "="):
    """Print a formatted section."""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}")

def ask_single_question(client: RAGClient, question: str, top_k: Optional[int] = None):
    """Ask a single question and display the answer."""
    try:
        print_section(f"Question: {question}", "-")
        print("Thinking...\n")
        
        result = client.ask_question(question, top_k)
        
        # Display answer
        print("📝 ANSWER:")
        print("-" * 60)
        print(result['answer'])
        print("-" * 60)
        
        # Display metadata
        print(f"\n📊 METADATA:")
        print(f"  ⏱️  Response Time: {result['response_time']:.2f}s")
        print(f"  📚 Sources: {', '.join(result['sources'])}")
        print(f"  🔢 Chunks Used: {result['chunks_used']}")
        print(f"  🔄 Fallback Used: {'Yes' if result['fallback_used'] else 'No'}")
        
        return result
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def interactive_mode(client: RAGClient):
    """Run interactive question-answering session."""
    print_section("🤖 Interactive Q&A Mode")
    print("Ask questions about your documents.")
    print("Commands:")
    print("  - Type your question and press Enter")
    print("  - 'search <query>' to search for similar chunks")
    print("  - 'docs' to list available documents")
    print("  - 'status' to see system status")
    print("  - 'quit' or 'exit' to quit")
    print("-" * 60)
    
    while True:
        try:
            # Get user input
            user_input = input("\n❓ You: ").strip()
            
            # Handle empty input
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            elif user_input.lower() == 'status':
                status = client.get_status()
                print(f"\n📊 System Status:")
                print(f"  - Status: {status['status']}")
                print(f"  - Documents: {status['documents']}")
                print(f"  - Chunks: {status['chunks']}")
                print(f"  - Ready: {status['ready']}")
                continue
            
            elif user_input.lower() == 'docs':
                docs = client.list_documents()
                print(f"\n📚 Available Documents ({docs['count']}):")
                for doc in docs['documents']:
                    print(f"  - {doc}")
                continue
            
            elif user_input.lower().startswith('search '):
                query = user_input[7:].strip()
                print(f"\n🔍 Searching for: {query}")
                results = client.search_documents(query, top_k=3)
                
                if results['results']:
                    print(f"\nFound {len(results['results'])} results:")
                    for i, result in enumerate(results['results'], 1):
                        print(f"\n--- Result {i} (Score: {result['score']:.4f}) ---")
                        print(f"Source: {result['source']}")
                        print(f"Content: {result['content'][:200]}...")
                else:
                    print("No results found.")
                continue
            
            # Ask question
            print("\n💭 AI Assistant:")
            result = client.ask_question(user_input)
            print(f"{result['answer']}")
            
            # Show sources
            if result['sources'] and not result['fallback_used']:
                print(f"\n📚 Sources: {', '.join(result['sources'])}")
            
            print(f"⏱️  ({result['response_time']:.2f}s)")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

def show_status(client: RAGClient):
    """Show system status."""
    try:
        print_section("System Status")
        
        # Health check
        health = client.check_health()
        print(f"✅ API Status: {health['status']}")
        print(f"  - Version: {health['version']}")
        print(f"  - Ready: {health['ready']}")
        print(f"  - Documents: {health['documents_loaded']}")
        print(f"  - Chunks: {health['chunks_available']}")
        
        # Processing status
        status = client.get_status()
        print(f"\n📊 Processing Status: {status['status']}")
        if status.get('processing_time'):
            print(f"  - Processing Time: {status['processing_time']:.2f}s")
        print(f"  - Loaded from Cache: {status.get('loaded_from_cache', False)}")
        
        # Documents
        docs = client.list_documents()
        print(f"\n📚 Documents ({docs['count']}):")
        for doc in docs['documents']:
            print(f"  - {doc}")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Ask questions to the Sortify RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ask.py "What is machine learning?"
  python ask.py --interactive
  python ask.py --search "deep learning"
  python ask.py --status
  python ask.py --url http://localhost:8000
        """
    )
    
    parser.add_argument('question', nargs='?', help='Question to ask')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='Interactive mode')
    parser.add_argument('-s', '--search', metavar='QUERY', 
                       help='Search for similar chunks')
    parser.add_argument('--status', action='store_true', 
                       help='Show system status')
    parser.add_argument('--top-k', type=int, default=5, 
                       help='Number of top results (default: 5)')
    parser.add_argument('--url', default=API_BASE_URL, 
                       help=f'API base URL (default: {API_BASE_URL})')
    
    args = parser.parse_args()
    
    # Create client
    client = RAGClient(args.url)
    
    # Check if API is running
    try:
        client.check_health()
    except ConnectionError as e:
        print(f"❌ {e}")
        print(f"\nPlease start the API server first:")
        print(f"  python start.py --mode api")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        sys.exit(1)
    
    # Route to appropriate function
    try:
        if args.status:
            show_status(client)
        
        elif args.search:
            print_section(f"Searching: {args.search}")
            results = client.search_documents(args.search, top_k=args.top_k)
            
            if results['results']:
                print(f"\nFound {len(results['results'])} results in {results['response_time']:.2f}s:\n")
                for i, result in enumerate(results['results'], 1):
                    print(f"{'='*60}")
                    print(f"Result {i} - Score: {result['score']:.4f}")
                    print(f"Source: {result['source']}")
                    print(f"{'='*60}")
                    print(result['content'])
                    print()
            else:
                print("❌ No results found.")
        
        elif args.interactive:
            interactive_mode(client)
        
        elif args.question:
            ask_single_question(client, args.question, top_k=args.top_k)
        
        else:
            parser.print_help()
            print("\n💡 Tip: Try 'python ask.py --interactive' for interactive mode")
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

