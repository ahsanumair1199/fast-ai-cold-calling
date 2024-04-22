import os


def create_structure():
    dirs = [
        os.path.join("config"),
        os.path.join("src", "agents_toolbox"),
        os.path.join("src", "utils")
    ]

    for dir_ in dirs:
        os.makedirs(dir_, exist_ok=True)
        with open(os.path.join(dir_, ".gitkeep"), "w") as f:
            pass

    files = [
        ".gitignore",
        "README.md",
        "setup.py",
        os.path.join("src", "__init__.py"),
        os.path.join("src", "utils", "__init__.py"),
        os.path.join("config", "params.yaml"),
        os.path.join("config", "system.yaml"),
    ]

    for file in files:
        if not os.path.exists(file):
            with open(file, "w") as f:
                pass


if __name__ == "__main__":
    create_structure()
