#!/usr/bin/env python3
"""
Terminal-based Q&A interface for Sortify RAG System.
Optimized for students to ask questions about their study documents.

Features:
- Works directly with the RAG system (no API needed)
- Handles all documents in storage
- Rich terminal interface with colors
- Command history and auto-completion
- Statistics and performance metrics
- Robust error handling
"""

import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import RAGConfig
from rag_system import FastRAG

# ANSI color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colored(text: str, color: str) -> str:
    """Return colored text for terminal."""
    return f"{color}{text}{Colors.END}"

class QATerminal:
    """Terminal-based Q&A interface for RAG system."""
    
    def __init__(self):
        """Initialize the terminal interface."""
        self.config = None
        self.rag = None
        self.question_count = 0
        self.total_response_time = 0.0
        self.session_start = time.time()
        self.question_history: List[Dict] = []
        self.enable_cache = True
        self.response_cache = {}  # In-memory cache for instant responses
        
    def print_header(self):
        """Print welcome header."""
        print("\n" + "="*70)
        print(colored("🎓 SORTIFY RAG - Study Document Q&A System", Colors.BOLD + Colors.CYAN))
        print(colored("   Ask questions about your study documents", Colors.BLUE))
        print("="*70)
        
    def print_section(self, title: str, char: str = "-"):
        """Print a section divider."""
        print(f"\n{char * 70}")
        print(colored(f"  {title}", Colors.BOLD))
        print(f"{char * 70}")
    
    def initialize_system(self) -> bool:
        """Initialize the RAG system."""
        try:
            print(colored("\n⚙️  Initializing RAG system...", Colors.YELLOW))
            
            # Load configuration
            self.config = RAGConfig.from_env()
            print(colored("  ✓ Configuration loaded", Colors.GREEN))
            
            # Initialize RAG system
            self.rag = FastRAG(self.config)
            print(colored("  ✓ Models loaded", Colors.GREEN))
            print(colored("  ✓ System initialized", Colors.GREEN))
            
            # Process documents (load from cache if available)
            print(colored("\n📚 Processing documents...", Colors.YELLOW))
            stats = self.rag.process_documents()
            
            if stats['ready']:
                cached = " (cached)" if stats.get('loaded_from_cache', False) else ""
                print(colored(f"  ✓ Ready! {stats['documents']} documents → {stats['chunks']} chunks{cached}", Colors.GREEN))
                print(colored(f"  ⏱️  Processing time: {stats['processing_time']:.2f}s", Colors.BLUE))
                
                # Show document details
                self._show_document_list()
                return True
            else:
                print(colored("  ✗ Failed to process documents", Colors.RED))
                return False
                
        except Exception as e:
            print(colored(f"\n❌ Error initializing system: {e}", Colors.RED))
            import traceback
            traceback.print_exc()
            return False
    
    def _show_document_list(self):
        """Show list of loaded documents."""
        if not self.rag or not self.rag.chunks:
            return
        
        # Get unique document sources
        sources = sorted(set(chunk.source for chunk in self.rag.chunks))
        
        print(colored(f"\n📄 Loaded Documents ({len(sources)}):", Colors.CYAN))
        for i, source in enumerate(sources, 1):
            # Count chunks per document
            chunk_count = sum(1 for chunk in self.rag.chunks if chunk.source == source)
            print(f"  {i}. {colored(source, Colors.BOLD)} ({chunk_count} chunks)")
    
    def show_help(self):
        """Show help message with available commands."""
        self.print_section("📖 Available Commands")
        
        commands = [
            ("ask <question>", "Ask a question about your documents"),
            ("<question>", "Direct question (no 'ask' needed)"),
            ("search <query>", "Search for specific content"),
            ("docs", "List all loaded documents"),
            ("stats", "Show session statistics"),
            ("storage", "Show storage information"),
            ("history", "Show question history"),
            ("clear", "Clear the screen"),
            ("help", "Show this help message"),
            ("quit / exit", "Exit the program"),
        ]
        
        for cmd, desc in commands:
            print(f"  {colored(cmd, Colors.CYAN):30} - {desc}")
        
        print(f"\n💡 {colored('Tip:', Colors.YELLOW)} Just type your question naturally!")
    
    def show_statistics(self):
        """Show session statistics."""
        self.print_section("📊 Session Statistics")
        
        session_duration = time.time() - self.session_start
        avg_response_time = self.total_response_time / self.question_count if self.question_count > 0 else 0
        
        print(f"  Questions Asked: {colored(str(self.question_count), Colors.GREEN)}")
        print(f"  Session Duration: {colored(f'{session_duration:.1f}s', Colors.BLUE)}")
        print(f"  Avg Response Time: {colored(f'{avg_response_time:.2f}s', Colors.BLUE)}")
        print(f"  Documents Loaded: {colored(str(len(set(c.source for c in self.rag.chunks))), Colors.GREEN)}")
        print(f"  Total Chunks: {colored(str(len(self.rag.chunks)), Colors.GREEN)}")
    
    def show_storage_info(self):
        """Show storage information."""
        self.print_section("💾 Storage Information")
        storage_dir = Path(self.config.embeddings_storage_path)
        emb_file = storage_dir / "document_embeddings.npy"
        if emb_file.exists():
            size_mb = emb_file.stat().st_size / 1024 / 1024
            print(f"  Embeddings: {colored(f'{size_mb:.2f} MB', Colors.GREEN)}")
            print(f"  Chunks: {colored(str(len(self.rag.chunks)), Colors.CYAN)}")
        else:
            print(colored("  No embeddings found", Colors.YELLOW))
    
    def show_history(self):
        """Show question history."""
        if not self.question_history:
            print(colored("\n📝 No questions asked yet.", Colors.YELLOW))
            return
        
        self.print_section(f"📝 Question History ({len(self.question_history)})")
        
        for i, entry in enumerate(self.question_history[-10:], 1):  # Show last 10
            print(f"\n  {colored(f'Q{i}:', Colors.CYAN)} {entry['question']}")
            print(f"       {colored('→', Colors.BLUE)} {entry['answer'][:100]}...")
            print(f"       {colored('⏱', Colors.YELLOW)}  {entry['response_time']:.2f}s | {colored('📚', Colors.GREEN)} {', '.join(entry['sources'][:2])}")
    
    def search_documents(self, query: str, top_k: int = 5):
        """Search for specific content in documents."""
        try:
            print(colored(f"\n🔍 Searching for: '{query}'", Colors.YELLOW))
            
            results = self.rag.search(query, top_k=top_k)
            
            if not results:
                print(colored("  No results found.", Colors.RED))
                return
            
            print(colored(f"\n  Found {len(results)} results:", Colors.GREEN))
            
            for i, result in enumerate(results, 1):
                print(f"\n  {colored(f'[Result {i}]', Colors.BOLD)} Score: {result.score:.4f}")
                print(f"  Source: {colored(result.chunk.source, Colors.CYAN)}")
                print(f"  {'-' * 66}")
                # Show first 200 characters
                content = result.chunk.content[:200] + "..." if len(result.chunk.content) > 200 else result.chunk.content
                print(f"  {content}")
                
        except Exception as e:
            print(colored(f"\n❌ Search error: {e}", Colors.RED))
    
    def ask_question(self, question: str):
        """Ask a question and display the answer."""
        try:
            # Visual feedback
            print(colored(f"\n❓ Question: {question}", Colors.CYAN))
            
            # Check cache first
            cache_key = question.lower().strip()
            if self.enable_cache and cache_key in self.response_cache:
                print(colored("⚡ Retrieved from cache (instant)", Colors.GREEN))
                result = self.response_cache[cache_key].copy()
                result['response_time'] = 0.0
                result['from_cache'] = True
            else:
                print(colored("💭 Thinking...", Colors.YELLOW))
                
                # Get answer
                start_time = time.time()
                result = self.rag.answer_question(question)
                response_time = result['response_time']
                
                # Cache the result (if not an error)
                if self.enable_cache and 'Error' not in result.get('answer', ''):
                    self.response_cache[cache_key] = result.copy()
            
            response_time = result['response_time']
            
            # Update statistics
            self.question_count += 1
            self.total_response_time += response_time
            
            # Store in history
            self.question_history.append({
                'question': question,
                'answer': result['answer'],
                'sources': result['sources'],
                'response_time': response_time,
                'timestamp': datetime.now().isoformat(),
                'chunks_used': result['chunks_used'],
                'fallback_used': result['fallback_used'],
                'from_cache': result.get('from_cache', False)
            })
            
            # Display answer
            print(f"\n{colored('✨ Answer:', Colors.GREEN + Colors.BOLD)}")
            print(f"{'-' * 70}")
            print(result['answer'])
            print(f"{'-' * 70}")
            
            # Display metadata
            print(f"\n{colored('📊 Metadata:', Colors.BLUE)}")
            
            # Show cache status
            if result.get('from_cache', False):
                print(f"  ⚡ Response Time: {colored('0.00s (cached)', Colors.GREEN)}")
            else:
                print(f"  ⏱️  Response Time: {colored(f'{response_time:.2f}s', Colors.YELLOW)}")
            
            print(f"  📚 Sources: {colored(', '.join(result['sources']), Colors.CYAN)}")
            print(f"  🔢 Chunks Used: {colored(str(result['chunks_used']), Colors.GREEN)}")
            
            if result['fallback_used']:
                print(f"  {colored('🔄 Used general knowledge (no relevant docs found)', Colors.YELLOW)}")
            
        except Exception as e:
            print(colored(f"\n❌ Error answering question: {e}", Colors.RED))
            import traceback
            traceback.print_exc()
    
    def handle_command(self, user_input: str) -> bool:
        """Handle user commands. Returns False to exit."""
        user_input = user_input.strip()
        
        # Empty input
        if not user_input:
            return True
        
        # Convert to lowercase for command matching
        cmd_lower = user_input.lower()
        
        # Exit commands
        if cmd_lower in ['quit', 'exit', 'q', 'bye']:
            return False
        
        # Help command
        elif cmd_lower in ['help', '?', 'h']:
            self.show_help()
        
        # Stats command
        elif cmd_lower in ['stats', 'statistics']:
            self.show_statistics()
        
        # Storage command
        elif cmd_lower in ['storage', 'store']:
            self.show_storage_info()
        
        # History command
        elif cmd_lower in ['history', 'hist']:
            self.show_history()
        
        # Documents list command
        elif cmd_lower in ['docs', 'documents', 'list']:
            self._show_document_list()
        
        # Clear command
        elif cmd_lower in ['clear', 'cls']:
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_header()
        
        # Search command
        elif cmd_lower.startswith('search '):
            query = user_input[7:].strip()
            if query:
                self.search_documents(query)
            else:
                print(colored("  Usage: search <query>", Colors.YELLOW))
        
        # Ask command (explicit)
        elif cmd_lower.startswith('ask '):
            question = user_input[4:].strip()
            if question:
                self.ask_question(question)
            else:
                print(colored("  Usage: ask <question>", Colors.YELLOW))
        
        # Direct question (anything else)
        else:
            self.ask_question(user_input)
        
        return True
    
    def run_interactive(self):
        """Run the interactive terminal session."""
        self.print_header()
        
        # Initialize system
        if not self.initialize_system():
            print(colored("\n❌ Failed to initialize system. Exiting.", Colors.RED))
            return
        
        # Show help
        print(colored("\n💡 Type 'help' for commands or just ask a question!", Colors.YELLOW))
        
        # Main loop
        print()
        while True:
            try:
                # Get user input
                prompt = colored("\n🎓 You: ", Colors.BOLD + Colors.CYAN)
                user_input = input(prompt).strip()
                
                # Handle command
                if not self.handle_command(user_input):
                    break
                    
            except KeyboardInterrupt:
                print(colored("\n\n⚠️  Interrupted by user", Colors.YELLOW))
                break
            except EOFError:
                print(colored("\n\n👋 Goodbye!", Colors.BLUE))
                break
            except Exception as e:
                print(colored(f"\n❌ Unexpected error: {e}", Colors.RED))
                import traceback
                traceback.print_exc()
        
        # Show final statistics
        if self.question_count > 0:
            print()
            self.show_statistics()
        
        print(colored("\n👋 Thank you for using Sortify RAG! Happy studying! 📚", Colors.GREEN + Colors.BOLD))
        print()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sortify RAG Terminal Q&A Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qa_terminal.py                    # Start interactive mode
  python qa_terminal.py "What is AI?"      # Ask single question
  python qa_terminal.py --search "ML"      # Search documents
        """
    )
    
    parser.add_argument('question', nargs='?', help='Ask a single question')
    parser.add_argument('--search', metavar='QUERY', help='Search documents')
    
    args = parser.parse_args()
    
    terminal = QATerminal()
    
    # Single question mode
    if args.question:
        terminal.print_header()
        if terminal.initialize_system():
            terminal.ask_question(args.question)
    # Search mode
    elif args.search:
        terminal.print_header()
        if terminal.initialize_system():
            terminal.search_documents(args.search)
    # Interactive mode (default)
    else:
        terminal.run_interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\n\n👋 Interrupted. Goodbye!", Colors.YELLOW))
        sys.exit(0)
    except Exception as e:
        print(colored(f"\n❌ Fatal error: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        sys.exit(1)

