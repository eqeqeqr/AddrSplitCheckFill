import os
import sys
import webbrowser
import threading
import time
from pathlib import Path


def _get_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def check_environment(app_root: Path) -> None:
    if getattr(sys, 'frozen', False):
        return
    iic_dir = app_root / "iic"
    if not iic_dir.exists():
        print("=" * 60)
        print("错误：未找到模型目录 iic/")
        print("=" * 60)
        print(f"请将 iic 文件夹放在以下位置：{app_root}")
        print("iic 文件夹包含地址解析所需的 MGeo 模型文件。")
        print("=" * 60)
        input("按回车键退出...")
        sys.exit(1)


def open_browser(url: str, delay: float = 1.5) -> None:
    def _open():
        time.sleep(delay)
        webbrowser.open(url)
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


if __name__ == "__main__":
    app_root = _get_app_root()
    check_environment(app_root)

    host = "127.0.0.1"
    port = 8008
    url = f"http://{host}:{port}"

    print("=" * 60)
    print("地址拆分工具")
    print("=" * 60)
    print(f"服务地址：{url}")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    open_browser(url)

    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
