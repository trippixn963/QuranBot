#!/usr/bin/env python3
# =============================================================================
# QuranBot - Quiz Management Tool
# =============================================================================
# Comprehensive tool for managing quiz questions in SQLite database
# Add, edit, delete, and import quiz questions with ease
# =============================================================================

import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class QuizManager:
    """
    Comprehensive quiz management system for SQLite database.
    
    Features:
    - Add new quiz questions
    - Edit existing questions
    - Import from JSON files
    - Export to JSON files
    - Search and filter questions
    - Validate question format
    """

    def __init__(self, db_path: Path = None):
        """Initialize quiz manager"""
        self.db_path = db_path or Path("data/quranbot.db")
        self._ensure_quiz_tables()
        
    def _ensure_quiz_tables(self):
        """Create quiz questions table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Create quiz questions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    option_a TEXT NOT NULL,
                    option_b TEXT NOT NULL,
                    option_c TEXT NOT NULL,
                    option_d TEXT NOT NULL,
                    correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A', 'B', 'C', 'D')),
                    category TEXT DEFAULT 'general',
                    difficulty TEXT DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
                    surah_reference TEXT,
                    verse_reference TEXT,
                    explanation TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    times_used INTEGER DEFAULT 0,
                    times_correct INTEGER DEFAULT 0
                )
            """)
            
            # Create index for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quiz_category_difficulty 
                ON quiz_questions(category, difficulty, is_active)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quiz_surah 
                ON quiz_questions(surah_reference, is_active)
            """)
            
            conn.commit()
            print("✅ Quiz questions table ready")
            
        finally:
            conn.close()
    
    def add_question(
        self, 
        question: str,
        option_a: str,
        option_b: str, 
        option_c: str,
        option_d: str,
        correct_answer: str,
        category: str = "general",
        difficulty: str = "medium",
        surah_reference: str = None,
        verse_reference: str = None,
        explanation: str = None,
        source: str = "manual"
    ) -> int:
        """
        Add a new quiz question.
        
        Returns:
            Question ID if successful, -1 if failed
        """
        try:
            # Validate inputs
            if correct_answer.upper() not in ['A', 'B', 'C', 'D']:
                raise ValueError("Correct answer must be A, B, C, or D")
                
            if difficulty.lower() not in ['easy', 'medium', 'hard']:
                raise ValueError("Difficulty must be easy, medium, or hard")
            
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    INSERT INTO quiz_questions 
                    (question, option_a, option_b, option_c, option_d, correct_answer,
                     category, difficulty, surah_reference, verse_reference, explanation, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    question, option_a, option_b, option_c, option_d, correct_answer.upper(),
                    category, difficulty.lower(), surah_reference, verse_reference, explanation, source
                ))
                
                question_id = cursor.lastrowid
                conn.commit()
                
                print(f"✅ Added question #{question_id}: {question[:50]}...")
                return question_id
                
            finally:
                conn.close()
                
        except Exception as e:
            print(f"❌ Failed to add question: {e}")
            return -1
    
    def get_questions(
        self, 
        category: str = None,
        difficulty: str = None,
        surah_reference: str = None,
        active_only: bool = True,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Get quiz questions with optional filtering"""
        
        query = "SELECT * FROM quiz_questions WHERE 1=1"
        params = []
        
        if active_only:
            query += " AND is_active = 1"
            
        if category:
            query += " AND category = ?"
            params.append(category)
            
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
            
        if surah_reference:
            query += " AND surah_reference = ?"
            params.append(surah_reference)
            
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute(query, params)
            questions = [dict(row) for row in cursor.fetchall()]
            return questions
        finally:
            conn.close()
    
    def update_question(self, question_id: int, **updates) -> bool:
        """Update an existing question"""
        try:
            valid_fields = {
                'question', 'option_a', 'option_b', 'option_c', 'option_d',
                'correct_answer', 'category', 'difficulty', 'surah_reference',
                'verse_reference', 'explanation', 'is_active'
            }
            
            update_fields = []
            values = []
            
            for field, value in updates.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                print("❌ No valid fields to update")
                return False
            
            # Add updated timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(question_id)
            
            query = f"""
                UPDATE quiz_questions 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(query, values)
                
                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"✅ Updated question #{question_id}")
                    return True
                else:
                    print(f"❌ Question #{question_id} not found")
                    return False
                    
            finally:
                conn.close()
                
        except Exception as e:
            print(f"❌ Failed to update question: {e}")
            return False
    
    def delete_question(self, question_id: int, soft_delete: bool = True) -> bool:
        """Delete a question (soft delete by default)"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                if soft_delete:
                    # Soft delete (mark as inactive)
                    cursor = conn.execute(
                        "UPDATE quiz_questions SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (question_id,)
                    )
                else:
                    # Hard delete (permanent removal)
                    cursor = conn.execute("DELETE FROM quiz_questions WHERE id = ?", (question_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    delete_type = "deactivated" if soft_delete else "deleted"
                    print(f"✅ Question #{question_id} {delete_type}")
                    return True
                else:
                    print(f"❌ Question #{question_id} not found")
                    return False
                    
            finally:
                conn.close()
                
        except Exception as e:
            print(f"❌ Failed to delete question: {e}")
            return False
    
    def import_from_json(self, json_file: Path) -> int:
        """Import questions from JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            
            # Handle different JSON formats
            questions = []
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                if 'questions' in data:
                    questions = data['questions']
                elif 'quiz_data' in data:
                    questions = data['quiz_data']
                else:
                    # Assume the dict values are questions
                    questions = list(data.values())
            
            for q in questions:
                try:
                    # Handle QuranBot's complex question format
                    question_data = q.get('question', {})
                    if isinstance(question_data, dict):
                        # Use English version, fallback to Arabic if needed
                        question_text = question_data.get('english') or question_data.get('arabic')
                    else:
                        question_text = question_data or q.get('text') or q.get('prompt')
                    
                    # Handle QuranBot's choices format
                    choices = q.get('choices', {})
                    if isinstance(choices, dict):
                        # Extract English options, fallback to Arabic
                        option_a = (choices.get('A', {}).get('english') if isinstance(choices.get('A'), dict) 
                                   else choices.get('A')) or choices.get('A', {}).get('arabic', '')
                        option_b = (choices.get('B', {}).get('english') if isinstance(choices.get('B'), dict) 
                                   else choices.get('B')) or choices.get('B', {}).get('arabic', '')
                        option_c = (choices.get('C', {}).get('english') if isinstance(choices.get('C'), dict) 
                                   else choices.get('C')) or choices.get('C', {}).get('arabic', '')
                        option_d = (choices.get('D', {}).get('english') if isinstance(choices.get('D'), dict) 
                                   else choices.get('D')) or choices.get('D', {}).get('arabic', '')
                    else:
                        # Fallback to simple options format
                        options = q.get('options', {})
                        if isinstance(options, dict):
                            option_a = options.get('A') or options.get('a') or options.get('0')
                            option_b = options.get('B') or options.get('b') or options.get('1')
                            option_c = options.get('C') or options.get('c') or options.get('2')
                            option_d = options.get('D') or options.get('d') or options.get('3')
                        elif isinstance(options, list) and len(options) >= 4:
                            option_a, option_b, option_c, option_d = options[:4]
                        else:
                            print(f"⚠️ Skipping question with invalid options: {str(question_text)[:50]}...")
                            continue
                    
                    correct = q.get('correct_answer') or q.get('correct') or q.get('answer')
                    
                    # Handle explanation format
                    explanation_data = q.get('explanation', {})
                    if isinstance(explanation_data, dict):
                        explanation = explanation_data.get('english') or explanation_data.get('arabic')
                    else:
                        explanation = explanation_data
                    
                    # Convert difficulty number to text
                    difficulty_num = q.get('difficulty', 2)
                    if isinstance(difficulty_num, int):
                        difficulty_map = {1: 'easy', 2: 'medium', 3: 'hard'}
                        difficulty = difficulty_map.get(difficulty_num, 'medium')
                    else:
                        difficulty = str(difficulty_num).lower() if difficulty_num else 'medium'
                    
                    if not all([question_text, option_a, option_b, option_c, option_d, correct]):
                        print(f"⚠️ Skipping incomplete question: {str(question_text)[:50]}...")
                        continue
                    
                    question_id = self.add_question(
                        question=question_text,
                        option_a=option_a,
                        option_b=option_b,
                        option_c=option_c,
                        option_d=option_d,
                        correct_answer=correct,
                        category=q.get('category', 'imported'),
                        difficulty=difficulty,
                        surah_reference=q.get('surah'),
                        verse_reference=q.get('verse'),
                        explanation=explanation,
                        source=f"imported_from_{json_file.name}"
                    )
                    
                    if question_id > 0:
                        imported_count += 1
                        
                except Exception as e:
                    print(f"⚠️ Failed to import question: {e}")
                    continue
            
            print(f"📥 Imported {imported_count} questions from {json_file}")
            return imported_count
            
        except Exception as e:
            print(f"❌ Failed to import from {json_file}: {e}")
            return 0
    
    def export_to_json(self, output_file: Path, **filters) -> bool:
        """Export questions to JSON file"""
        try:
            questions = self.get_questions(**filters)
            
            # Convert to export format
            export_data = {
                "metadata": {
                    "total_questions": len(questions),
                    "exported_at": str(Path().resolve()),
                    "source": "QuranBot SQLite Database"
                },
                "questions": []
            }
            
            for q in questions:
                export_data["questions"].append({
                    "id": q["id"],
                    "question": q["question"],
                    "options": {
                        "A": q["option_a"],
                        "B": q["option_b"],
                        "C": q["option_c"],
                        "D": q["option_d"]
                    },
                    "correct_answer": q["correct_answer"],
                    "category": q["category"],
                    "difficulty": q["difficulty"],
                    "surah_reference": q["surah_reference"],
                    "verse_reference": q["verse_reference"],
                    "explanation": q["explanation"],
                    "stats": {
                        "times_used": q["times_used"],
                        "times_correct": q["times_correct"],
                        "success_rate": round(q["times_correct"] / max(q["times_used"], 1) * 100, 1)
                    }
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"📤 Exported {len(questions)} questions to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get quiz database statistics"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Total counts
            total = conn.execute("SELECT COUNT(*) as count FROM quiz_questions").fetchone()["count"]
            active = conn.execute("SELECT COUNT(*) as count FROM quiz_questions WHERE is_active = 1").fetchone()["count"]
            
            # By category
            categories = conn.execute("""
                SELECT category, COUNT(*) as count 
                FROM quiz_questions 
                WHERE is_active = 1 
                GROUP BY category 
                ORDER BY count DESC
            """).fetchall()
            
            # By difficulty
            difficulties = conn.execute("""
                SELECT difficulty, COUNT(*) as count 
                FROM quiz_questions 
                WHERE is_active = 1 
                GROUP BY difficulty 
                ORDER BY 
                    CASE difficulty 
                        WHEN 'easy' THEN 1 
                        WHEN 'medium' THEN 2 
                        WHEN 'hard' THEN 3 
                    END
            """).fetchall()
            
            # Usage stats
            usage = conn.execute("""
                SELECT 
                    AVG(times_used) as avg_used,
                    AVG(CASE WHEN times_used > 0 THEN times_correct * 100.0 / times_used ELSE 0 END) as avg_success_rate,
                    MAX(times_used) as max_used
                FROM quiz_questions 
                WHERE is_active = 1
            """).fetchone()
            
            return {
                "total_questions": total,
                "active_questions": active,
                "inactive_questions": total - active,
                "categories": [dict(row) for row in categories],
                "difficulties": [dict(row) for row in difficulties],
                "usage_stats": dict(usage) if usage else {}
            }
            
        finally:
            conn.close()


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="QuranBot Quiz Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/quiz_manager.py --stats                          # Show statistics
  python tools/quiz_manager.py --list --limit 5                 # List 5 questions
  python tools/quiz_manager.py --add                            # Interactive add
  python tools/quiz_manager.py --import quiz_data.json          # Import from JSON
  python tools/quiz_manager.py --export backup.json            # Export all questions
  python tools/quiz_manager.py --category "Quran" --list       # Filter by category
        """
    )
    
    parser.add_argument("--stats", action="store_true", help="Show quiz statistics")
    parser.add_argument("--list", action="store_true", help="List questions")
    parser.add_argument("--add", action="store_true", help="Add new question interactively")
    parser.add_argument("--import", dest="import_file", help="Import from JSON file")
    parser.add_argument("--export", dest="export_file", help="Export to JSON file")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="Filter by difficulty")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of results")
    
    args = parser.parse_args()
    
    manager = QuizManager()
    
    if args.stats:
        print("📊 Quiz Database Statistics")
        print("=" * 50)
        stats = manager.get_statistics()
        
        print(f"📝 Total Questions: {stats['total_questions']}")
        print(f"✅ Active: {stats['active_questions']}")
        print(f"❌ Inactive: {stats['inactive_questions']}")
        
        if stats['categories']:
            print(f"\n📂 By Category:")
            for cat in stats['categories']:
                print(f"   {cat['category']}: {cat['count']} questions")
        
        if stats['difficulties']:
            print(f"\n🎯 By Difficulty:")
            for diff in stats['difficulties']:
                print(f"   {diff['difficulty'].title()}: {diff['count']} questions")
        
        if stats['usage_stats'] and any(stats['usage_stats'].values()):
            usage = stats['usage_stats']
            print(f"\n📈 Usage Statistics:")
            print(f"   Average uses per question: {usage.get('avg_used') or 0:.1f}")
            print(f"   Average success rate: {usage.get('avg_success_rate') or 0:.1f}%")
            print(f"   Most used question: {usage.get('max_used') or 0} times")
    
    elif args.list:
        questions = manager.get_questions(
            category=args.category,
            difficulty=args.difficulty,
            limit=args.limit
        )
        
        print(f"📋 Quiz Questions ({len(questions)} found)")
        print("=" * 50)
        
        for q in questions:
            print(f"\n#{q['id']} - {q['category'].title()} ({q['difficulty']})")
            print(f"❓ {q['question']}")
            print(f"   A) {q['option_a']}")
            print(f"   B) {q['option_b']}")
            print(f"   C) {q['option_c']}")
            print(f"   D) {q['option_d']}")
            print(f"✅ Correct: {q['correct_answer']}")
            if q['times_used'] > 0:
                success_rate = q['times_correct'] / q['times_used'] * 100
                print(f"📊 Used {q['times_used']} times, {success_rate:.1f}% success rate")
    
    elif args.add:
        print("➕ Add New Quiz Question")
        print("=" * 30)
        
        question = input("❓ Question: ").strip()
        option_a = input("A) ").strip()
        option_b = input("B) ").strip()
        option_c = input("C) ").strip()
        option_d = input("D) ").strip()
        correct = input("✅ Correct answer (A/B/C/D): ").strip().upper()
        category = input("📂 Category (default: general): ").strip() or "general"
        difficulty = input("🎯 Difficulty (easy/medium/hard, default: medium): ").strip().lower() or "medium"
        surah = input("📖 Surah reference (optional): ").strip() or None
        verse = input("📝 Verse reference (optional): ").strip() or None
        explanation = input("💡 Explanation (optional): ").strip() or None
        
        question_id = manager.add_question(
            question=question,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct,
            category=category,
            difficulty=difficulty,
            surah_reference=surah,
            verse_reference=verse,
            explanation=explanation
        )
        
        if question_id > 0:
            print(f"🎉 Question added successfully with ID #{question_id}")
        else:
            print("❌ Failed to add question")
    
    elif args.import_file:
        import_file = Path(args.import_file)
        if import_file.exists():
            count = manager.import_from_json(import_file)
            print(f"✅ Import complete: {count} questions added")
        else:
            print(f"❌ File not found: {import_file}")
    
    elif args.export_file:
        export_file = Path(args.export_file)
        success = manager.export_to_json(
            export_file,
            category=args.category,
            difficulty=args.difficulty
        )
        if success:
            print(f"✅ Export complete: {export_file}")
        else:
            print("❌ Export failed")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 