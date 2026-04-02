"""Parse contract documents (.pdf, .docx, .txt) into structured sections."""

import re
from pathlib import Path

from contract_reviewer.models.contract import Contract, Section


class ContractParser:
    """Extract structured sections from contract documents."""

    # Common Chinese contract section patterns
    SECTION_PATTERNS = [
        re.compile(r"^第[一二三四五六七八九十百]+[条章节编]"),  # 第一条, 第二章
        re.compile(r"^[一二三四五六七八九十]+[、.]"),  # 一、 二.
        re.compile(r"^[（(]\s*[一二三四五六七八九十]+\s*[）)]"),  # （一） (二)
        re.compile(r"^\d+[\.、]\s"),  # 1. 2、
        re.compile(r"^Article\s+\d+", re.IGNORECASE),  # Article 1
        re.compile(r"^Section\s+\d+", re.IGNORECASE),  # Section 1
    ]

    def parse(self, file_path: str) -> Contract:
        """Parse a contract file into a Contract object."""
        path = Path(file_path)
        text = self._extract_text(path)
        sections = self._split_sections(text)

        return Contract(
            name=path.stem,
            source_path=str(path.absolute()),
            full_text=text,
            sections=sections,
        )

    def _extract_text(self, path: Path) -> str:
        """Extract raw text from file based on extension."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path)
        elif suffix == ".docx":
            return self._parse_docx(path)
        elif suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _parse_pdf(self, path: Path) -> str:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Also extract tables as text
                for table in page.extract_tables():
                    rows = []
                    for row in table:
                        cells = [str(c or "") for c in row]
                        rows.append(" | ".join(cells))
                    text += "\n" + "\n".join(rows)
                pages.append(text)
            return "\n\n".join(pages)

    def _parse_docx(self, path: Path) -> str:
        import docx

        doc = docx.Document(str(path))
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                paragraphs.append(" | ".join(cells))
        return "\n\n".join(paragraphs)

    def _split_sections(self, text: str) -> list[Section]:
        """Split text into sections by detecting clause/article boundaries."""
        lines = text.split("\n")
        sections: list[Section] = []
        current_heading = ""
        current_body_lines: list[str] = []
        section_index = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_body_lines.append("")
                continue

            is_heading = any(p.match(stripped) for p in self.SECTION_PATTERNS)

            if is_heading and current_body_lines:
                # Save previous section
                body = "\n".join(current_body_lines).strip()
                if body or current_heading:
                    sections.append(
                        Section(
                            heading=current_heading,
                            body=body,
                            section_type=self._detect_type(current_heading, body),
                            index=section_index,
                        )
                    )
                    section_index += 1
                current_heading = stripped
                current_body_lines = []
            elif is_heading:
                current_heading = stripped
            else:
                current_body_lines.append(stripped)

        # Save last section
        body = "\n".join(current_body_lines).strip()
        if body or current_heading:
            sections.append(
                Section(
                    heading=current_heading,
                    body=body,
                    section_type=self._detect_type(current_heading, body),
                    index=section_index,
                )
            )

        return sections if sections else [Section(body=text, section_type="body")]

    @staticmethod
    def _detect_type(heading: str, body: str) -> str:
        """Heuristic section type detection."""
        combined = (heading + " " + body[:200]).lower()
        if any(kw in combined for kw in ["甲方", "乙方", "party a", "party b", "签署方"]):
            return "parties"
        if any(kw in combined for kw in ["签章", "签字", "盖章", "signature", "signed by"]):
            return "signature"
        if "|" in body and body.count("|") > 3:
            return "table"
        return "body"
