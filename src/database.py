import json
import os
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "games_db.json"
COVERS_DIR = Path(__file__).parent.parent / "covers"

class GameDB:
    def __init__(self):
        self.db_path = DB_PATH
        self.covers_dir = COVERS_DIR
        self.covers_dir.mkdir(exist_ok=True)
        self.data = self.load()

    def load(self):
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"games": []}

    def save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, name, exe_path, cover=None):
        game = {
            "id": uuid.uuid4().hex[:8],
            "name": name,
            "exe_path": exe_path,
            "cover": cover,
            "added_time": datetime.now().isoformat()
        }
        self.data["games"].append(game)
        self.save()
        return game

    def remove(self, game_id):
        self.data["games"] = [g for g in self.data["games"] if g["id"] != game_id]
        self.save()

    def update(self, game_id, **kwargs):
        for g in self.data["games"]:
            if g["id"] == game_id:
                g.update(kwargs)
                self.save()
                return g
        return None

    def get_all(self):
        return self.data["games"]

    def get_by_id(self, game_id):
        for g in self.data["games"]:
            if g["id"] == game_id:
                return g
        return None
