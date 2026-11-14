"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    chunks = []
    step = size - overlap
    text = page.text
    start = 0
    idx = 0

    while start < len(text):
        chunk_text = text[start : start + size].strip()
        if chunk_text:
            chunks.append(Chunk(
                chunk_id=f"{page.document_id}_p{page.page}_c{idx}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=dict(page.metadata)
            ))
            idx += 1
        start += step
    return chunks

def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    chunks = []
    paras = page.text.split("\n\n")
    text = ""
    for para in paras:
        if text and (len(text) + len(para) >= max_size):
            # lay cai hien tai
            chunks.append(Chunk(
                chunk_id=f"{page.document_id}_p{page.page}_{len(chunks)}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text.strip(),
                metadata=dict(page.metadata)
            ))
            text = ""
        
        text += para + "\n\n"
    
    if text.strip():
        chunks.append(Chunk(
            chunk_id=f"{page.document_id}_p{page.page}_{len(chunks)}",
            document_id=page.document_id,
            source=page.source,
            page=page.page,
            text=text.strip(),
            metadata=dict(page.metadata)
        ))

    return chunks
    