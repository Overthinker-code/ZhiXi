from __future__ import annotations

import shutil
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.config import settings  # noqa: E402
from app.services.teaching_artifact_service import teaching_artifact_service  # noqa: E402


PROMPT = """美国某大学共有200名教师，校方与教师工会刚刚签订一项协议。按照协议，
所有年工资超过$26000（含$26000）的教师工资将保持不变，年工资少于$26000的教师将增加工资：
每个由教师所赡养的人（包括教师本人）每年补助$100，教师每有一年工龄每年再补助$50，
但增加后的年工资总额不能多于$26000。教师工资档案包含目前年工资、赡养人数、雇用日期等信息。
程序需要计算并印出每名教师的原有工资和调整后的新工资。画出此系统的数据流图。
给我生成图片，不要插图，不要Mermaid，黑字白底的图片。"""


def main() -> None:
    artifact = teaching_artifact_service.generate_data_flow_diagram("教师工资调整系统", PROMPT)
    source = Path(settings.BASE_PATH) / "uploads" / "generated_images" / artifact["file_name"]
    output = ROOT / "output" / "教师工资调整系统_数据流图_DFD.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    print(output)


if __name__ == "__main__":
    main()
