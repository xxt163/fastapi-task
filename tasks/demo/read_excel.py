import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


def read_excel(file_path: str):
    import pandas as pd

    df = pd.read_excel(file_path)
    return df


def run(data: dict):
    logger.info("开始读取 Excel 文件", extra={"file_path": data.get("file_path")})

    file_path = data.get("file_path", "/home/xxt/data/11.xlsx")
    logger.info(f"文件路径: {file_path}")

    df = read_excel(file_path)
    logger.info(f"成功读取 {len(df)} 行数据")

    return df.to_dict()


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    )
    logger.addHandler(handler)
    print(run({"file_path": "/home/xxt/data/11.xlsx"}))
