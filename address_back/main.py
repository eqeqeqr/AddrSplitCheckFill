import os
import sys
import webbrowser
import threading
import time
from pathlib import Path


class _LogFileWriter:
    """只写入日志文件的 writer，用于 uvicorn 启动后的输出"""

    def __init__(self, log_file):
        self._log_file = log_file

    def write(self, text):
        self._log_file.write(text)
        self._log_file.flush()

    def flush(self):
        self._log_file.flush()

    def isatty(self):
        return False


def _get_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _setup_logging(app_root: Path):
    log_dir = app_root / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "server.log"
    log_file = open(log_path, "a", encoding="utf-8")
    return log_path, log_file


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
    log_path, log_file = _setup_logging(app_root)

    print("=" * 60)
    print("地址拆分工具")
    print("=" * 60)
    print("正在启动服务，请稍候...")
    print(f"日志文件：{log_path}")
    print("按 Ctrl+C 或关闭窗口停止服务")
    print("=" * 60)

    check_environment(app_root)

    host = "127.0.0.1"
    port = 8008
    url = f"http://{host}:{port}/split"

    open_browser(url, delay=3.0)

    # 启动后将所有输出重定向到日志文件，控制台只保留启动信息
    tee_writer = _LogFileWriter(log_file)
    sys.stdout = tee_writer
    sys.stderr = tee_writer

    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
