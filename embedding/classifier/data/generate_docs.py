"""
MAXIMUM DIVERSITY Document Generator
=====================================
Generates 2,600 documents (20 per category) with MAXIMUM variety.

Features:
- 20 variations per category = 2,600 total documents
- Randomized prompts within each category
- 9 tone variations
- 8 format styles
- Multi-lingual content (5%)
- Realistic noise (15%)
- Variable word counts
- Content validation

Time: ~6-8 hours
Result: BEST POSSIBLE training data for 85-95% accuracy
"""

import json
import requests
import time
import random
from typing import Dict, List, Any, Tuple
from collections import Counter
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os


class MaximumDiversityGenerator:
    """Generate 2,600 maximally diverse documents."""
    
    # Tone variations
    TONES = [
        "formal and professional",
        "casual and conversational", 
        "technical and detailed",
        "concise and direct",
        "verbose and explanatory",
        "enthusiastic and engaging",
        "neutral and objective",
        "humorous and lighthearted",
        "serious and authoritative",
    ]
    
    # Multi-lingual content
    LANGUAGES = [
        ("Spanish", "español"),
        ("French", "français"),
        ("German", "Deutsch"),
        ("Chinese", "中文"),
        ("Japanese", "日本語"),
        ("Italian", "italiano"),
    ]
    
    # Formatting styles
    FORMAT_STYLES = [
        "use bullet points and numbered lists",
        "use tables to organize information",
        "include section headers and subheaders",
        "write in continuous paragraphs without lists",
        "use a Q&A format",
        "include examples in code blocks or quotes",
        "add footnotes and references",
        "use a mix of paragraphs and lists",
    ]
    
    # Realistic noise patterns
    NOISE_PATTERNS = [
        "minor_typos",
        "truncated",
        "incomplete",
        "formatting_messy",
    ]
    
    # All 130 categories
    CATEGORIES = [
        "Academic > Lecture Notes", "Academic > Assignments & Homework", "Academic > Lab Reports",
        "Academic > Study Materials", "Academic > Textbooks & Readings", "Academic > Exam Papers",
        "Academic > Course Syllabi", "Academic > Class Schedules", "Academic > Transcripts",
        "Academic > Certificates & Diplomas",
        
        "Work > Resumes & CVs", "Work > Cover Letters", "Work > Business Reports",
        "Work > Meeting Notes", "Work > Presentations", "Work > Contracts & Agreements",
        "Work > Invoices & Receipts", "Work > Project Documentation", "Work > Email Correspondence",
        "Work > Performance Reviews", "Work > Job Descriptions", "Work > Policies & Procedures",
        "Work > Training Materials", "Work > Proposals", "Work > Memos & Announcements",
        
        "Research > Academic Papers", "Research > Thesis & Dissertations", "Research > Literature Reviews",
        "Research > Case Studies", "Research > Grant Proposals", "Research > Survey Data",
        "Research > Conference Papers", "Research > Research Notes",
        
        "Technical > Code & Scripts", "Technical > Documentation", "Technical > Tutorials & Guides",
        "Technical > API References", "Technical > Bug Reports", "Technical > Architecture Diagrams",
        "Technical > Release Notes", "Technical > Technical Specifications",
        
        "Financial > Bank Statements", "Financial > Tax Documents", "Financial > Investment Records",
        "Financial > Budgets & Forecasts", "Financial > Pay Stubs", "Financial > Expense Reports",
        "Legal > Contracts", "Legal > Legal Documents", "Legal > Licenses & Permits",
        "Legal > Court Documents",
        
        "Personal > Journal & Diary", "Personal > Notes & Ideas", "Personal > To-Do Lists",
        "Personal > Letters & Correspondence", "Personal > Medical Records", "Personal > Recipes",
        "Personal > Travel Plans", "Personal > Shopping Lists", "Personal > Calendars & Schedules",
        "Personal > Address Books", "Personal > Personal Statements", "Personal > Family Documents",
        "Personal > Pet Records", "Personal > Fitness & Workout Plans", "Personal > Habit Trackers",
        
        "Creative > Writing & Stories", "Creative > Scripts & Screenplays", "Creative > Articles & Blogs",
        "Creative > Poetry", "Creative > Art & Design Notes", "Creative > Song Lyrics",
        "Creative > Photography Notes", "Creative > Video Scripts", "Creative > Comic Scripts",
        "Creative > Portfolio",
        
        "Books > Fiction", "Books > Non-Fiction", "Books > Textbooks", "Books > Manuals & Guides",
        "Books > Ebooks", "Books > Book Notes & Summaries",
        
        "Education > Online Courses", "Education > Certifications", "Education > Workshop Materials",
        "Education > Study Guides", "Education > Flashcards", "Education > Educational Videos Scripts",
        "Education > Lesson Plans", "Education > Teaching Resources",
        
        "Health > Medical Records", "Health > Prescriptions", "Health > Lab Results",
        "Health > Insurance Documents", "Health > Workout Plans", "Health > Mental Health Journals",
        
        "Property > Lease Agreements", "Property > Property Deeds", "Property > Mortgage Documents",
        "Property > Home Inspection Reports", "Property > HOA Documents",
        
        "Government > ID Documents", "Government > Immigration Papers", "Government > Voting Information",
        "Government > Birth/Death Certificates", "Government > Social Security", "Government > Driver's License",
        
        "Entertainment > Movie Scripts", "Entertainment > Game Design Documents", "Entertainment > Music Sheets",
        "Entertainment > Event Plans", "Entertainment > Streaming Notes",
        
        "Business > Business Plans", "Business > Marketing Materials", "Business > Sales Reports",
        "Business > Customer Data", "Business > Product Documentation", "Business > Competitor Analysis",
        "Business > Pitch Decks",
        
        "Religious > Scripture Notes", "Religious > Prayer Journals", "Religious > Sermon Notes",
        
        "Hobbies > DIY Projects", "Hobbies > Gardening Notes", "Hobbies > Crafts & Patterns",
        "Hobbies > Collection Catalogs", "Hobbies > Gaming Guides",
        
        "News > News Clippings", "News > Press Releases", "News > Newsletter",
        
        "Other > Forms & Applications", "Other > Certificates", "Other > Warranties & Manuals",
        "Other > Miscellaneous", "Other > Uncategorized",
    ]
    
    # TOPIC POOLS for randomization (expand each category with multiple topics)
    TOPIC_POOLS = {
        "Academic > Lecture Notes": ["Machine Learning", "Organic Chemistry", "World History", "Microeconomics", "Quantum Physics", "Literary Analysis", "Psychology", "Sociology", "Biology", "Calculus"],
        "Academic > Assignments & Homework": ["Calculus", "Biology", "Computer Science", "Economics", "Physics", "Chemistry", "English Literature", "History", "Statistics", "Philosophy"],
        "Work > Resumes & CVs": ["Software Engineer", "Marketing Manager", "Data Analyst", "Graphic Designer", "Financial Analyst", "HR Manager", "Product Manager", "Sales Director", "UX Designer", "Project Manager"],
        "Work > Cover Letters": ["tech startup", "consulting firm", "nonprofit organization", "Fortune 500 company", "healthcare provider", "education institution", "government agency", "creative agency"],
        "Creative > Writing & Stories": ["mystery", "romance", "sci-fi", "fantasy", "thriller", "horror", "literary fiction", "historical fiction", "adventure", "dystopian"],
        "Technical > Code & Scripts": ["Python web scraper", "JavaScript API client", "Java data processor", "Go automation script", "Rust CLI tool", "TypeScript React component", "Ruby on Rails controller"],
        # Add more as needed
    }
    
    def __init__(self, model_name="dolphin-mixtral:8x7b", max_workers=None):
        """Initialize generator with concurrent processing support."""
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        self.generated_hashes = set()
        self.retry_count = 5  # Increased for long generations
        self.hash_lock = Lock()  # Thread-safe hash checking
        
        # Auto-detect CPU cores (use half to avoid overload)
        if max_workers is None:
            import multiprocessing
            self.max_workers = max(2, multiprocessing.cpu_count() // 2)
        else:
            self.max_workers = max_workers
        
        if not self._check_ollama():
            raise ConnectionError("Ollama not running")
        
        print(f"Initialized with model: {model_name}")
        print(f"Concurrent workers: {self.max_workers}")
        print(f"Retry attempts: {self.retry_count}")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _call_ollama(self, prompt: str, max_tokens: int) -> str:
        """Call Ollama with improved retry logic and timeout."""
        for attempt in range(self.retry_count):
            try:
                # Adjust temperature based on attempt for variety
                temperature = 0.8 + (attempt * 0.05)
                
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "num_ctx": 8192,  # Larger context window
                        "top_p": 0.9,
                        "top_k": 40,
                    }
                }
                
                # Increased timeout for Mixtral - scales with expected tokens
                timeout = min(240, max(120, max_tokens // 10))
                
                response = requests.post(
                    self.ollama_url, 
                    json=payload, 
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("response", "").strip()
                    
                    # Validate minimum length (at least 500 words for quality)
                    if content and len(content.split()) >= 500:
                        return content
                    elif attempt < self.retry_count - 1:
                        print(f"      Attempt {attempt + 1}: Content too short, retrying...")
                        time.sleep(2)
                        continue
                
            except requests.exceptions.Timeout:
                if attempt < self.retry_count - 1:
                    print(f"      Attempt {attempt + 1}: Timeout, retrying with longer wait...")
                    time.sleep(5)
                else:
                    print(f"      Failed: Timeout after {self.retry_count} attempts")
            
            except Exception as e:
                if attempt == self.retry_count - 1:
                    print(f"      Failed: {e}")
                else:
                    time.sleep(2)
        
        return ""
    
    def _get_word_count_range(self, category: str) -> Tuple[int, int]:
        """Get appropriate word count range for category - MINIMUM 1500 words."""
        category_lower = category.lower()
        
        # Short documents (1500-2000 words) - lists, schedules, simple items
        if any(kw in category_lower for kw in ['to-do', 'shopping', 'schedule', 'address book', 'flashcard', 'invoice', 'receipt']):
            return (1500, 2000)
        
        # Medium documents (1800-2500 words) - notes, emails, journals
        elif any(kw in category_lower for kw in ['notes', 'journal', 'diary', 'recipe', 'email', 'memo']):
            return (1800, 2500)
        
        # Medium-long documents (2000-3000 words) - meetings, presentations, articles
        elif any(kw in category_lower for kw in ['meeting', 'presentation', 'documentation', 'tutorial', 'blog', 'article']):
            return (2000, 3000)
        
        # Long documents (2500-3500 words) - reports, proposals, reviews
        elif any(kw in category_lower for kw in ['resume', 'cover letter', 'report', 'proposal', 'review', 'policy']):
            return (2500, 3500)
        
        # Very long documents (3000-5000 words) - academic, research, business plans
        elif any(kw in category_lower for kw in ['paper', 'thesis', 'business plan', 'case study', 'grant', 'textbook', 'dissertation']):
            return (3000, 5000)
        
        # Default: medium-long (2000-3000 words)
        return (2000, 3000)
    
    def _get_randomized_prompt(self, category: str, var_num: int) -> str:
        """
        Get RANDOMIZED prompt for maximum diversity.
        Each variation gets different topics, angles, contexts.
        """
        # Base prompt template based on category
        base_prompt = self._get_base_prompt_template(category)
        
        # RANDOMIZE: Add different topic/context each time
        if category in self.TOPIC_POOLS:
            topic = random.choice(self.TOPIC_POOLS[category])
            base_prompt = base_prompt.replace("{topic}", topic)
        
        # Add tone variation (80%)
        if random.random() < 0.8:
            tone = random.choice(self.TONES)
            base_prompt += f" Use a {tone} tone."
        
        # Add format style (70%)
        if random.random() < 0.7:
            format_style = random.choice(self.FORMAT_STYLES)
            base_prompt += f" Format: {format_style}."
        
        # Add multi-lingual content (5%)
        if random.random() < 0.05:
            lang_name, lang_native = random.choice(self.LANGUAGES)
            base_prompt += f" Include a paragraph in {lang_name} ({lang_native})."
        
        # Add realistic elements (40%)
        if random.random() < 0.4:
            elements = [
                "Include references to images or figures.",
                "Add a table with data.",
                "Include footnotes or citations.",
                "Reference appendices.",
                "Add timestamps or version numbers.",
            ]
            base_prompt += f" {random.choice(elements)}"
        
        # Add variation-specific details for more uniqueness
        variation_modifiers = [
            f"Focus on practical examples.",
            f"Include real-world scenarios.",
            f"Add specific details and numbers.",
            f"Make it comprehensive and detailed.",
            f"Keep it concise but informative.",
            f"Add personal touches and authenticity.",
        ]
        
        if var_num % 3 == 0:  # Every 3rd variation
            base_prompt += f" {random.choice(variation_modifiers)}"
        
        return base_prompt
    
    def _get_base_prompt_template(self, category: str) -> str:
        """Get base prompt template with {topic} placeholders."""
        
        # Just showing a few examples - you'd expand all 130 categories
        if category == "Academic > Lecture Notes":
            return "Write detailed lecture notes on {topic}. Include: date, main concepts, key formulas/facts, examples, and homework assignment."
        
        elif category == "Academic > Assignments & Homework":
            return "Create a {topic} homework assignment with 5-7 problems. Include: assignment number, due date, problems with clear instructions, and point values."
        
        elif category == "Work > Resumes & CVs":
            return "Write a professional resume for a {topic}. Include: contact info, professional summary, work experience (3-4 positions), skills, education."
        
        elif category == "Creative > Writing & Stories":
            return "Write a {topic} short story opening. Include: compelling first paragraph, character introduction, setting description, conflict/hook."
        
        # For categories not in TOPIC_POOLS, use generic but detailed prompts
        else:
            doc_type = category.split(" > ")[-1]
            return f"Write a realistic {doc_type} document. Include all relevant details, proper format, and authentic content for this document type."
    
    def _inject_realistic_noise(self, content: str) -> str:
        """Add realistic noise patterns (15% of docs)."""
        if random.random() > 0.15:
            return content
        
        noise_type = random.choice(self.NOISE_PATTERNS)
        
        if noise_type == "minor_typos":
            words = content.split()
            if len(words) > 50:
                for _ in range(random.randint(1, 3)):
                    idx = random.randint(0, len(words) - 1)
                    word = words[idx]
                    if len(word) > 3:
                        pos = random.randint(0, len(word) - 2)
                        word_list = list(word)
                        word_list[pos], word_list[pos + 1] = word_list[pos + 1], word_list[pos]
                        words[idx] = ''.join(word_list)
                content = ' '.join(words)
        
        elif noise_type == "truncated":
            cutoff = int(len(content) * random.uniform(0.8, 0.9))
            content = content[:cutoff] + "..."
        
        elif noise_type == "incomplete":
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 2:
                content = '\n\n'.join(paragraphs[:-1])
                content += "\n\n[Document incomplete]"
        
        elif noise_type == "formatting_messy":
            content = content.replace('\n\n', '\n\n\n')
            content = content.replace('. ', '.  ')
        
        return content
    
    def _is_duplicate(self, content: str) -> bool:
        """Check for duplicates (thread-safe)."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        with self.hash_lock:
            if content_hash in self.generated_hashes:
                return True
            self.generated_hashes.add(content_hash)
        
        return False
    
    def _create_filename(self, category: str, var_num: int) -> str:
        """Create realistic filename."""
        main_type = category.split(" > ")[-1].lower().replace(" & ", "_").replace(" ", "_")
        
        suffixes = ["_v1", "_v2", "_draft", "_final", f"_{var_num}", ""]
        extensions = {
            "code": ".py", "scripts": ".py", "documentation": ".md",
            "notes": ".txt", "journal": ".txt", "recipe": ".txt",
            "todo": ".txt", "list": ".txt", "diary": ".txt",
        }
        
        ext = ".pdf"
        for key, value in extensions.items():
            if key in main_type:
                ext = value
                break
        
        return f"{main_type}{random.choice(suffixes)}{ext}"
    
    def generate_document(self, category: str, variation_num: int) -> Dict[str, Any]:
        """Generate a single document with maximum diversity."""
        
        # Get randomized prompt
        prompt = self._get_randomized_prompt(category, variation_num)
        
        # Get word count
        min_words, max_words = self._get_word_count_range(category)
        target_tokens = int((min_words + max_words) / 2 * 1.3)
        
        # Try to generate
        for attempt in range(self.retry_count):
            content = self._call_ollama(prompt, target_tokens)
            
            if not content:
                continue
            
            if self._is_duplicate(content):
                if attempt < self.retry_count - 1:
                    continue
            
            # Success - apply noise
            content = self._inject_realistic_noise(content.strip())
            
            filename = self._create_filename(category, variation_num)
            return {
                "filename": filename,
                "content": content,
                "category": category
            }
        
        # Failed
        filename = self._create_filename(category, variation_num)
        return {
            "filename": filename,
            "content": f"[Placeholder for {category}]",
            "category": category
        }
    
    def _generate_batch(
        self, 
        category: str, 
        start_var: int, 
        end_var: int
    ) -> List[Dict[str, Any]]:
        """Generate multiple documents concurrently for a category."""
        docs = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.generate_document, category, var_num): var_num
                for var_num in range(start_var, end_var + 1)
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                var_num = futures[future]
                try:
                    doc = future.result()
                    docs.append(doc)
                    
                    word_count = len(doc['content'].split())
                    if "[Placeholder" in doc['content']:
                        print(f"  {var_num}: FAILED")
                    else:
                        print(f"  {var_num}: {word_count} words")
                
                except Exception as e:
                    print(f"  {var_num}: Error - {e}")
        
        # Sort by variation number for consistent ordering
        docs.sort(key=lambda x: x['filename'])
        return docs
    
    def generate_all_documents(
        self,
        docs_per_category: int = 30,
        output_file: str = "maximum_documents_3900.json",
        batch_size: int = 5
    ) -> List[Dict]:
        """Generate ALL documents with concurrent processing."""
        
        # Resume from partial progress if file exists
        all_docs = []
        completed_categories = set()
        
        if os.path.exists(output_file):
            with open(output_file) as f:
                all_docs = json.load(f)
                print(f"Resuming from {len(all_docs)} saved documents")
                category_counts = Counter([doc['category'] for doc in all_docs])
                completed_categories = {cat for cat, count in category_counts.items() if count >= docs_per_category}
                print(f"Already completed: {len(completed_categories)} categories")
        
        # Shuffle category order for variety
        categories = self.CATEGORIES.copy()
        random.shuffle(categories)
        
        total = len(self.CATEGORIES) * docs_per_category
        failed_count = sum(1 for d in all_docs if "[Placeholder" in d['content'])
        
        print(f"Generating {total - len(all_docs)} remaining documents")
        print(f"Using concurrent processing with {self.max_workers} workers")
        print(f"Batch size: {batch_size} documents per category at a time\n")
        
        start_time = time.time()
        save_counter = 0
        
        for i, category in enumerate(categories, 1):
            # Skip completed categories
            if category in completed_categories:
                continue
            
            print(f"[{i}/{len(categories)}] {category}")
            
            # Find existing docs for this category
            existing_count = sum(1 for d in all_docs if d['category'] == category)
            remaining = docs_per_category - existing_count
            
            if remaining <= 0:
                continue
            
            start_var = existing_count + 1
            
            # Process in batches to manage memory and provide progress
            for batch_start in range(start_var, docs_per_category + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, docs_per_category)
                
                # Generate batch concurrently
                batch_docs = self._generate_batch(category, batch_start, batch_end)
                all_docs.extend(batch_docs)
                
                # Update failed count
                failed_count += sum(1 for d in batch_docs if "[Placeholder" in d['content'])
                
                # Save progress periodically
                save_counter += len(batch_docs)
                if save_counter >= 50:
                    with open(output_file, 'w') as f:
                        json.dump(all_docs, f, indent=2)
                    elapsed = time.time() - start_time
                    docs_generated = len(all_docs) - len([d for d in all_docs if "[Placeholder" in d['content']])
                    rate = docs_generated / elapsed if elapsed > 0 else 0
                    remaining_docs = total - len(all_docs)
                    eta = remaining_docs / rate if rate > 0 else 0
                    print(f"  Progress: {len(all_docs)}/{total} | Rate: {rate*60:.1f} docs/min | ETA: {eta/60:.1f} min\n")
                    save_counter = 0
        
        # Final save
        with open(output_file, 'w') as f:
            json.dump(all_docs, f, indent=2)
        
        elapsed = time.time() - start_time
        
        print(f"\nGeneration complete")
        print(f"Total documents: {len(all_docs)}")
        print(f"Success rate: {(len(all_docs) - failed_count) / len(all_docs) * 100:.1f}%")
        print(f"Time taken: {elapsed / 60:.1f} minutes ({elapsed / 3600:.1f} hours)")
        print(f"Average rate: {len(all_docs) / elapsed * 60:.1f} documents/minute")
        print(f"Saved to: {output_file}")
        
        return all_docs


def main():
    """Main pipeline."""
    print("MAXIMUM DIVERSITY DOCUMENT GENERATOR")
    print("Model: dolphin-mixtral:8x7b")
    print("Documents: 3,900 (30 per category)")
    print("Word range: 1,500-5,000 per document")
    print("Estimated time: 30-45 hours\n")
    
    try:
        generator = MaximumDiversityGenerator(model_name="dolphin-mixtral:8x7b")
        
        documents = generator.generate_all_documents(
            docs_per_category=30,
            output_file="maximum_documents_3900.json"
        )
        
        print("\nGeneration complete.")
        print("Output: maximum_documents_3900.json")
        print("Next: Generate embeddings and train classifier")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Ensure Ollama is running and dolphin-mixtral:8x7b is installed")


if __name__ == "__main__":
    main()