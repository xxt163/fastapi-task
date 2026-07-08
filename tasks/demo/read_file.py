

def run(data: dict):
    file_path = data.get("file_path", r"D:\Workspace\11.xlsx")
    print(f"文件路径: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        print(f"成功读取 {len(text)} 个字符")

    return text


if __name__ == "__main__":
    print(run({"file_path": "F:\\test.txt"}))
