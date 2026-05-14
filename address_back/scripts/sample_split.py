from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.address import ColumnMode
from app.services.split_service import split_excel_file


if __name__ == "__main__":
    excel_path = Path(__file__).resolve().parents[2] / "excel" / "test_address.xlsx"
    job_id, result_df, detail = split_excel_file(
        excel_path,
        column_mode=ColumnMode.level11,
        scene_field="level_7",
        sample_size=100,
    )
    print(f"job_id={job_id}")
    print(f"total_rows={detail.total_rows}, processed_rows={detail.processed_rows}")
    print(f"columns={list(result_df.columns)}")
    print(f"result_file={detail.result_file}")
    print(result_df.head(3).to_string(index=False))
