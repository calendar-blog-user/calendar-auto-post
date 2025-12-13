#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini完全生成版（修正版）
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
import time

SCOPES = ['https://www.googleapis.com/auth/blogger']

class AstronomicalCalculator:
    """正確な天文計算"""
    
    @staticmethod
    def calculate_solar_longitude(dt):
        """太陽黄経を精密計算"""
        jst = ZoneInfo("Asia/Tokyo")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=jst)
        
        y, m, d = dt.year, dt.month, dt.day
        h = dt.hour + dt.minute/60.0 + dt.second/3600.0
        
        if m <= 2:
            y -= 1
            m += 12
        
        a = int(y / 100)
        b = 2 - a + int(a / 4)
        jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + h/24.0 + b - 1524.5
        
        t = (jd - 2451545.0) / 36525.0
        
        l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
        l0 = l0 % 360
        
        m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
        m_rad = math.radians(m)
        
        e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t
        
        c = (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m_rad)
        c += (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
        c += 0.000289 * math.sin(3 * m_rad)
        
        true_longitude = (l0 + c) % 360
        
        return true_longitude
    
    @classmethod
    def get_current_sekki(cls, dt):
        """現在の二十四節気"""
        sekki_data = [
            (315, "立春", "りっしゅん"),
            (330, "雨水", "うすい"),
            (345, "啓蟄", "けいちつ"),
            (0, "春分", "しゅんぶん"),
            (15, "清明", "せいめい"),
            (30, "穀雨", "こくう"),
            (45, "立夏", "りっか"),
            (60, "小満", "しょうまん"),
            (75, "芒種", "ぼうしゅ"),
            (90, "夏至", "げし"),
            (105, "小暑", "しょうしょ"),
            (120, "大暑", "たいしょ"),
            (135, "立秋", "りっしゅう"),
            (150, "処暑", "しょしょ"),
            (165, "白露", "はくろ"),
            (180, "秋分", "しゅうぶん"),
            (195, "寒露", "かんろ"),
            (210, "霜降", "そうこう"),
            (225, "立冬", "りっとう"),
            (240, "小雪", "しょうせつ"),
            (255, "大雪", "たいせつ"),
            (270, "冬至", "とうじ"),
            (285, "小寒", "しょうかん"),
            (300, "大寒", "だいかん")
        ]
        
        longitude = cls.calculate_solar_longitude(dt)
        
        for i, (deg, name, reading) in enumerate(sekki_data):
            next_deg = sekki_data[(i + 1) % len(sekki_data)][0]
            
            if deg <= next_deg:
                if deg <= longitude < next_deg:
                    return (name, reading)
            else:
                if longitude >= deg or longitude < next_deg:
                    return (name, reading)
        
        return sekki_data[0][1:]
    
    @classmethod
    def get_current_kou(cls, dt):
        """現在の七十二候"""
        month, day = dt.month, dt.day
        
        kou_data = [
            (2, 4, "東風解凍", "はるかぜこおりをとく"),
            (2, 9, "黄鶯睍睆", "うぐいすなく"),
            (2, 14, "魚上氷", "うおこおりをいずる"),
            (2, 19, "土脉潤起", "つちのしょううるおいおこる"),
            (2, 24, "霞始靆", "かすみはじめてたなびく"),
            (3, 1, "草木萌動", "そうもくめばえいずる"),
            (3, 6, "蟄虫啓戸", "すごもりむしとをひらく"),
            (3, 11, "桃始笑", "ももはじめてさく"),
            (3, 16, "菜虫化蝶", "なむしちょうとなる"),
            (3, 21, "雀始巣", "すずめはじめてすくう"),
            (3, 26, "櫻始開", "さくらはじめてひらく"),
            (3, 31, "雷乃発声", "かみなりすなわちこえをはっす"),
            (4, 5, "玄鳥至", "つばめきたる"),
            (4, 10, "鴻雁北", "こうがんかえる"),
            (4, 15, "虹始見", "にじはじめてあらわる"),
            (4, 20, "葭始生", "あしはじめてしょうず"),
            (4, 25, "霜止出苗", "しもやんでなえいず"),
            (4, 30, "牡丹華", "ぼたんはなさく"),
            (5, 5, "蛙始鳴", "かわずはじめてなく"),
            (5, 10, "蚯蚓出", "みみずいずる"),
            (5, 15, "竹笋生", "たけのこしょうず"),
            (5, 21, "蚕起食桑", "かいこおきてくわをはむ"),
            (5, 26, "紅花栄", "べにばなさかう"),
            (5, 31, "麦秋至", "むぎのときいたる"),
            (6, 6, "蟷螂生", "かまきりしょうず"),
            (6, 11, "腐草為螢", "くされたるくさほたるとなる"),
            (6, 16, "梅子黄", "うめのみきばむ"),
            (6, 21, "乃東枯", "なつかれくさかるる"),
            (6, 26, "菖蒲華", "あやめはなさく"),
            (7, 2, "半夏生", "はんげしょうず"),
            (7, 7, "温風至", "あつかぜいたる"),
            (7, 12, "蓮始開", "はすはじめてひらく"),
            (7, 17, "鷹乃学習", "たかすなわちわざをならう"),
            (7, 23, "桐始結花", "きりはじめてはなをむすぶ"),
            (7, 28, "土潤溽暑", "つちうるおうてむしあつし"),
            (8, 2, "大雨時行", "たいうときどきふる"),
            (8, 7, "涼風至", "すずかぜいたる"),
            (8, 13, "寒蝉鳴", "ひぐらしなく"),
            (8, 18, "蒙霧升降", "ふかききりまとう"),
            (8, 23, "綿柎開", "わたのはなしべひらく"),
            (8, 28, "天地始粛", "てんちはじめてさむし"),
            (9, 2, "禾乃登", "こくものすなわちみのる"),
            (9, 7, "草露白", "くさのつゆしろし"),
            (9, 12, "鶺鴒鳴", "せきれいなく"),
            (9, 17, "玄鳥去", "つばめさる"),
            (9, 23, "雷乃収声", "かみなりすなわちこえをおさむ"),
            (9, 28, "蟄虫坏戸", "むしかくれてとをふさぐ"),
            (10, 3, "水始涸", "みずはじめてかるる"),
            (10, 8, "鴻雁来", "こうがんきたる"),
            (10, 13, "菊花開", "きくのはなひらく"),
            (10, 18, "蟋蟀在戸", "きりぎりすとにあり"),
            (10, 23, "霜始降", "しもはじめてふる"),
            (10, 28, "霎時施", "こさめときどきふる"),
            (11, 2, "楓蔦黄", "もみじつたきばむ"),
            (11, 7, "山茶始開", "つばきはじめてひらく"),
            (11, 12, "地始凍", "ちはじめてこおる"),
            (11, 17, "金盞香", "きんせんかさく"),
            (11, 22, "虹蔵不見", "にじかくれてみえず"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう"),
            (12, 2, "橘始黄", "たちばなはじめてきばむ"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる"),
            (12, 12, "熊蟄穴", "くまあなにこもる"),
            (12, 17, "鱖魚群", "さけのうおむらがる"),
            (12, 22, "乃東生", "なつかれくさしょうず"),
            (12, 27, "麋角解", "さわしかつのおつる"),
            (1, 1, "雪下出麦", "ゆきわたりてむぎのびる"),
            (1, 5, "芹乃栄", "せりすなわちさかう"),
            (1, 10, "水泉動", "しみずあたたかをふくむ"),
            (1, 15, "雉始雊", "きじはじめてなく"),
            (1, 20, "款冬華", "ふきのはなさく"),
            (1, 25, "水沢腹堅", "さわみずこおりつめる"),
            (1, 30, "鶏始乳", "にわとりはじめてとやにつく")
        ]
        
        current_kou = kou_data[0][2:]
        for m, d, name, reading in reversed(kou_data):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading)
                break
        
        return current_kou


class LunarCalendar:
    """旧暦計算"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """旧暦計算"""
        reference = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        reference_lunar = {'year': 2025, 'month': 10, 'day': 21, 'age': 19.8}
        
        synodic = 29.530588861
        elapsed_days = (date - reference).total_seconds() / 86400
        
        moon_age = (reference_lunar['age'] + elapsed_days) % synodic
        if moon_age < 0:
            moon_age += synodic
        
        elapsed_months = int((reference_lunar['age'] + elapsed_days) / synodic)
        
        lunar_year = reference_lunar['year']
        lunar_month = reference_lunar['month']
        lunar_day = reference_lunar['day']
        
        for _ in range(abs(elapsed_months)):
            if elapsed_months > 0:
                lunar_month += 1
                if lunar_month > 12:
                    lunar_month = 1
                    lunar_year += 1
            else:
                lunar_month -= 1
                if lunar_month < 1:
                    lunar_month = 12
                    lunar_year -= 1
        
        days_in_month = elapsed_days - (elapsed_months * synodic)
        lunar_day = reference_lunar['day'] + int(days_in_month)
        
        while lunar_day > 30:
            lunar_day -= 30
            lunar_month += 1
            if lunar_month > 12:
                lunar_month = 1
                lunar_year += 1
        
        while lunar_day < 1:
            lunar_day += 30
            lunar_month -= 1
            if lunar_month < 1:
                lunar_month = 12
                lunar_year -= 1
        
        # 月相判定
        if moon_age < 1.5:
            phase, appearance = "新月", "夜空に月は見えません"
        elif moon_age < 3.7:
            phase, appearance = "二日月", "夕方の西空に細い月が輝きます"
        elif moon_age < 7.4:
            phase, appearance = "上弦へ向かう月", "夕方の空に弓なりの月"
        elif 7.4 <= moon_age < 11:
            phase, appearance = "上弦の月", "宵の空に半月が見えます"
        elif moon_age < 14.8:
            phase, appearance = "満月へ向かう月", "宵から夜半にかけて膨らむ月"
        elif 14.8 <= moon_age < 16.3:
            phase, appearance = "満月", "夜通し輝く丸い月"
        elif moon_age < 22.1:
            phase, appearance = "下弦へ向かう月（寝待月）", "夜が更けてから昇る月"
        elif 22.1 <= moon_age < 25.9:
            phase, appearance = "下弦の月", "明け方に半月が見えます"
        else:
            phase, appearance = "晦日月", "明け方の東空に細い月"
        
        # 六曜計算
        rokuyou_list = ["先勝", "友引", "先負", "仏滅", "大安", "赤口"]
        rokuyou_index = (lunar_month + lunar_day) % 6
        rokuyou = rokuyou_list[rokuyou_index]
        
        # 干支計算
        eto_list = ["甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉",
                    "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未",
                    "甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳",
                    "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
                    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑",
                    "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥"]
        
        base_date = datetime(2000, 1, 1, tzinfo=ZoneInfo("Asia/Tokyo"))
        days_diff = (date.replace(hour=0, minute=0, second=0, microsecond=0) - base_date).days
        eto_index = (days_diff + 36) % 60
        eto = eto_list[eto_index]
        
        return {
            'year': lunar_year,
            'month': lunar_month,
            'day': lunar_day,
            'age': round(moon_age, 1),
            'phase': phase,
            'appearance': appearance,
            'rokuyou': rokuyou,
            'eto': eto
        }
    
    @staticmethod
    def get_lunar_month_name(month):
        """旧暦月の異名"""
        names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
            7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        return names.get(month, "")


class GeminiContentGenerator:
    """Gemini APIで全コンテンツを生成"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        # 正しいモデル名を使用
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    
    def generate_all_content(self, date, lunar, sekki, kou):
        """Geminiで全セクションを生成"""
        if not self.api_key:
            print("  ✗ GEMINI_API_KEYが設定されていません")
            raise Exception("GEMINI_API_KEYが必要です")
        
        lunar_month_name = LunarCalendar.get_lunar_month_name(lunar['month'])
        
        prompt = f"""本日の暦情報にもとづいて、以下の指示に従って自然・歴史・信仰・暮らしの視点から文化的背景とともに網羅的に詳しく、豊かで情緒的な表現で解説してください。
文章は適度に改行してください。

【本日の暦情報】
日付: {date.year}年{date.month}月{date.day}日
旧暦: {lunar_month_name}（{lunar['day']}日）
月齢: {lunar['age']}（{lunar['phase']}）
二十四節気: {sekki[0]}（{sekki[1]}）
七十二候: {kou[0]}（{kou[1]}）
干支: {lunar['eto']}
六曜: {lunar['rokuyou']}

🎭 1. 役割（ペルソナ）の指定
あなたは暦・季節・日本文化に深く通じた案内人。単なる日付情報ではなく、「暮らし・信仰・文化・自然のつながり」を語る存在として、日本の四季・自然観・農耕文化を大切に解説してください。

📅 2. 必ず次のような章立てで出力
回答は前置きを一切付けず、「☀️ 季節の移ろい」から開始し、🎼 伝統芸能の内容まで出力し、それ以降は一切書かないこと。章立ては以下の通りとし、表形式は絶対に使用しないで、箇条書きで網羅的に詳しく、豊かで情緒的な表現で解説してください。

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
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 8000
                }
            }
            
            print("  Gemini APIにリクエスト送信中...")
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            print(f"  レスポンスステータス: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # デバッグ: レスポンス構造を確認
                print(f"  レスポンスキー: {result.keys()}")
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    print(f"  ✓ Geminiコンテンツ生成完了（{len(content)}文字）")
                    return content
                else:
                    print(f"  ✗ レスポンス形式が不正: {result}")
                    raise Exception("Geminiレスポンスに候補がありません")
            else:
                error_text = response.text
                print(f"  ✗ Gemini APIエラー: {response.status_code}")
                print(f"  エラー詳細: {error_text}")
                raise Exception(f"Gemini API エラー: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("  ✗ Gemini APIタイムアウト")
            raise Exception("Gemini APIがタイムアウトしました")
        except Exception as e:
            print(f"  ✗ Geminiエラー: {str(e)}")
            raise


class CalendarPostGenerator:
    """暦情報投稿生成"""
    
    def __init__(self, target_date=None, gemini_api_key=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.gemini_key = gemini_api_key
    
    def generate_post(self):
        """投稿内容生成"""
        # 暦情報計算
        print("暦情報を計算中...")
        lunar = LunarCalendar.calculate_lunar_date(self.date)
        sekki = AstronomicalCalculator.get_current_sekki(self.date)
        kou = AstronomicalCalculator.get_current_kou(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        lunar_month_name = LunarCalendar.get_lunar_month_name(lunar['month'])
        
        # 季節の言葉
        seasonal_words = f"{lunar_month_name}・歳末・{sekki[0]}"
        
        # Geminiでコンテンツ生成
        print("\nGeminiでコンテンツ生成中...")
        gemini_generator = GeminiContentGenerator(self.gemini_key)
        gemini_content = gemini_generator.generate_all_content(self.date, lunar, sekki, kou)
        
        # HTML生成
        html = f"""
<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">📅 今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 22px; font-weight: bold;">西暦：{self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 12px 0 0 0; font-size: 19px;">旧暦：{lunar_month_name}（{lunar['day']}日）</p>
<p style="margin: 10px 0 0 0; font-size: 18px;">月齢：{lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 18px;">干支：{lunar['eto']}</p>
<p style="margin: 10px 0 0 0; font-size: 18px;">六曜：{lunar['rokuyou']}</p>
<p style="margin: 10px 0 0 0; font-size: 17px;">季節の言葉：{seasonal_words}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<div style="line-height: 2; font-size: 16px; white-space: pre-line;">
{gemini_content}
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
<p style="margin: 0; font-size: 18px; color: #14532d; font-weight: 500; line-height: 2;">
季節の移ろいを感じながら、心穏やかな一日をお過ごしください
</p>
</div>

</div>
"""
        
        return {
            'title': f'{self.date.year}年{self.date.month}月{self.date.day}日({weekday})の暦 - {sekki[0]}・{lunar_month_name}',
            'content': html,
            'labels': ['暦', '二十四節気', '七十二候', '旧暦', '季節', '伝統', '行事', '自然', '月齢', '干支']
        }


class BloggerPoster:
    """Blogger投稿クラス"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
    
    def authenticate(self):
        """Google API認証"""
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
            
            print(f"\n✓ 投稿成功: {response.get('url')}")
            return response
        except Exception as e:
            print(f"\n✗ 投稿エラー: {str(e)}")
            raise


def main():
    """メイン処理"""
    try:
        blog_id = os.environ.get('BLOG_ID')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        if not gemini_key:
            raise Exception("GEMINI_API_KEY環境変数が設定されていません")
        
        print("=" * 70)
        print("暦情報自動投稿システム - Gemini完全生成版")
        print("=" * 70)
        jst = ZoneInfo('Asia/Tokyo')
        now = datetime.now(jst)
        print(f"実行日時: {now.strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"Gemini API Key: {gemini_key[:20]}...{gemini_key[-4:]}")
        
        print("\n" + "=" * 70)
        
        # 暦情報生成
        generator = CalendarPostGenerator(target_date=now, gemini_api_key=gemini_key)
        post_data = generator.generate_post()
        
        print(f"\n✓ タイトル: {post_data['title']}")
        print(f"✓ コンテンツサイズ: {len(post_data['content'])} 文字")
        print(f"✓ ラベル: {', '.join(post_data['labels'])}")
        
        # Blogger投稿
        print("\nBloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 70)
        print("✓ すべての処理が完了しました")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
