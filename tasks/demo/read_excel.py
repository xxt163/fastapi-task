import pandas as pd


def read_excel(file_path: str):
    df = pd.read_excel(file_path)
    return df


def run(data: dict):
    file_path = data.get("file_path", r"D:\Workspace\11.xlsx")
    print(f"文件路径: {file_path}")

    df = read_excel(file_path)
    print(f"成功读取 {len(df)} 行数据")

    return df.to_dict()


if __name__ == "__main__":
    print(run({"file_path": r"D:\Workspace\11.xlsx"}))
