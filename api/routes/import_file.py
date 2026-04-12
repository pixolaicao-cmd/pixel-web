"""
POST /memories/import — 上传文件 → MarkItDown 转 Markdown → 存进记忆库
支持格式：PDF、Word (.docx)、PowerPoint (.pptx)、Excel (.xlsx)、TXT、HTML
"""

import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database import get_db
from user_auth import get_current_user

router = APIRouter()

# 允许的 MIME 类型 → 文件后缀
ALLOWED: dict[str, str] = {
    "application/pdf":                                                        ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":      ".xlsx",
    "application/msword":                                                     ".doc",
    "text/plain":                                                             ".txt",
    "text/html":                                                              ".html",
    "text/markdown":                                                          ".md",
}

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/memories/import")
async def import_file_to_memory(
    file: UploadFile = File(...),
    category: str = Form(default="document"),
    current_user: dict = Depends(get_current_user),
):
    """
    上传文件，MarkItDown 转成 Markdown，存进用户的记忆库。
    返回 {memory_id, preview（前 300 字符）, total_chars}
    """
    # 类型检查
    mime = (file.content_type or "").split(";")[0].strip()
    suffix = ALLOWED.get(mime)
    if not suffix:
        # 按文件名后缀兜底判断
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext in {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".html", ".md"}:
            suffix = ext
        else:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {mime or ext or 'unknown'}",
            )

    # 大小检查
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    # MarkItDown 转换
    try:
        from markitdown import MarkItDown
        md_converter = MarkItDown()

        # 写到临时文件（MarkItDown 需要文件路径）
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = md_converter.convert(tmp_path)
            markdown_text = result.text_content.strip()
        finally:
            os.unlink(tmp_path)

    except ImportError:
        raise HTTPException(status_code=503, detail="MarkItDown not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)[:200]}")

    if not markdown_text:
        raise HTTPException(status_code=422, detail="File converted to empty content")

    # 存进记忆库（按段分割，每段最多 2000 字符，避免单条记忆太长）
    db = get_db()
    user_id = current_user["sub"]
    filename = file.filename or "imported_file"

    # 加文件名前缀，方便以后搜索
    header = f"[来自文件: {filename}]\n\n"
    full_content = header + markdown_text

    # 分段存储（超过 2000 字的文件拆成多条记忆）
    CHUNK = 1800
    chunks = [full_content[i:i + CHUNK] for i in range(0, len(full_content), CHUNK)]

    inserted_ids = []
    for i, chunk in enumerate(chunks):
        label = f" (第{i+1}/{len(chunks)}段)" if len(chunks) > 1 else ""
        row = {
            "user_id":  user_id,
            "content":  chunk + label,
            "category": category,
        }
        res = db.table("memories").insert(row).execute()
        if res.data:
            inserted_ids.append(res.data[0]["id"])

    return {
        "memory_ids":   inserted_ids,
        "chunks":       len(chunks),
        "total_chars":  len(markdown_text),
        "preview":      markdown_text[:300],
        "filename":     filename,
    }
