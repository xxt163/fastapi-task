def read_excel(file_path: str):
    import pandas as pd

    df = pd.read_excel(file_path)
    return df


def run(data: dict):
    # file_path = data.get("file_path")
    file_path = "/home/xxt/data/11.xlsx"
    df = read_excel(file_path)
    return df.to_dict()
