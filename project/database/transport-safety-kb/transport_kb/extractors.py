from __future__ import annotations

import io
import re
import tempfile
from html import unescape
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from bs4 import BeautifulSoup


def decode_html(content: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def extract_html(content: bytes) -> tuple[str, str]:
    html = decode_html(content)
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "nav", "footer", "iframe"]):
        node.decompose()
    title = ""
    if soup.title:
        title = " ".join(soup.title.get_text(" ", strip=True).split())
    selectors = (
        "article", ".article", ".article-content", ".content", ".TRS_Editor",
        "#UCAP-CONTENT", "#zoom", ".pages_content", ".main_cent", "main",
    )
    candidates = [soup.select_one(selector) for selector in selectors]
    candidates = [node for node in candidates if node is not None]
    root = max(candidates, key=lambda node: len(node.get_text("\n", strip=True)), default=soup.body or soup)
    text = root.get_text("\n", strip=True)
    text = unescape(text).replace("\u3000", " ").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text.strip()


def extract_pdf(content: bytes) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF extraction requires installed pypdf") from exc
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"[第{index}页]\n{text.strip()}")
    return "", "\n\n".join(pages).strip()


def extract_docx(content: bytes) -> tuple[str, str]:
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise RuntimeError("invalid DOCX source") from exc
    root = ElementTree.fromstring(document_xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if text:
            paragraphs.append(text)
    return "", "\n".join(paragraphs)


def extract_doc(content: bytes) -> tuple[str, str]:
    """Extract a legacy OLE Word document through an isolated Word instance."""
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise RuntimeError("legacy DOC extraction requires installed pywin32") from exc

    temp_path: Path | None = None
    word = None
    document = None
    try:
        with tempfile.NamedTemporaryFile(prefix="transport-kb-", suffix=".doc", delete=False) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        word = DispatchEx("Word.Application")
        word.DisplayAlerts = 0
        word.Visible = False
        document = word.Documents.Open(
            str(temp_path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        text = str(document.Content.Text or "")
        text = text.replace("\r\x07", "\n").replace("\r", "\n").replace("\x07", "")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return "", text
    except Exception as exc:
        raise RuntimeError("legacy DOC extraction failed") from exc
    finally:
        if document is not None:
            try:
                document.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def extract_content(media_type: str, content: bytes) -> tuple[str, str]:
    if "pdf" in media_type.lower() or content.startswith(b"%PDF"):
        return extract_pdf(content)
    if "wordprocessingml" in media_type.lower():
        return extract_docx(content)
    if "msword" in media_type.lower() or content.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
        return extract_doc(content)
    return extract_html(content)
