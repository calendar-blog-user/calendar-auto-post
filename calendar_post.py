#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini統合版（改善版）
正確な天文計算 + Gemini AIによる豊かな文章生成
"""

import os
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import requests
import time
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
        
        # 六曜を計算
        rokuyou_list = ["大安", "赤口", "先勝", "友引", "先負", "仏滅"]
        rokuyou_index = (lunar_month + lunar_day) % 6
        rokuyou = rokuyou_list[rokuyou_index]
        
        return {
            'year': lunar_year, 'month': lunar_month, 'day': lunar_day,
            'age': round(moon_age, 1), 'phase': phase, 'appearance': appearance,
            'month_name': lunar_month_names.get(lunar_month, ""),
            'rokuyou': rokuyou
        }


class SunCalculator:
    """日の出・日の入り計算（岡山）"""
    
    @staticmethod
    def calculate_sunrise_sunset(date):
        """岡山の日の出・日の入り時刻を計算"""
        # 岡山の座標（北緯34.67度、東経133.92度）
        latitude = 34.67
        longitude = 133.92
        
        # 年の通日（1月1日を1とする）
        day_of_year = date.timetuple().tm_yday
        
        # 太陽の赤緯を計算（簡易計算）
        declination = 23.44 * math.sin(math.radians((360/365) * (day_of_year - 81)))
        
        # 時角を計算
        lat_rad = math.radians(latitude)
        dec_rad = math.radians(declination)
        
        cos_hour_angle = -math.tan(lat_rad) * math.tan(dec_rad)
        
        # 極夜・白夜のチェック
        if cos_hour_angle > 1:
            hour_angle = 0  # 極夜
        elif cos_hour_angle < -1:
            hour_angle = 180  # 白夜
        else:
            hour_angle = math.degrees(math.acos(cos_hour_angle))
        
        # 均時差の計算（簡易版）
        b = math.radians((360/365) * (day_of_year - 81))
        equation_of_time = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
        
        # 経度による時差補正（日本標準時は東経135度基準）
        time_correction = 4 * (135 - longitude) + equation_of_time
        
        # 日の出・日の入り時刻の計算
        sunrise_time = 12 - (hour_angle / 15) - (time_correction / 60)
        sunset_time = 12 + (hour_angle / 15) - (time_correction / 60)
        
        # 時刻をHH:MM形式に変換
        def to_time_string(decimal_hour):
            hour = int(decimal_hour)
            minute = int((decimal_hour - hour) * 60)
            return f"{hour:02d}:{minute:02d}"
        
        return {
            'sunrise': to_time_string(sunrise_time),
            'sunset': to_time_string(sunset_time)
        }


class GeminiContentGenerator:
    """Gemini APIを使用したコンテンツ生成"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        # Gemini 2.5 Flash（最新の正式モデル）を使用
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    def generate_content(self, date, lunar, sekki, kou):
        """Geminiで文章生成"""
        
        prompt = f"""あなたは日本の暦・季節・伝統文化に精通した親しみやすい案内人です。
以下の本日の暦情報をもとに、読者が季節を身近に感じられるよう、温かみのある自然な語り口で解説してください。

【本日の暦情報】
・西暦: {date.year}年{date.month}月{date.day}日
・旧暦: {lunar['month']}月{lunar['day']}日（{lunar['month_name']}）
・六曜: {lunar['rokuyou']}
・月齢: {lunar['age']}（{lunar['phase']}）
・二十四節気: {sekki[0]}（{sekki[1]}）
・七十二候: {kou[0]}（{kou[1]}）

【最重要：必ず守る書式ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 段落は2-3文書いたら**必ず空行**を入れること
2. 段落と段落の間には**必ず空の行**を1行入れること
3. 箇条書きの前後にも**必ず空行**を入れること
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【正しい書式の例】
```
今は二十四節気の「大雪」の時期です。この頃は雪が本格的に降り始めます。

七十二候では「熊蟄穴」を迎えています。動物たちが冬眠する頃です。

この季節のポイント:

* **雪の季節**：山々が白く染まります
* **冬支度**：暖かく過ごす準備が大切です

外は寒いですが、家族との団らんが温かいですね。
```

【悪い例（絶対にこうしないこと）】
```
今は二十四節気の「大雪」の時期です。この頃は雪が本格的に降り始めます。七十二候では「熊蟄穴」を迎えています。動物たちが冬眠する頃です。この季節のポイント:
* **雪の季節**：山々が白く染まります
* **冬支度**：暖かく過ごす準備が大切です
外は寒いですが、家族との団らんが温かいですね。
```

【文体ルール】
- 「ですます調」で親しみやすく
- 「でございます」などの古風な表現は使わない
- 各セクションは300文字以上で具体的に

【出力フォーマット】
以下の順番で、前置きなしで「☀️ 季節の移ろい」から開始し、🎼 伝統芸能で終了すること：

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

🎼 伝統芸能

それでは、**必ず2-3文ごとに空行を入れて**、親しみやすく温かい文章で本日の暦情報を詳しく解説してください。"""
        
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 1.0,
                    "topK": 64,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                }
            }
            
            print("Gemini APIにリクエスト送信中...")
            response = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=120
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"APIレスポンス取得成功")
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    
                    if 'content' in candidate and 'parts' in candidate['content']:
                        content = candidate['content']['parts'][0]['text']
                        print(f"生成されたコンテンツ長: {len(content)}文字")
                        print(f"コンテンツプレビュー（最初の200文字）:\n{content[:200]}...")
                        return content
                    else:
                        print("エラー: コンテンツ構造が予期しない形式です")
                        print(f"候補データ: {json.dumps(candidate, ensure_ascii=False, indent=2)}")
                else:
                    print("エラー: 候補が空です")
                    print(f"完全なレスポンス: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                return None
            else:
                print(f"Gemini APIエラー: {response.status_code}")
                print(f"エラー内容: {response.text}")
                return None
                
        except Exception as e:
            print(f"Gemini API呼び出し例外: {str(e)}")
            import traceback
            traceback.print_exc()
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
        sun_times = SunCalculator.calculate_sunrise_sunset(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        # 基本情報セクション（プログラムで生成）
        basic_info = f"""<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">📅 今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 24px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 15px 0 0 0; font-size: 20px;">旧暦: {lunar['month']}月{lunar['day']}日（{lunar['month_name']}）</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">六曜: {lunar['rokuyou']}</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 17px; opacity: 0.95; line-height: 1.7;">{lunar['appearance']}</p>
<p style="margin: 15px 0 0 0; font-size: 18px; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 15px;">
<strong>岡山の日の出・日の入り</strong><br>
日の出: {sun_times['sunrise']} / 日の入り: {sun_times['sunset']}
</p>
</div>

<div style="background: #f7fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #4299e1; margin-bottom: 35px;">
<p style="margin: 0 0 10px 0; font-size: 18px;"><strong>二十四節気:</strong> {sekki[0]}（{sekki[1]}）</p>
<p style="margin: 0; font-size: 18px;"><strong>七十二候:</strong> {kou[0]}（{kou[1]}）</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">
"""
        
        # Geminiでコンテンツ生成
        print("\n" + "="*70)
        print("Gemini APIでコンテンツを生成中...")
        print("="*70)
        
        if not self.gemini_api_key:
            print("エラー: GEMINI_API_KEYが設定されていません")
            gemini_content = None
        else:
            generator = GeminiContentGenerator(self.gemini_api_key)
            gemini_content = generator.generate_content(self.date, lunar, sekki, kou)
        
        if not gemini_content:
            print("\n警告: Geminiコンテンツの生成に失敗しました。")
            print("フォールバックコンテンツを使用します。")
            gemini_content = self._generate_rich_fallback_content(lunar, sekki, kou)
        
        # HTML整形
        print("\nHTML整形処理を開始...")
        gemini_html = self._format_gemini_content_to_html(gemini_content)
        print(f"整形後のHTML長: {len(gemini_html)}文字")
        
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
    
    def _format_gemini_content_to_html(self, content):
        """GeminiコンテンツをHTML形式に整形（Markdown対応版）"""
        if not content:
            return ""
        
        lines = content.split('\n')
        html_parts = []
        current_section = None
        current_content = []
        
        section_config = {
            '☀️': ('#fc8181', '季節の移ろい'),
            '🎌': ('#f6ad55', '記念日・祝日'),
            '💡': ('#4299e1', '暦にまつわる文化雑学'),
            '🚜': ('#68d391', '農事歴'),
            '🏡': ('#9f7aea', '日本の風習・しきたり'),
            '📚': ('#ed64a6', '神話・伝説'),
            '🍁': ('#38b2ac', '自然・気象'),
            '🍴': ('#f56565', '旬の食'),
            '🌸': ('#f687b3', '季節の草木'),
            '🌕': ('#4299e1', '月や星の暦・天文情報'),
            '🎨': ('#ed8936', '伝統工芸'),
            '🎼': ('#805ad5', '伝統芸能')
        }
        
        for line in lines:
            line_stripped = line.strip()
            
            # セクション開始を検出
            is_section_start = False
            for emoji, (color, name) in section_config.items():
                if line_stripped.startswith(emoji):
                    # 前のセクションを保存
                    if current_section and current_content:
                        emoji_key, color_val = current_section
                        section_body = self._convert_markdown_to_html(current_content)
                        html_parts.append(self._create_section_html(
                            line_with_emoji=f"{emoji_key} {section_config[emoji_key][1]}",
                            content=section_body,
                            color=color_val
                        ))
                    
                    # 新しいセクション開始
                    current_section = (emoji, color)
                    current_content = []
                    is_section_start = True
                    break
            
            if not is_section_start and line_stripped:
                current_content.append(line)
        
        # 最後のセクションを保存
        if current_section and current_content:
            emoji_key, color_val = current_section
            section_body = self._convert_markdown_to_html(current_content)
            html_parts.append(self._create_section_html(
                line_with_emoji=f"{emoji_key} {section_config[emoji_key][1]}",
                content=section_body,
                color=color_val
            ))
        
        return ''.join(html_parts)
    
    def _convert_markdown_to_html(self, lines):
        """MarkdownテキストをHTMLに変換"""
        html = []
        in_list = False
        current_paragraph = []
        
        for line in lines:
            stripped = line.strip()
            
            # 箇条書きの処理（* または - で始まる行）
            if stripped.startswith('* ') or stripped.startswith('- '):
                # 段落を閉じる
                if current_paragraph:
                    html.append(f"<p style='margin: 0 0 15px 0; line-height: 2;'>{''.join(current_paragraph)}</p>")
                    current_paragraph = []
                
                # リスト開始
                if not in_list:
                    html.append("<ul style='margin: 15px 0; padding-left: 25px;'>")
                    in_list = True
                
                # リスト項目
                item_text = stripped[2:].strip()  # * または - を除去
                # 太字処理 **text**
                item_text = self._process_bold(item_text)
                html.append(f"<li style='margin-bottom: 12px; line-height: 2;'>{item_text}</li>")
            
            # 空行
            elif not stripped:
                # リストを閉じる
                if in_list:
                    html.append("</ul>")
                    in_list = False
                
                # 段落を閉じる
                if current_paragraph:
                    html.append(f"<p style='margin: 0 0 15px 0; line-height: 2;'>{''.join(current_paragraph)}</p>")
                    current_paragraph = []
            
            # 通常の段落
            else:
                # リストを閉じる
                if in_list:
                    html.append("</ul>")
                    in_list = False
                
                # 段落に追加
                processed_line = self._process_bold(stripped)
                current_paragraph.append(processed_line)
        
        # 最後のリストを閉じる
        if in_list:
            html.append("</ul>")
        
        # 最後の段落を閉じる
        if current_paragraph:
            html.append(f"<p style='margin: 0 0 15px 0; line-height: 2;'>{''.join(current_paragraph)}</p>")
        
        return ''.join(html)
    
    def _process_bold(self, text):
        """太字マークダウン（**text**）をHTMLに変換"""
        import re
        # **text** を <strong>text</strong> に変換
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return text
    
    def _create_section_html(self, line_with_emoji, content, color):
        """セクションのHTMLを生成"""
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin: 35px 0 25px 0; border-left: 6px solid {color}; padding-left: 15px;">{line_with_emoji}</h3>
<div style="background: #f7fafc; padding: 28px; border-radius: 12px; margin-bottom: 30px; border-left: 4px solid {color};">
<div style="color: #2d3748; font-size: 16px;">{content}</div>
</div>
"""
    
    def _generate_rich_fallback_content(self, lunar, sekki, kou):
        """充実したフォールバックコンテンツ"""
        month = self.date.month
        day = self.date.day
        
        return f"""☀️ 季節の移ろい（二十四節気・七十二候）

本日は二十四節気の「{sekki[0]}」（{sekki[1]}）の時期です。二十四節気は、太陽の黄道上の位置によって一年を24等分したもので、古代中国で生まれ、日本の農耕文化に深く根付いてきました。

七十二候では「{kou[0]}」（{kou[1]}）を迎えています。七十二候は二十四節気をさらに細かく、約5日ごとに分けたもので、季節の繊細な移ろいを表現しています。

冬の深まりとともに、自然は静かに春の準備を始めています。寒さの中にも、確かな季節の息吹を感じることができる時期です。

🎌 記念日・祝日

{month}月{day}日は、日本の暦において特別な意味を持つ日々が続く季節です。年末が近づき、一年の締めくくりに向けて様々な行事が行われます。

師走という言葉が示すように、師も走るほど忙しい時期ですが、それは単なる慌ただしさではなく、一年の総決算として大切な営みが重なる時期でもあります。

冬至が近づくと「一陽来復」という言葉が思い起こされます。これは、陰が極まって陽が復活し始めるという意味で、最も暗い時期を過ぎれば、必ず光が戻ってくるという希望を表しています。

💡 暦にまつわる文化雑学

旧暦{lunar['month']}月は「{lunar['month_name']}」と呼ばれます。この呼び名には深い意味が込められており、日本人の季節感や自然観が反映されています。

神無月という名称には、全国の神々が出雲に集まり、各地では神様が不在になるという言い伝えがあります。ただし、出雲地方では逆に「神在月」と呼ばれ、神々を迎える特別な祭事が行われます。

霜月になると、霜が降り始める季節として、冬の到来を実感する時期です。また、新嘗祭（にいなめさい）という重要な宮中祭祀が行われ、その年の収穫を神々に感謝する習わしがあります。

師走は一年の最後の月として、様々な締めくくりの行事が行われます。「師が走る」ほど忙しいという説や、「年が果てる（しはす）」が転じたという説など、語源には諸説あります。

🚜 農事歴

この時期、農村では一年の農作業がほぼ終わり、冬支度が本格化します。稲作地域では、脱穀・籾摺りが終わり、新米の出荷も一段落する頃です。

畑では、大根・白菜・ネギなどの冬野菜が霜に当たって甘みを増し、最も美味しくなる時期を迎えます。特に大根は「寒大根」として珍重され、おでんやふろふき大根に最適です。

伝統的には、この時期は「漬物の仕込み」の季節でもあります。沢庵漬け、白菜漬け、野沢菜漬けなど、冬の保存食として各家庭で漬物づくりが盛んに行われました。

また、農具の手入れや修理、縄綯い（なわない）などの室内作業が中心となり、春の作付け計画を立てる大切な準備期間でもあります。

🏡 日本の風習・しきたり

12月に入ると、一年の締めくくりとして様々な風習が行われます。すす払い（12月13日頃）は、一年の汚れを落とし、新年を清らかに迎えるための大切な行事です。

正月飾りの準備も本格化します。門松、しめ飾り、鏡餅など、それぞれに深い意味が込められた飾りを用意します。これらは単なる装飾ではなく、年神様を迎えるための神聖な道具です。

冬至（12月21日頃）には、柚子湯に入る習慣があります。「冬至」と「湯治」をかけた語呂合わせと、柚子の香りで邪気を払うという意味が込められています。また、南瓜（かぼちゃ）を食べる習慣もあり、「ん」のつく食べ物を食べると運が良くなるという言い伝えがあります。

大晦日には、除夜の鐘が108回鳴らされます。これは人間の煩悩の数を表し、一つ一つの鐘の音で煩悩を払い、清らかな心で新年を迎えるという意味があります。

11月は「霜月」として、七五三（11月15日）や勤労感謝の日（新嘗祭）など、子どもの成長と収穫への感謝を祝う行事が行われます。

🍚 神話・伝説

師走から新年にかけての時期には、様々な神話や伝説が語り継がれています。特に「年神様」の存在は重要で、新年に各家庭を訪れて幸福をもたらすと信じられています。

出雲神話では、神無月（10月）に全国の八百万の神々が出雲大社に集まり、人々の縁結びや来年の豊作について会議を行うとされています。これは『古事記』や『日本書紀』に記される国譲り神話とも深く関連しています。

冬至は「一陽来復」の日として、陰陽思想において重要な転換点とされてきました。最も暗い時期を過ぎれば、必ず光が戻ってくるという思想は、日本人の自然観や人生観に大きな影響を与えています。

また、大晦日から元日にかけての時間は、時間が止まる神聖な瞬間とされ、多くの神社仏閣で特別な儀式が行われます。

🍁 自然・気象

12月は本格的な冬の到来を告げる季節です。朝晩の冷え込みが厳しくなり、霜柱が立つ朝も増えてきます。北国では本格的な降雪が始まり、山々は白銀の世界に包まれます。

太平洋側では、乾燥した晴天が続くことが多く、空気が澄み渡るため、遠くの山々がくっきりと見えます。富士山をはじめとする名峰の雪化粧が美しい季節です。

一方、日本海側では、冬型の気圧配置により雪や曇りの日が多くなります。季節風が日本海を渡る際に水蒸気を含み、山地にぶつかって大量の雪を降らせます。

冬至を過ぎると、わずかずつですが日が長くなり始めます。暗闇の中にも、確かな春への歩みが始まっているのです。

夜空は一年で最も美しい季節を迎えます。冬の大三角形（ベテルギウス、シリウス、プロキオン）やオリオン座が東の空から昇り、澄んだ空気の中で輝きます。

🍴 旬の食

12月は冬の食材が最盛期を迎える季節です。寒さで甘みを増した野菜類が特に美味しくなります。

【野菜】大根、白菜、春菊、ほうれん草、かぶ、長ねぎ、里芋、ゆず、れんこん

特に大根は「寒大根」として最高の味わいとなり、ふろふき大根、おでん、ぶり大根など、様々な料理で楽しめます。

【果物】みかん、りんご、柚子、金柑

みかんはこたつのお供として冬の風物詩です。柚子は冬至の柚子湯だけでなく、料理の香りづけにも欠かせません。

【魚介】ブリ、カキ（牡蠣）、サバ、鱈、ふぐ、あんこう

特にブリは「寒ブリ」として脂がのり、刺身や照り焼きで絶品です。牡蠣は「海のミルク」と呼ばれ、栄養豊富で鍋料理に最適です。

【行事食】冬至には南瓜（かぼちゃ）を食べる習慣があり、年越しそばで一年を締めくくります。また、クリスマスのごちそうも現代の風物詩となっています。

11月は「新米」の季節でもあり、秋の収穫を祝う「芋煮」「けんちん汁」などの郷土料理が各地で親しまれます。

🌸 季節の草木

冬の草木は、厳しい寒さに耐えながらも、凛とした美しさを見せてくれます。

【代表的な花】
・水仙（すいせん）：清楚な白い花と芳香が特徴。霜に負けず咲く姿は冬の庭を彩ります。花言葉は「自己愛」「神秘」
・山茶花（さざんか）：冬の訪れを告げる花。椿に似ていますが、花びらが散る様子が異なります。花言葉は「困難に打ち勝つ」「ひたむきさ」
・千両（せんりょう）：赤い実をつける縁起物。正月飾りとして親しまれています。花言葉は「商売繁盛」「裕福」
・南天（なんてん）：「難を転ずる」という語呂合わせから厄除けの木とされます
・梅（うめ）：早いものは12月下旬から咲き始め、春の訪れを告げます

【冬木立】葉を落とした木々の枝ぶりは、墨絵のような趣があり、日本庭園の冬景色を美しく演出します。

🌕 月や星の暦・天文情報

本日の月齢は{lunar['age']}で、{lunar['phase']}です。{lunar['appearance']}

冬の夜空は一年で最も美しい季節を迎えています。空気が澄んでいるため、星々が輝きを増し、天の川もくっきりと見えることがあります。

【冬の星座】
・オリオン座：冬の星座の王様。三つ星が目印で、ベテルギウス（赤色）とリゲル（青白色）という対照的な一等星を持ちます
・冬の大三角：オリオン座のベテルギウス、おおいぬ座のシリウス、こいぬ座のプロキオンで形成される大きな三角形
・おうし座：プレアデス星団（すばる）が美しい。日本では古くから「六連星（むつらぼし）」として親しまれています
・ぎょしゃ座：一等星カペラを含む五角形の星座

冬至の頃は、一年で最も昼が短く夜が長い時期です。しかし、これを過ぎると少しずつ日が長くなり、春への希望を感じることができます。

🎨 伝統工芸

冬の農閑期は、伝統工芸の制作が盛んになる季節です。

【藁細工】稲わらを使った工芸で、しめ縄、わらぐつ、縄飾りなど、実用性と美しさを兼ね備えた作品が作られます。特に正月飾りのしめ縄は、神聖な場所を示す大切な飾りです。

【干し柿づくり】軒先に吊るされた柿は、冬の農村風景を彩る風物詩。天然の甘味料として重宝され、正月の縁起物としても用いられます。

【曲げわっぱ】秋田県の伝統工芸。薄く削った杉材を曲げて作る弁当箱は、木の香りと調湿性に優れ、ご飯を美味しく保ちます。新米の季節に合わせて需要も高まります。

【正月飾り作り】門松、しめ飾り、鏡餅など、新年を迎えるための飾りを手作りする伝統が各地に残っています。これらは単なる装飾ではなく、年神様を迎えるための神聖な準備です。

【雪国の工芸】雪深い地域では、冬の間に様々な工芸品が作られます。竹細工、木彫り、織物など、長い冬を有意義に過ごすための知恵が詰まっています。

🎼 伝統芸能

冬は伝統芸能の公演が活発になる季節です。

【歌舞伎】12月は「顔見世興行」が行われる重要な時期です。特に「仮名手本忠臣蔵」は冬の名作として、毎年この時期に上演されます。討ち入りの季節に合わせた演目として、江戸時代から人々に愛されてきました。

【能楽】冬にふさわしい演目として、「小鍛冶」「羽衣」などが演じられます。また、年末年始には「翁」という特別な儀式的演目が奉納され、新年の平安を祈ります。

【神楽】各地の神社で冬の祭礼に合わせて神楽が奉納されます。特に出雲地方では、神在祭に合わせて壮大な神楽が演じられ、神話の世界を今に伝えています。

【雅楽】宮中や大きな神社では、年末年始の儀式に雅楽が演奏されます。千年以上の歴史を持つ音楽は、厳かな雰囲気の中で響き渡ります。

【民俗芸能】各地に伝わる獅子舞、田楽、盆踊りなどの民俗芸能も、冬の祭りで披露されます。これらは五穀豊穣や無病息災を祈る、庶民の芸能です。"""


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
            
            print(f"\n✅ 投稿成功: {response.get('url')}")
            return response
            
        except Exception as e:
            print(f"\n❌ 投稿エラー: {str(e)}")
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
        print("🌸 暦情報自動投稿システム Gemini 2.5 Flash統合版 起動")
        print("=" * 70)
        print(f"📅 投稿日時: {datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')}")
        
        # 暦情報生成
        print("\n🔄 今日の暦情報を生成中...")
        print("  - 正確な天文計算による二十四節気・七十二候")
        print("  - Gemini 2.5 Flash AIによる豊かな文章生成")
        print("  - 12セクション完全対応")
        
        generator = CalendarPostGenerator()
        post_data = generator.generate_post()
        
        print(f"\n📝 タイトル: {post_data['title']}")
        print(f"📊 推定文字数: 約{len(post_data['content'])}文字")
        print(f"🏷️  ラベル: {', '.join(post_data['labels'])}")
        
        # Blogger投稿
        print("\n📤 Bloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 70)
        print("✨ すべての処理が完了しました！")
        print("📚 正確な暦情報とGemini生成の豊かな文章が投稿されました")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
