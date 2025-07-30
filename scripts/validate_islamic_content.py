#!/usr/bin/env python3
"""
Islamic Content Validation Script for QuranBot

This script validates Islamic content in the codebase to ensure accuracy
and adherence to Islamic principles. It checks:
- Quranic verse references and translations
- Hadith authenticity and references
- Islamic terminology usage
- Cultural sensitivity

May Allah (SWT) guide us to accuracy in representing His teachings.
"""

import json
from pathlib import Path
import re
import sys

# Islamic content validation patterns
QURAN_VERSE_PATTERN = re.compile(r"Quran\s+(\d{1,3}):(\d{1,3})")
HADITH_PATTERN = re.compile(
    r"Hadith|Bukhari|Muslim|Tirmidhi|Abu Dawud|Nasa'i|Ibn Majah"
)
ISLAMIC_TERMS = {
    "Allah": ["God", "ALLAH", "allah"],
    "Prophet Muhammad": ["Prophet", "Muhammad", "PBUH", "SAW"],
    "Quran": ["Qur'an", "Holy Quran", "Al-Quran"],
    "Surah": ["Chapter", "Sura"],
    "Ayah": ["Verse", "Aya"],
    "Sunnah": ["Tradition", "Way of Prophet"],
    "Hadith": ["Saying", "Tradition"],
    "Salah": ["Prayer", "Namaz"],
    "Zakat": ["Charity", "Alms"],
    "Hajj": ["Pilgrimage"],
    "Sawm": ["Fasting", "Ramadan fasting"],
}

# Sensitive terms that require careful handling
SENSITIVE_TERMS = [
    "jihad",
    "kafir",
    "infidel",
    "crusade",
    "terrorism",
    "extremist",
    "radical",
    "fundamentalist",
]

# Valid Islamic content sources
VALID_SOURCES = {
    "quran.com",
    "sunnah.com",
    "islamqa.info",
    "islamhouse.com",
    "kalamullah.com",
    "islamweb.net",
    "dar-us-salam.com",
}


class IslamicContentValidator:
    """Validates Islamic content for accuracy and sensitivity."""

    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.validated_files: set[Path] = set()

    def validate_file(self, file_path: Path) -> bool:
        """Validate a single file for Islamic content accuracy."""
        try:
            if file_path.suffix == ".json":
                return self._validate_json_file(file_path)
            elif file_path.suffix == ".py":
                return self._validate_python_file(file_path)
            else:
                return True  # Skip non-relevant files

        except Exception as e:
            self._add_error(file_path, f"Validation error: {e}")
            return False

    def _validate_json_file(self, file_path: Path) -> bool:
        """Validate JSON files containing Islamic content."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            return self._validate_json_content(file_path, data)

        except json.JSONDecodeError as e:
            self._add_error(file_path, f"Invalid JSON: {e}")
            return False

    def _validate_python_file(self, file_path: Path) -> bool:
        """Validate Python files for Islamic content usage."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            return self._validate_text_content(file_path, content)

        except UnicodeDecodeError as e:
            self._add_error(file_path, f"Encoding error: {e}")
            return False

    def _validate_json_content(self, file_path: Path, data) -> bool:
        """Validate the content of JSON data structures."""
        valid = True

        if isinstance(data, dict):
            # Check for Quranic content
            if "questions" in data:
                valid &= self._validate_quiz_questions(file_path, data["questions"])
            elif "verses" in data:
                valid &= self._validate_verses(file_path, data["verses"])
            elif "hadith" in data:
                valid &= self._validate_hadith_content(file_path, data["hadith"])

            # Recursively check nested content
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    valid &= self._validate_json_content(file_path, value)
                elif isinstance(value, str):
                    valid &= self._validate_text_content(file_path, value, key)

        elif isinstance(data, list):
            for item in data:
                valid &= self._validate_json_content(file_path, item)

        return valid

    def _validate_quiz_questions(self, file_path: Path, questions) -> bool:
        """Validate Islamic quiz questions for accuracy."""
        valid = True

        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                continue

            # Check question content
            if "question" in question:
                valid &= self._validate_text_content(
                    file_path, question["question"], f"question[{i}].question"
                )

            # Check answer accuracy
            if "correct_answer" in question and "choices" in question:
                valid &= self._validate_quiz_answer(file_path, question, i)

            # Check for Islamic references
            if "explanation" in question:
                valid &= self._validate_explanation(
                    file_path, question["explanation"], i
                )

        return valid

    def _validate_verses(self, file_path: Path, verses) -> bool:
        """Validate Quranic verses for accuracy."""
        valid = True

        for verse in verses:
            if isinstance(verse, dict):
                # Validate verse reference
                if "surah" in verse and "ayah" in verse:
                    valid &= self._validate_verse_reference(
                        file_path, verse["surah"], verse["ayah"]
                    )

                # Validate Arabic text (if present)
                if "arabic" in verse:
                    valid &= self._validate_arabic_text(file_path, verse["arabic"])

                # Validate translation
                if "translation" in verse:
                    valid &= self._validate_translation(file_path, verse["translation"])

        return valid

    def _validate_text_content(
        self, file_path: Path, text: str, context: str = ""
    ) -> bool:
        """Validate text content for Islamic accuracy and sensitivity."""
        valid = True

        # Check for Quranic references
        quran_matches = QURAN_VERSE_PATTERN.findall(text)
        for surah, ayah in quran_matches:
            valid &= self._validate_verse_reference(
                file_path, int(surah), int(ayah), context
            )

        # Check for sensitive terms
        text_lower = text.lower()
        for term in SENSITIVE_TERMS:
            if term in text_lower:
                self._add_warning(
                    file_path,
                    f"Sensitive term '{term}' found in {context}. Please review context.",
                    {"term": term, "context": context},
                )

        # Check Islamic terminology usage
        for correct_term, variations in ISLAMIC_TERMS.items():
            for variation in variations:
                if (
                    variation.lower() in text_lower
                    and correct_term.lower() not in text_lower
                ):
                    self._add_warning(
                        file_path,
                        f"Consider using '{correct_term}' instead of '{variation}' in {context}",
                        {
                            "suggested": correct_term,
                            "found": variation,
                            "context": context,
                        },
                    )

        return valid

    def _validate_verse_reference(
        self, file_path: Path, surah: int, ayah: int, context: str = ""
    ) -> bool:
        """Validate Quranic verse reference for existence."""
        # Surah count validation (114 surahs in Quran)
        if not (1 <= surah <= 114):
            self._add_error(
                file_path,
                f"Invalid Surah number {surah} in {context}. Must be 1-114.",
                {"surah": surah, "ayah": ayah},
            )
            return False

        # Basic ayah validation (simplified - would need full Quran data for complete validation)
        if ayah < 1:
            self._add_error(
                file_path,
                f"Invalid Ayah number {ayah} in {context}. Must be >= 1.",
                {"surah": surah, "ayah": ayah},
            )
            return False

        # For now, assume valid if basic checks pass
        # In production, would validate against complete Quran database
        return True

    def _validate_quiz_answer(
        self, file_path: Path, question: dict, index: int
    ) -> bool:
        """Validate quiz answer correctness."""
        # This would require extensive Islamic knowledge database
        # For now, just structural validation
        correct_idx = question.get("correct_answer", -1)
        choices = question.get("choices", [])

        if not (0 <= correct_idx < len(choices)):
            self._add_error(
                file_path,
                f"Invalid correct_answer index {correct_idx} for question {index}",
                {"question_index": index, "correct_answer": correct_idx},
            )
            return False

        return True

    def _validate_explanation(
        self, file_path: Path, explanation: str, index: int
    ) -> bool:
        """Validate quiz explanation for Islamic accuracy."""
        # Check for proper Islamic references
        if not any(source in explanation for source in ["Quran", "Hadith", "Sunnah"]):
            self._add_warning(
                file_path,
                f"Question {index} explanation lacks Islamic source reference",
                {"question_index": index},
            )

        return self._validate_text_content(
            file_path, explanation, f"explanation[{index}]"
        )

    def _validate_arabic_text(self, file_path: Path, arabic_text: str) -> bool:
        """Validate Arabic text for proper encoding and characters."""
        # Check for Arabic Unicode range
        arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")

        if not arabic_pattern.search(arabic_text):
            self._add_warning(
                file_path,
                "Text marked as Arabic doesn't contain Arabic characters",
                {
                    "text": (
                        arabic_text[:50] + "..."
                        if len(arabic_text) > 50
                        else arabic_text
                    )
                },
            )

        return True

    def _validate_translation(self, file_path: Path, translation: str) -> bool:
        """Validate English translation quality."""
        return self._validate_text_content(file_path, translation, "translation")

    def _validate_hadith_content(self, file_path: Path, hadith_data) -> bool:
        """Validate Hadith content for authenticity markers."""
        valid = True

        if isinstance(hadith_data, dict):
            # Check for proper attribution
            required_fields = ["text", "narrator", "source"]
            missing_fields = [
                field for field in required_fields if field not in hadith_data
            ]

            if missing_fields:
                self._add_error(
                    file_path,
                    f"Hadith missing required fields: {missing_fields}",
                    {"missing_fields": missing_fields},
                )
                valid = False

            # Validate source authenticity
            if "source" in hadith_data:
                source = hadith_data["source"].lower()
                if not any(
                    valid_source in source
                    for valid_source in [
                        "bukhari",
                        "muslim",
                        "tirmidhi",
                        "abu dawud",
                        "nasai",
                        "ibn majah",
                    ]
                ):
                    self._add_warning(
                        file_path,
                        f"Hadith source '{hadith_data['source']}' may need verification",
                        {"source": hadith_data["source"]},
                    )

        return valid

    def _add_error(self, file_path: Path, message: str, details: dict | None = None):
        """Add a validation error."""
        self.errors.append(
            {
                "file": str(file_path),
                "message": message,
                "details": details or {},
                "type": "error",
            }
        )

    def _add_warning(self, file_path: Path, message: str, details: dict | None = None):
        """Add a validation warning."""
        self.warnings.append(
            {
                "file": str(file_path),
                "message": message,
                "details": details or {},
                "type": "warning",
            }
        )

    def get_report(self) -> dict:
        """Get validation report."""
        return {
            "files_validated": len(self.validated_files),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "error_details": self.errors,
            "warning_details": self.warnings,
            "status": "PASS" if len(self.errors) == 0 else "FAIL",
        }


def main():
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: python validate_islamic_content.py <file1> [file2] ...")
        sys.exit(1)

    validator = IslamicContentValidator()
    all_valid = True

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)
        if file_path.exists():
            valid = validator.validate_file(file_path)
            validator.validated_files.add(file_path)
            all_valid &= valid
        else:
            validator._add_error(file_path, "File not found")
            all_valid = False

    # Generate report
    report = validator.get_report()

    # Print summary
    print("\n🕌 Islamic Content Validation Report")
    print(f"{'='*50}")
    print(f"Files validated: {report['files_validated']}")
    print(f"Errors: {report['errors']}")
    print(f"Warnings: {report['warnings']}")
    print(f"Status: {report['status']}")

    # Print details if there are issues
    if report["errors"] > 0:
        print("\n❌ Errors:")
        for error in report["error_details"]:
            print(f"  {error['file']}: {error['message']}")

    if report["warnings"] > 0:
        print("\n⚠️  Warnings:")
        for warning in report["warning_details"]:
            print(f"  {warning['file']}: {warning['message']}")

    if all_valid:
        print("\n✅ All Islamic content validates successfully!")
        print("الحمد لله (Alhamdulillahi Rabbil Alameen)")
    else:
        print("\n❌ Islamic content validation failed!")
        print("Please review and correct the issues above.")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
