#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini統合版
正確な天文計算 + Gemini AIによる豊かな文章生成
"""

import os
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']


class AccurateSolarTermCalculator:
    """正確な太陽黄経計算による二十四節気・七十二候算出"""
    
    @staticmethod
    def calculate_solar_longitude(dt):
        """指定日時の太陽黄経を計算"""
        jst = ZoneInfo("Asia/Tokyo")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=jst)
        
        y = dt.year
        m = dt.month
        d = dt.day + (dt.hour + dt.minute/60.0 + dt.second/3600.0)/24.0
        
        if m <= 2:
            y -= 1
            m += 12
        
        a = int(y / 100)
        b = 2 - a + int(a / 4)
        jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
        T = (jd - 2451545.0) / 36525.0
        
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
        M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
        M_rad = math.radians(M)
        
        C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
        C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
        C += 0.000289 * math.sin(3 * M_rad)
        
        true_longitude = L0 + C
        omega = 125.04 - 1934.136 * T
        lambda_sun = true_longitude - 0.00569 - 0.00478 * math.sin(math.radians(omega))
        
        lambda_sun = lambda_sun % 360
        if lambda_sun < 0:
            lambda_sun += 360
            
        return lambda_sun
    
    @classmethod
    def get_current_sekki(cls, date):
        """現在の二十四節気を取得"""
        sekki_data = [
            (315, "立春", "りっしゅん"), (330, "雨水", "うすい"), (345, "啓蟄", "けいちつ"),
            (0, "春分", "しゅんぶん"), (15, "清明", "せいめい"), (30, "穀雨", "こくう"),
            (45, "立夏", "りっか"), (60, "小満", "しょうまん"), (75, "芒種", "ぼうしゅ"),
            (90, "夏至", "げし"), (105, "小暑", "しょうしょ"), (120, "大暑", "たいしょ"),
            (135, "立秋", "りっしゅう"), (150, "処暑", "しょしょ"), (165, "白露", "はくろ"),
            (180, "秋分", "しゅうぶん"), (195, "寒露", "かんろ"), (210, "霜降", "そうこう"),
            (225, "立冬", "りっとう"), (240, "小雪", "しょうせつ"), (255, "大雪", "たいせつ"),
            (270, "冬至", "とうじ"), (285, "小寒", "しょうかん"), (300, "大寒", "だいかん")
        ]
        
        longitude = cls.calculate_solar_longitude(date)
        current_sekki = sekki_data[0]
        
        for i in range(len(sekki_data)):
            deg, name, reading = sekki_data[i]
            next_deg = sekki_data[(i + 1) % len(sekki_data)][0]
            
            if deg <= next_deg:
                if deg <= longitude < next_deg:
                    current_sekki = (name, reading)
                    break
            else:
                if longitude >= deg or longitude < next_deg:
                    current_sekki = (name, reading)
                    break
        
        return current_sekki
    
    @classmethod
    def get_current_kou(cls, date):
        """現在の七十二候を取得"""
        kou_data = [
            (1, 5, "芹乃栄", "せりすなわちさかう"), (1, 10, "水泉動", "しみずあたたかをふくむ"),
            (1, 15, "雉始雊", "きじはじめてなく"), (1, 20, "款冬華", "ふきのはなさく"),
            (1, 25, "水沢腹堅", "さわみずこおりつめる"), (1, 30, "鶏始乳", "にわとりはじめてとやにつく"),
            (2, 4, "東風解凍", "はるかぜこおりをとく"), (2, 9, "黄鶯睍睆", "うぐいすなく"),
            (2, 14, "魚上氷", "うおこおりをいずる"), (2, 19, "土脉潤起", "つちのしょううるおいおこる"),
            (2, 24, "霞始靆", "かすみはじめてたなびく"), (2, 29, "草木萌動", "そうもくめばえいずる"),
            (3, 5, "蟄虫啓戸", "すごもりむしとをひらく"), (3, 10, "桃始笑", "ももはじめてさく"),
            (3, 15, "菜虫化蝶", "なむしちょうとなる"), (3, 20, "雀始巣", "すずめはじめてすくう"),
            (3, 25, "櫻始開", "さくらはじめてひらく"), (3, 30, "雷乃発声", "かみなりすなわちこえをはっす"),
            (4, 4, "玄鳥至", "つばめきたる"), (4, 9, "鴻雁北", "こうがんかえる"),
            (4, 14, "虹始見", "にじはじめてあらわる"), (4, 20, "葭始生", "あしはじめてしょうず"),
            (4, 25, "霜止出苗", "しもやんでなえいず"), (4, 30, "牡丹華", "ぼたんはなさく"),
            (5, 5, "蛙始鳴", "かわずはじめてなく"), (5, 10, "蚯蚓出", "みみずいずる"),
            (5, 15, "竹笋生", "たけのこしょうず"), (5, 21, "蚕起食桑", "かいこおきてくわをはむ"),
            (5, 26, "紅花栄", "べにばなさかう"), (5, 31, "麦秋至", "むぎのときいたる"),
            (6, 5, "蟷螂生", "かまきりしょうず"), (6, 10, "腐草為螢", "くされたるくさほたるとなる"),
            (6, 16, "梅子黄", "うめのみきばむ"), (6, 21, "乃東枯", "なつかれくさかるる"),
            (6, 26, "菖蒲華", "あやめはなさく"), (7, 2, "半夏生", "はんげしょうず"),
            (7, 7, "温風至", "あつかぜいたる"), (7, 12, "蓮始開", "はすはじめてひらく"),
            (7, 17, "鷹乃学習", "たかすなわちわざをならう"), (7, 22, "桐始結花", "きりはじめてはなをむすぶ"),
            (7, 28, "土潤溽暑", "つちうるおうてむしあつし"), (8, 2, "大雨時行", "たいうときどきふる"),
            (8, 7, "涼風至", "すずかぜいたる"), (8, 12, "寒蝉鳴", "ひぐらしなく"),
            (8, 17, "蒙霧升降", "ふかききりまとう"), (8, 23, "綿柎開", "わたのはなしべひらく"),
            (8, 28, "天地始粛", "てんちはじめてさむし"), (9, 2, "禾乃登", "こくものすなわちみのる"),
            (9, 7, "草露白", "くさのつゆしろし"), (9, 12, "鶺鴒鳴", "せきれいなく"),
            (9, 17, "玄鳥去", "つばめさる"), (9, 23, "雷乃収声", "かみなりすなわちこえをおさむ"),
            (9, 28, "蟄虫坏戸", "むしかくれてとをふさぐ"), (10, 3, "水始涸", "みずはじめてかるる"),
            (10, 8, "鴻雁来", "こうがんきたる"), (10, 13, "菊花開", "きくのはなひらく"),
            (10, 18, "蟋蟀在戸", "きりぎりすとにあり"), (10, 23, "霜始降", "しもはじめてふる"),
            (10, 28, "霎時施", "こさめときどきふる"), (11, 2, "楓蔦黄", "もみじつたきばむ"),
            (11, 7, "山茶始開", "つばきはじめてひらく"), (11, 12, "地始凍", "ちはじめてこおる"),
            (11, 17, "金盞香", "きんせんかさく"), (11, 22, "虹蔵不見", "にじかくれてみえず"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう"), (12, 2, "橘始黄", "たちばなはじめてきばむ"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる"), (12, 12, "熊蟄穴", "くまあなにこもる"),
            (12, 16, "鱖魚群", "さけのうおむらがる"), (12, 21, "乃東生", "なつかれくさしょうず"),
            (12, 26, "麋角解", "さわしかつのおつる"), (12, 31, "雪下出麦", "ゆきわたりてむぎのびる")
        ]
        
        month = date.month
        day = date.day
        
        current_kou = kou_data[0][2:]
        for m, d, name, reading in reversed(kou_data):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading)
                break
        
        return current_kou


class AccurateLunarCalendar:
    """正確な旧暦計算"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """旧暦を計算"""
        reference = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        reference_lunar_year, reference_lunar_month, reference_lunar_day = 2025, 10, 21
        reference_moon_age, synodic = 19.8, 29.530588861
        
        elapsed_days = (date - reference).total_seconds() / 86400
        moon_age = (reference_moon_age + elapsed_days) % synodic
        if moon_age < 0:
            moon_age += synodic
        
        elapsed_months = int((reference_moon_age + elapsed_days) / synodic)
        lunar_year, lunar_month, lunar_day = reference_lunar_year, reference_lunar_month, reference_lunar_day
        
        for _ in range(abs(elapsed_months)):
            if elapsed_months > 0:
                lunar_month += 1
                if lunar_month > 12:
                    lunar_month, lunar_year = 1, lunar_year + 1
            else:
                lunar_month -= 1
                if lunar_month < 1:
                    lunar_month, lunar_year = 12, lunar_year - 1
        
        days_in_current_month = elapsed_days - (elapsed_months * synodic)
        lunar_day = reference_lunar_day + int(days_in_current_month)
        
        while lunar_day > 30:
            lunar_day -= 30
            lunar_month += 1
            if lunar_month > 12:
                lunar_month, lunar_year = 1, lunar_year + 1
        
        while lunar_day < 1:
            lunar_day += 30
            lunar_month -= 1
            if lunar_month < 1:
                lunar_month, lunar_year = 12, lunar_year - 1
        
        phase_data = [
            (1.5, "新月", "夜空に月は見えません"),
            (3.7, "二日月", "夕方の西空に細い月が輝きます"),
            (7.4, "上弦へ向かう月", "夕方の空に弓なりの月"),
            (11, "上弦の月", "宵の空に半月が見えます"),
            (14.8, "満月へ向かう月", "宵から夜半にかけて膨らむ月"),
            (16.3, "満月", "夜通し輝く丸い月"),
            (22.1, "下弦へ向かう月", "夜半から明け方に欠けていく月"),
            (25.9, "下弦の月", "明け方に半月が見えます"),
            (30, "晦日月", "明け方の東空に細い月")
        ]
        
        phase, appearance = "晦日月", "明け方の東空に細い月"
        for threshold, p, a in phase_data:
            if moon_age < threshold:
                phase, appearance = p, a
                break
        
        lunar_month_names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
            7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        
        return {
            'year': lunar_year, 'month': lunar_month, 'day': lunar_day,
            'age': round(moon_age, 1), 'phase': phase, 'appearance': appearance,
            'month_name': lunar_month_names.get(lunar_month, "")
        }


class GeminiContentGenerator:
    """Gemini APIを使用したコンテンツ生成"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
    
    def generate_content(self, date, lunar, sekki, kou):
        """Geminiで文章生成"""
        
        prompt = f"""本日の暦情報にもとづいて、以下の指示に従って自然・歴史・信仰・暮らしの視点から文化的背景とともに網羅的に詳しく、豊かで情緒的な表現で解説してください。
文章は適度に改行してください。

【本日の暦情報】
・西暦: {date.year}年{date.month}月{date.day}日
・旧暦: {lunar['month']}月{lunar['day']}日（{lunar['month_name']}）
・月齢: {lunar['age']}（{lunar['phase']}）
・二十四節気: {sekki[0]}（{sekki[1]}）
・七十二候: {kou[0]}（{kou[1]}）

🎭 1. 役割（ペルソナ）の指定
あなたは暦・季節・日本文化に深く通じた案内人。単なる日付情報ではなく、「暮らし・信仰・文化・自然のつながり」を語る存在として、日本の四季・自然観・農耕文化を大切に解説してください。

📅 2. 必ず次のような章立てで出力
回答は前置きを一切付けず、「☀️ 季節の移ろい」から開始し、🎼 伝統芸能の内容まで出力し、それ以降は一切書かないこと。
章立ては以下の通りとし、表形式は絶対に使用しないで、箇条書きで網羅的に詳しく、豊かで情緒的な表現で解説してください。

☀️ 季節の移ろい（二十四節気・七十二候）
🎌 記念日・祝日
💡 暦にまつわる文化雑学
🚜 農事歴
🏡 日本の風習・しきたり
📚 神話・伝説
🍁 自然・気象
🍴 旬の食
🌸 季節の草木
🌕 月や星の暦・天文情報
🎨 伝統工芸
🎼 伝統芸能"""
        
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.8,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                }
            }
            
            response = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content
            
            print(f"Gemini APIエラー: {response.status_code}")
            return None
                
        except Exception as e:
            print(f"Gemini API呼び出しエラー: {str(e)}")
            return None


class CalendarPostGenerator:
    """暦情報投稿生成"""
    
    def __init__(self, date=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = date or datetime.now(self.jst)
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
    def generate_post(self):
        """投稿を生成"""
        lunar = AccurateLunarCalendar.calculate_lunar_date(self.date)
        sekki = AccurateSolarTermCalculator.get_current_sekki(self.date)
        kou = AccurateSolarTermCalculator.get_current_kou(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        # 基本情報セクション（プログラムで生成）
        basic_info = f"""<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">📅 今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 24px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 15px 0 0 0; font-size: 20px;">旧暦: {lunar['month']}月{lunar['day']}日（{lunar['month_name']}）</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 17px; opacity: 0.95; line-height: 1.7;">{lunar['appearance']}</p>
</div>

<div style="background: #f7fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #4299e1; margin-bottom: 35px;">
<p style="margin: 0 0 10px 0; font-size: 18px;"><strong>二十四節気:</strong> {sekki[0]}（{sekki[1]}）</p>
<p style="margin: 0; font-size: 18px;"><strong>七十二候:</strong> {kou[0]}（{kou[1]}）</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">
"""
        
        # Geminiでコンテンツ生成
        print("Gemini APIでコンテンツを生成中...")
        generator = GeminiContentGenerator(self.gemini_api_key)
        gemini_content = generator.generate_content(self.date, lunar, sekki, kou)
        
        if not gemini_content:
            print("警告: Geminiコンテンツの生成に失敗しました。デフォルトコンテンツを使用します。")
            gemini_content = self._generate_fallback_content(lunar, sekki, kou)
        
        # HTML整形
        gemini_html = self._format_gemini_content(gemini_content)
        
        # 締めの挨拶
        closing = """
<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
<p style="margin: 0; font-size: 18px; color: #14532d; font-weight: 500; line-height: 2;">
季節を感じながら、今日も良い一日をお過ごしください
</p>
</div>

</div>"""
        
        full_content = basic_info + gemini_html + closing
        
        return {
            'title': f'{self.date.year}年{self.date.month}月{self.date.day}日({weekday})の暦情報',
            'content': full_content,
            'labels': ['暦', '二十四節気', '旧暦', '季節', '七十二候', '農事歴', '風習', '伝統文化', '行事食', '天文', '神話', '伝統芸能']
        }
    
    def _format_gemini_content(self, content):
        """Geminiコンテンツを HTML形式に整形"""
        sections = content.split('\n\n')
        html_parts = []
        
        section_styles = {
            '☀️': '#fc8181',
            '🎌': '#f6ad55',
            '💡': '#4299e1',
            '🚜': '#68d391',
            '🏡': '#9f7aea',
            '📚': '#ed64a6',
            '🍁': '#38b2ac',
            '🍴': '#f56565',
            '🌸': '#f687b3',
            '🌕': '#4299e1',
            '🎨': '#ed8936',
            '🎼': '#805ad5'
        }
        
        for section in sections:
            if not section.strip():
                continue
            
            # セクションタイトルを検出
            for emoji, color in section_styles.items():
                if section.startswith(emoji):
                    title_end = section.find('\n')
                    if title_end > 0:
                        title = section[:title_end]
                        body = section[title_end+1:]
                        
                        html_parts.append(f"""
<h3 style="color: #2d3748; font-size: 26px; margin: 35px 0 25px 0; border-left: 6px solid {color}; padding-left: 15px;">{title}</h3>
<div style="background: #f7fafc; padding: 25px; border-radius: 12px; margin-bottom: 30px; border-left: 4px solid {color};">
<div style="color: #2d3748; line-height: 2; font-size: 16px; white-space: pre-wrap;">{body}</div>
</div>
""")
                    break
        
        return ''.join(html_parts)
    
    def _generate_fallback_content(self, lunar, sekki, kou):
        """フォールバックコンテンツ"""
        return f"""☀️ 季節の移ろい（二十四節気・七十二候）

本日は二十四節気の「{sekki[0]}」、七十二候では「{kou[0]}」の時期です。
日本の伝統的な暦は、太陽の動きと自然の変化を繊細に捉えています。

🎌 記念日・祝日

本日の記念日をご確認ください。

💡 暦にまつわる文化雑学

旧暦{lunar['month']}月は「{lunar['month_name']}」と呼ばれています。

🚜 農事歴

この時期の農作業についてご紹介します。

🏡 日本の風習・しきたり

季節に応じた風習があります。

📚 神話・伝説

日本の神話と暦の関わりは深いものがあります。

🍁 自然・気象

この時期の自然の変化を感じてください。

🍴 旬の食

季節の美味しい食材を楽しみましょう。

🌸 季節の草木

今の時期に見られる草花をご紹介します。

🌕 月や星の暦・天文情報

月齢{lunar['age']}の{lunar['phase']}です。

🎨 伝統工芸

季節に関連する伝統工芸があります。

🎼 伝統芸能

この時期に関連する伝統芸能をご紹介します。"""


class BloggerPoster:
    """Blogger投稿クラス"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        
    def authenticate(self):
        """Google APIの認証"""
        creds = None
        
        if os.environ.get('GOOGLE_TOKEN'):
            token_data = json.loads(os.environ['GOOGLE_TOKEN'])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.environ.get('GOOGLE_CREDENTIALS'):
                    creds_data = json.loads(os.environ['GOOGLE_CREDENTIALS'])
                    flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise Exception("認証情報が見つかりません")
        
        self.credentials = creds
        self.service = build('blogger', 'v3', credentials=creds)
        
    def post_to_blog(self, blog_id, title, content, labels):
        """Bloggerに投稿"""
        try:
            post = {
                'kind': 'blogger#post',
                'title': title,
                'content': content,
                'labels': labels
            }
            
            request = self.service.posts().insert(blogId=blog_id, body=post)
            response = request.execute()
            
            print(f"投稿成功: {response.get('url')}")
            return response
            
        except Exception as e:
            print(f"投稿エラー: {str(e)}")
            raise


def main():
    """メイン処理"""
    try:
        blog_id = os.environ.get('BLOG_ID')
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        if not gemini_api_key:
            raise Exception("GEMINI_API_KEY環境変数が設定されていません")
        
        print("=" * 70)
        print("暦情報自動投稿システム Gemini統合版 起動")
        print("=" * 70)
        print(f"投稿日時: {datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')}")
        
        # 暦情報生成
        print("\n今日の暦情報を生成中...")
        print("- 正確な天文計算による二十四節気・七十二候")
        print("- Gemini AIによる豊かな文章生成")
        
        generator = CalendarPostGenerator()
        post_data = generator.generate_post()
        
        print(f"\nタイトル: {post_data['title']}")
        print(f"推定文字数: 約{len(post_data['content'])}文字")
        
        # Blogger投稿
        print("\nBloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 70)
        print("すべての処理が完了しました！")
        print("正確な暦情報とGemini生成の豊かな文章が投稿されました")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
