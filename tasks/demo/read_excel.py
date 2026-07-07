from tasks._utils import get_logger

logger = get_logger(__name__)



def read_excel(file_path: str):
    import pandas as pd

    df = pd.read_excel(file_path)
    return df


def run(data: dict):
    logger.info("开始读取 Excel 文件", extra={"file_path": data.get("file_path")})

    file_path = data.get("file_path", r"D:\Workspace\11.xlsx")
    logger.info(f"文件路径: {file_path}")

    df = read_excel(file_path)
    logger.info(f"成功读取 {len(df)} 行数据")

    return df.to_dict()


if __name__ == "__main__":
    from tasks._utils import run_main
    run_main(run, {"file_path": r"D:\Workspace\11.xlsx"})
