#!/usr/bin/env python3
"""
QuranBot - Fix Quiz Data Corruption
====================================
This script fixes the corrupted quiz data that's causing the KeyError: 'options'
issue and massive Discord rate limiting on the VPS.

The problem:
- Some questions in quiz_data.json are missing the 'options' field
- This causes repeated crashes every few seconds
- Discord rate limits the bot due to constant error messages
- Audio and other features stop working due to performance degradation

The solution:
- Validate all quiz questions
- Remove corrupted entries
- Restore default questions if needed
- Clean up the quiz data files

Usage:
    python fix_quiz_corruption.py
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def backup_quiz_data():
    """Create backup of existing quiz data before fixing"""
    try:
        data_dir = Path("data")
        backup_dir = (
            Path("backup")
            / "quiz_corruption_fix"
            / datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Files to backup
        files_to_backup = [
            "quiz_data.json",
            "quiz_state.json",
            "quiz_stats.json",
            "recent_questions.json",
        ]

        backed_up = []
        for filename in files_to_backup:
            src = data_dir / filename
            if src.exists():
                dst = backup_dir / filename
                shutil.copy2(src, dst)
                backed_up.append(filename)

        print(f"✅ Backup created: {backup_dir}")
        print(f"📁 Files backed up: {', '.join(backed_up)}")
        return True

    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def validate_question(question, index=None):
    """Validate a single question structure"""
    if not isinstance(question, dict):
        return False, f"Question {index} is not a dictionary"

    required_fields = ["question", "options", "difficulty", "category"]
    missing_fields = [field for field in required_fields if field not in question]

    if missing_fields:
        return False, f"Question {index} missing fields: {missing_fields}"

    if not isinstance(question["options"], list) or len(question["options"]) == 0:
        return False, f"Question {index} has invalid options field"

    return True, "Valid"


def fix_quiz_data():
    """Fix corrupted quiz data"""
    try:
        data_dir = Path("data")
        quiz_data_file = data_dir / "quiz_data.json"

        if not quiz_data_file.exists():
            print("📄 No quiz_data.json found - will create default questions")
            return create_default_quiz_data()

        print("🔍 Loading quiz data...")
        with open(quiz_data_file, "r", encoding="utf-8") as f:
            quiz_data = json.load(f)

        if "questions" not in quiz_data:
            print("❌ No questions found in quiz_data.json")
            return create_default_quiz_data()

        questions = quiz_data["questions"]
        print(f"📊 Found {len(questions)} questions")

        # Validate and clean questions
        valid_questions = []
        corrupted_count = 0

        for i, question in enumerate(questions):
            is_valid, error_msg = validate_question(question, i)
            if is_valid:
                valid_questions.append(question)
            else:
                corrupted_count += 1
                print(f"❌ {error_msg}")

        print(f"✅ Valid questions: {len(valid_questions)}")
        print(f"🗑️  Corrupted questions removed: {corrupted_count}")

        # Update quiz data
        quiz_data["questions"] = valid_questions

        # Save cleaned data
        with open(quiz_data_file, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved cleaned quiz data")

        # If we have very few questions, add defaults
        if len(valid_questions) < 5:
            print("⚠️  Too few valid questions, adding defaults...")
            return add_default_questions(quiz_data_file)

        return True

    except Exception as e:
        print(f"❌ Error fixing quiz data: {e}")
        return False


def create_default_quiz_data():
    """Create quiz_data.json with default questions"""
    try:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        default_questions = [
            {
                "question": "How many chapters (surahs) are there in the Quran?",
                "options": ["114", "116", "112", "118"],
                "correct_answer": 0,
                "difficulty": "easy",
                "category": "general",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
            {
                "question": "What is the first chapter of the Quran called?",
                "options": ["Al-Baqarah", "Al-Fatihah", "An-Nas", "Al-Ikhlas"],
                "correct_answer": 1,
                "difficulty": "easy",
                "category": "surah_names",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
            {
                "question": "Which prophet is mentioned most frequently in the Quran?",
                "options": [
                    "Prophet Muhammad (PBUH)",
                    "Prophet Ibrahim (PBUH)",
                    "Prophet Musa (PBUH)",
                    "Prophet Isa (PBUH)",
                ],
                "correct_answer": 2,
                "difficulty": "medium",
                "category": "prophets",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
            {
                "question": "What does 'Bismillah' mean?",
                "options": [
                    "In the name of Allah",
                    "Praise be to Allah",
                    "Allah is great",
                    "There is no god but Allah",
                ],
                "correct_answer": 0,
                "difficulty": "easy",
                "category": "vocabulary",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
            {
                "question": "Which surah is known as the 'Heart of the Quran'?",
                "options": ["Al-Fatihah", "Yaseen", "Al-Baqarah", "Al-Ikhlas"],
                "correct_answer": 1,
                "difficulty": "medium",
                "category": "surah_names",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
        ]

        quiz_data = {
            "questions": default_questions,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "source": "default_questions",
            },
        }

        quiz_data_file = data_dir / "quiz_data.json"
        with open(quiz_data_file, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)

        print(
            f"✅ Created quiz_data.json with {len(default_questions)} default questions"
        )
        return True

    except Exception as e:
        print(f"❌ Error creating default quiz data: {e}")
        return False


def add_default_questions(quiz_data_file):
    """Add default questions to existing quiz data"""
    try:
        with open(quiz_data_file, "r", encoding="utf-8") as f:
            quiz_data = json.load(f)

        # Add more default questions
        additional_questions = [
            {
                "question": "What is the last surah in the Quran?",
                "options": ["An-Nas", "Al-Falaq", "Al-Ikhlas", "Al-Masad"],
                "correct_answer": 0,
                "difficulty": "easy",
                "category": "surah_names",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
            {
                "question": "How many verses are in Surah Al-Fatihah?",
                "options": ["5", "6", "7", "8"],
                "correct_answer": 2,
                "difficulty": "medium",
                "category": "general",
                "created_at": datetime.now().isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            },
        ]

        quiz_data["questions"].extend(additional_questions)

        with open(quiz_data_file, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Added {len(additional_questions)} additional questions")
        return True

    except Exception as e:
        print(f"❌ Error adding default questions: {e}")
        return False


def clean_quiz_state():
    """Clean up quiz state files"""
    try:
        data_dir = Path("data")

        # Reset recent questions to allow all questions to be asked again
        recent_questions_file = data_dir / "recent_questions.json"
        if recent_questions_file.exists():
            with open(recent_questions_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            print("🧹 Cleared recent questions list")

        # Clean quiz state
        quiz_state_file = data_dir / "quiz_state.json"
        if quiz_state_file.exists():
            with open(quiz_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Keep user scores but clear recent questions
            if "recent_questions" in state:
                state["recent_questions"] = []

            with open(quiz_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            print("🧹 Cleaned quiz state")

        return True

    except Exception as e:
        print(f"❌ Error cleaning quiz state: {e}")
        return False


def main():
    """Main function to fix quiz corruption"""
    print("🔧 QuranBot Quiz Corruption Fix")
    print("=" * 40)

    # Step 1: Backup existing data
    print("\n1. Creating backup...")
    if not backup_quiz_data():
        print("❌ Backup failed - stopping for safety")
        return False

    # Step 2: Fix quiz data
    print("\n2. Fixing quiz data...")
    if not fix_quiz_data():
        print("❌ Failed to fix quiz data")
        return False

    # Step 3: Clean state
    print("\n3. Cleaning quiz state...")
    if not clean_quiz_state():
        print("❌ Failed to clean quiz state")
        return False

    print("\n✅ Quiz corruption fix completed!")
    print("\nNext steps:")
    print("1. Restart the bot: systemctl restart quranbot.service")
    print("2. Check logs: journalctl -u quranbot.service -f")
    print("3. The rate limiting should stop within a few minutes")
    print("4. Audio should resume normal operation")

    return True


if __name__ == "__main__":
    main()
