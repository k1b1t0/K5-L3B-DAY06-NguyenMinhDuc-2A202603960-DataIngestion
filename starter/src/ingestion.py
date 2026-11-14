"""Read and normalize source data. TODO: implement functions."""
from pathlib import Path
from .models import DocumentPage
import unicodedata
import re
from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def load_html(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    with open(path, "r", encoding="utf-8") as f:
        docs = []
        text = ""
        soup = BeautifulSoup(f, "html.parser")
        chapter_divs = soup.find_all("div", id=lambda x: x and x.startswith("chapter-"))
        for index, chapter_div in enumerate(chapter_divs):
            for p in chapter_div.find_all("p"):
                clean_p = normalize_text(p.get_text())
                if clean_p:
                    text += clean_p + "\n\n"
                    if len(text) >= 1500:
                        docs.append(DocumentPage(
                            document_id=document_id,
                            source=source,
                            page=len(docs) + 1,
                            text=text.strip(),
                            metadata={"chapter": f"Chapter {index + 1}"}
                        ))
                        text = ""
        if text.strip():
            docs.append(DocumentPage(
                document_id=document_id,
                source=source,
                page=len(docs) + 1,
                text=text.strip(),
                metadata={"chapter": f"Chapter {len(chapter_divs)}"}
            ))
        return docs
