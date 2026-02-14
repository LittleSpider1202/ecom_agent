"""工具 API"""
import asyncio
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post("/file-picker")
async def file_picker(
    accept: Optional[str] = Query(None, description="文件类型过滤，如 .pdf"),
    multiple: bool = Query(True, description="是否多选"),
    title: Optional[str] = Query(None, description="对话框标题"),
):
    """打开原生文件选择对话框，返回完整路径"""
    def _pick():
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        filetypes = [("All files", "*.*")]
        if accept:
            exts = " ".join(f"*{e.strip()}" for e in accept.split(","))
            filetypes.insert(0, (f"指定文件 ({accept})", exts))

        dialog_title = title or "选择文件"

        if multiple:
            files = filedialog.askopenfilenames(
                title=dialog_title,
                filetypes=filetypes,
            )
        else:
            f = filedialog.askopenfilename(
                title=dialog_title,
                filetypes=filetypes,
            )
            files = (f,) if f else ()

        root.destroy()
        return [str(f) for f in files if f]

    # tkinter 必须在主线程或独立线程运行
    files = await asyncio.to_thread(_pick)
    return {"files": files}
