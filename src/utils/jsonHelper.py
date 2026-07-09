import json

def saveAsJSON(obj, path: str):
    """saves objects or nested objects as json"""
    with open(path, mode="w", encoding="utf-8") as file:
        json.dump(obj, file, indent=4, default=lambda obj: obj.__dict__)

def loadJSON(path):
    """returns the json date of the file"""
    with open(path, mode="r", encoding="utf-8") as file:
        return json.load(file)

