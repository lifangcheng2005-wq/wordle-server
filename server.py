import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

games_db: Dict[str, dict] = {}
total_games = 0
wins_count = 0

class NewGameRequest(BaseModel):
    hard_mode: Optional[bool] = False

class GuessRequest(BaseModel):
    game_id: str
    guess: str

def get_stats_dict():
    global total_games, wins_count
    rate = round((wins_count / total_games * 100), 1) if total_games > 0 else 0
    return {"total": total_games, "wins": wins_count, "win_rate": rate}

@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = None):
    global total_games
    total_games += 1
    
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    hard_mode = req.hard_mode if req else False
    
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "hard_mode": hard_mode,
        "green_hints": {},
        "guesses_count": 0
    }
    return {"game_id": game_id, "message": "New game started!"}

@app.get("/api/stats")
def get_stats():
    return get_stats_dict()

@app.post("/api/guess")
def process_guess(req: GuessRequest):
    global wins_count
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：檢查字典庫
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    game_info = games_db[game_id]
    if game_info["status"] != "PLAYING":
        raise HTTPException(status_code=400, detail="Game already ended.")

    game_info["guesses_count"] += 1
    target = game_info["target"]
    hard_mode = game_info["hard_mode"]
    green_hints = game_info["green_hints"]

    # 任務四：Hard Mode 驗證
    if hard_mode:
        for idx_str, char in green_hints.items():
            idx = int(idx_str)
            if guess[idx] != char:
                raise HTTPException(status_code=400, detail="Hard Mode: Must use revealed hint at green position")

    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            green_hints[str(i)] = guess[i]

    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    is_correct = (guess == target)
    is_game_over = is_correct or (game_info["guesses_count"] >= 6)

    if is_correct:
        game_info["status"] = "WON"
        wins_count += 1
    elif game_info["guesses_count"] >= 6:
        game_info["status"] = "LOST"

    # 任務一：未結束回傳 None，遊戲結束（猜對或滿 6 次）才回傳 target_word
    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target if is_game_over else None,
        "stats": get_stats_dict()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
