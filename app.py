from flask import flash
import openai
import requests
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///words.db'
db = SQLAlchemy(app)

# 設定 OpenAI API 金鑰（記得換成你的 API Key）
OPENAI_API_KEY = "你的 API 金鑰"

# 建立單字資料表
class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(50), nullable=False)
    translation = db.Column(db.String(100), nullable=False)
    example_sentence_en = db.Column(db.String(255), nullable=True)
    example_sentence_zh = db.Column(db.String(255), nullable=True)
    familiarity = db.Column(db.Integer, default=1)
    next_review = db.Column(db.Date, default=datetime.date.today())

# 初始化資料庫
with app.app_context():
    db.create_all()

# **使用 Google 翻譯 API**
def translate_word(word):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": "zh-TW",
        "dt": "t",
        "q": word,
    }
    response = requests.get(url, params=params, verify=False)
    if response.status_code == 200:
        return response.json()[0][0][0]
    return "翻譯失敗"

def generate_example_sentence(word):
    url = f"https://tatoeba.org/en/api_v0/search?query={word}&from=eng&to=eng"
    
    try:
        response = requests.get(url, verify=False)  # ✅ 關閉 SSL 憑證驗證
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                english_sentence = data["results"][0]["text"]  # 取第一個例句
                
                # 使用 Google 翻譯翻譯成中文
                translation_url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    "client": "gtx",
                    "sl": "en",
                    "tl": "zh-TW",
                    "dt": "t",
                    "q": english_sentence,
                }
                response_zh = requests.get(translation_url, params=params, verify=False)
                chinese_sentence = response_zh.json()[0][0][0]
                
                return english_sentence, chinese_sentence
    except Exception as e:
        print("Tatoeba API 錯誤:", e)

    return f"{word} is an important word.", "這是一個重要的單字。"



@app.route('/')
def index():
    words = Word.query.all()
    return render_template('index.html', words=words)

@app.route('/add', methods=['POST'])
def add_word():
    word = request.form['word'].strip()  # 去除左右空白
    # 檢查是否重複輸入（不區分大小寫，可以依需求調整）
    if Word.query.filter(Word.word.ilike(word)).first():
        flash("這個單字已經存在！", "warning")
        return redirect(url_for('index'))
    
    translation = translate_word(word)  # Google 翻譯
    example_sentence_en, example_sentence_zh = generate_example_sentence(word)  # AI 例句
    
    new_word = Word(word=word, translation=translation, 
                    example_sentence_en=example_sentence_en, 
                    example_sentence_zh=example_sentence_zh)
    db.session.add(new_word)
    db.session.commit()
    
    flash("單字已新增！", "success")
    return redirect(url_for('index'))


@app.route('/quiz')
def quiz():
    words = Word.query.all()
    if words:
        question_word = random.choice(words)
        return render_template('quiz.html', word=question_word)
    return "No words available for quiz."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
