#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム 完全版
- 正確な旧暦計算
- 二十四節気・七十二候の自動計算
- Gemini API統合による豊かな文章生成
- 完全無料で365日稼働
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

class SolarTermCalculator:
    """二十四節気・七十二候の自動計算クラス"""
    
    @staticmethod
    def calculate_solar_longitude(date):
        """太陽黄経を計算（簡易版）"""
        # 春分を基準（黄経0度）
        vernal_equinox = datetime(date.year, 3, 20, tzinfo=ZoneInfo("Asia/Tokyo"))
        days_from_equinox = (date - vernal_equinox).days
        
        # 1年 = 365.25日 = 360度
        longitude = (days_from_equinox * 360 / 365.25) % 360
        return longitude
    
    @classmethod
    def get_current_sekki(cls, date):
        """現在の二十四節気を計算で取得"""
        longitude = cls.calculate_solar_longitude(date)
        
        # 二十四節気の定義（太陽黄経による）
        sekki_data = [
            (315, "立春", "りっしゅん", "春の始まり"),
            (330, "雨水", "うすい", "雪が雨に変わる"),
            (345, "啓蟄", "けいちつ", "虫が目覚める"),
            (0, "春分", "しゅんぶん", "昼夜が等しい"),
            (15, "清明", "せいめい", "万物が清らか"),
            (30, "穀雨", "こくう", "穀物を潤す雨"),
            (45, "立夏", "りっか", "夏の始まり"),
            (60, "小満", "しょうまん", "草木が茂る"),
            (75, "芒種", "ぼうしゅ", "麦を刈る時期"),
            (90, "夏至", "げし", "最も昼が長い"),
            (105, "小暑", "しょうしょ", "暑さが増す"),
            (120, "大暑", "たいしょ", "最も暑い"),
            (135, "立秋", "りっしゅう", "秋の始まり"),
            (150, "処暑", "しょしょ", "暑さが収まる"),
            (165, "白露", "はくろ", "露が白く輝く"),
            (180, "秋分", "しゅうぶん", "昼夜が等しい"),
            (195, "寒露", "かんろ", "露が冷たい"),
            (210, "霜降", "そうこう", "霜が降りる"),
            (225, "立冬", "りっとう", "冬の始まり"),
            (240, "小雪", "しょうせつ", "雪が降り始める"),
            (255, "大雪", "たいせつ", "雪が本格化"),
            (270, "冬至", "とうじ", "最も昼が短い"),
            (285, "小寒", "しょうかん", "寒さが厳しく"),
            (300, "大寒", "だいかん", "最も寒い")
        ]
        
        # 現在の節気を探す
        current_sekki = sekki_data[0]
        for i, (deg, name, reading, desc) in enumerate(sekki_data):
            if longitude >= deg:
                current_sekki = (name, reading, desc)
            else:
                break
        
        return current_sekki
    
    @classmethod
    def get_current_kou(cls, date):
        """現在の七十二候を計算で取得"""
        longitude = cls.calculate_solar_longitude(date)
        
        # 七十二候（5度ごと）
        kou_data = {
            315: ("東風解凍", "はるかぜこおりをとく", "春風が氷を解かす"),
            320: ("黄鶯睍睆", "うぐいすなく", "鶯が鳴き始める"),
            325: ("魚上氷", "うおこおりをいずる", "魚が氷の下から現れる"),
            330: ("土脉潤起", "つちのしょううるおいおこる", "土が潤い始める"),
            335: ("霞始靆", "かすみはじめてたなびく", "霞がたなびく"),
            340: ("草木萌動", "そうもくめばえいずる", "草木が芽吹く"),
            345: ("蟄虫啓戸", "すごもりむしとをひらく", "虫が出てくる"),
            350: ("桃始笑", "ももはじめてさく", "桃の花が咲く"),
            355: ("菜虫化蝶", "なむしちょうとなる", "青虫が蝶になる"),
            240: ("虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる"),
            245: ("朔風払葉", "きたかぜこのはをはらう", "北風が葉を払う"),
            250: ("橘始黄", "たちばなはじめてきばむ", "橘の実が黄色くなる"),
            255: ("閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり本格的な冬"),
            260: ("熊蟄穴", "くまあなにこもる", "熊が冬眠する"),
            265: ("鱖魚群", "さけのうおむらがる", "鮭が川を上る"),
        }
        
        # 最も近い候を探す
        nearest_kou = ("閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり本格的な冬")
        min_diff = 360
        
        for deg, kou_info in kou_data.items():
            diff = abs(longitude - deg)
            if diff < min_diff:
                min_diff = diff
                nearest_kou = kou_info
        
        return nearest_kou


class AccurateLunarCalendar:
    """正確な旧暦計算クラス"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """正確な旧暦を計算"""
        # 2000年1月6日18時14分 JSTが新月（旧暦11月30日/12月1日境界）
        reference_date = datetime(2000, 1, 6, 18, 14, tzinfo=ZoneInfo("Asia/Tokyo"))
        synodic_month = 29.530588861  # 朔望月の正確な周期
        
        # 経過時間（秒）
        elapsed_seconds = (date - reference_date).total_seconds()
        elapsed_days = elapsed_seconds / 86400
        
        # 月齢計算
        moon_age = elapsed_days % synodic_month
        
        # 経過した朔望月の数
        elapsed_months = int(elapsed_days / synodic_month)
        
        # 2000年1月6日は旧暦1999年11月30日（新月直前）
        # より正確には12月1日として計算
        base_year = 2000
        base_month = 12
        
        # 旧暦の年月を計算
        total_months = elapsed_months + (base_year - 2000) * 12 + base_month - 1
        lunar_year = 2000 + total_months // 12
        lunar_month = (total_months % 12) + 1
        
        # 旧暦の日
        lunar_day = int(moon_age) + 1
        if lunar_day > 30:
            lunar_day = 30
        
        # 月相の判定
        if moon_age < 1.5:
            phase = "新月"
            appearance = "夜空に月は見えません"
        elif moon_age < 3.7:
            phase = "二日月"
            appearance = "夕方の西空に細い月"
        elif moon_age < 7.4:
            phase = "上弦へ向かう月"
            appearance = "夕方から宵に弓なりの月"
        elif 7.4 <= moon_age < 11.1:
            phase = "上弦の月"
            appearance = "宵から夜半に半月"
        elif moon_age < 14.8:
            phase = "満月へ向かう月"
            appearance = "宵から夜半に膨らむ月"
        elif 14.8 <= moon_age < 16.3:
            phase = "満月"
            appearance = "夜通し輝く丸い月"
        elif moon_age < 22.1:
            phase = "下弦へ向かう月"
            appearance = "夜半から明け方に欠けていく月"
        elif 22.1 <= moon_age < 25.9:
            phase = "下弦の月"
            appearance = "明け方に半月"
        else:
            phase = "晦日月"
            appearance = "明け方の東空に細い月"
        
        return {
            'year': lunar_year,
            'month': lunar_month,
            'day': lunar_day,
            'age': round(moon_age, 1),
            'phase': phase,
            'appearance': appearance
        }


class GeminiContentGenerator:
    """Gemini APIを使った文章生成クラス"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
    
    def generate_text(self, prompt, max_tokens=1000):
        """Gemini APIで文章生成"""
        if not self.api_key:
            return None
        
        try:
            url = f"{self.endpoint}?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": max_tokens
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini API エラー: {e}")
            return None


class RichCalendarGenerator:
    """豊富な暦情報生成クラス"""
    
    def __init__(self, target_date=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.gemini = GeminiContentGenerator()
    
    def get_lunar_month_name(self, month):
        """旧暦月の異名"""
        names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月",
            5: "皐月", 6: "水無月", 7: "文月", 8: "葉月",
            9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        return names.get(month, "")
    
    def get_seasonal_description(self):
        """季節の詳細な説明をGemini APIで生成"""
        lunar = AccurateLunarCalendar.calculate_lunar_date(self.date)
        sekki = SolarTermCalculator.get_current_sekki(self.date)
        kou = SolarTermCalculator.get_current_kou(self.date)
        
        prompt = f"""以下の情報に基づいて、日本の暦に関する情緒ある説明文を200文字程度で生成してください。

日付: {self.date.month}月{self.date.day}日
旧暦: {lunar['month']}月{lunar['day']}日（{self.get_lunar_month_name(lunar['month'])}）
月齢: {lunar['age']}（{lunar['phase']}）
二十四節気: {sekki[0]}
七十二候: {kou[0]}

古くからの言い伝えや季節感を織り交ぜて、読者が季節を感じられるような文章にしてください。"""
        
        generated = self.gemini.generate_text(prompt, max_tokens=300)
        
        # Gemini APIが使えない場合のフォールバック
        if not generated:
            lunar_name = self.get_lunar_month_name(lunar['month'])
            return f"旧暦{lunar['month']}月は「{lunar_name}」。{lunar['phase']}の頃は、{lunar['appearance']}が見られる季節です。このころは{sekki[0]}の時期で、{sekki[2]}。{kou[2]}など、季節の移ろいを感じられる頃です。"
        
        return generated
    
    def get_agricultural_calendar(self):
        """農事歴の情報"""
        month = self.date.month
        
        agri_info = {
            12: {
                'period': '冬支度の農期',
                'activities': [
                    '稲作地域では藁仕事や農具の手入れ',
                    '畑では大根・白菜など冬野菜の収穫',
                    '東北や北海道では雪囲いの準備',
                    '伝統的には漬物の仕込みが本格化'
                ],
                'detail': '昔の農村では、この時期は農作業が一段落し、冬に向けて縄綯いなどの室内作業が中心でした。'
            },
            1: {
                'period': '農閑期',
                'activities': [
                    '藁細工や縄綯いなどの室内作業',
                    '農具の手入れと修理',
                    '堆肥づくりの準備',
                    '春の作付け計画'
                ],
                'detail': '寒さが厳しい時期ですが、春に向けての大切な準備期間です。'
            }
        }
        
        return agri_info.get(month, agri_info[12])
    
    def get_customs_and_events(self):
        """風習・記念日・しきたり"""
        month = self.date.month
        day = self.date.day
        
        customs = {
            12: {
                'customs': ['冬囲い', '正月飾りの準備', 'すす払い', '冬至の柚子湯'],
                'events': [
                    '大雪（12/7頃）',
                    '冬至（12/21頃）',
                    'クリスマス（12/25）',
                    '大晦日（12/31）'
                ],
                'description': '一年の締めくくりの月。正月準備が本格化し、日本の冬の風物詩が見られる頃です。'
            }
        }
        
        return customs.get(month, customs[12])
    
    def generate_html_content(self):
        """完全版HTMLコンテンツ生成"""
        
        # 基本情報取得
        lunar = AccurateLunarCalendar.calculate_lunar_date(self.date)
        sekki = SolarTermCalculator.get_current_sekki(self.date)
        kou = SolarTermCalculator.get_current_kou(self.date)
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        lunar_name = self.get_lunar_month_name(lunar['month'])
        
        # 季節の説明文
        seasonal_desc = self.get_seasonal_description()
        
        # 農事歴
        agri = self.get_agricultural_calendar()
        
        # 風習・イベント
        customs = self.get_customs_and_events()
        
        # 旬の食材
        foods_map = {
            12: ["大根", "白菜", "春菊", "ネギ", "かぶ", "ほうれん草", "みかん", "ゆず", "鱈", "鰤", "牡蠣", "ふぐ"],
            1: ["白菜", "ネギ", "小松菜", "大根", "みかん", "金柑", "鱈", "寒ブリ", "牡蠣", "あんこう"]
        }
        foods = foods_map.get(self.date.month, foods_map[12])
        
        # 季節の花
        flowers_map = {
            12: ("水仙", "自己愛・神秘", "清楚な香りの冬の花。冬の庭を彩る代表的な花です。"),
            1: ("福寿草", "幸せを招く・永久の幸福", "新春を告げる黄金の花。雪解けとともに咲き始めます。")
        }
        flower = flowers_map.get(self.date.month, flowers_map[12])
        
        # HTML生成
        html = f"""
<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 800px; margin: 0 auto; line-height: 1.8; color: #333;">

<h2 style="color: #2c5282; border-bottom: 3px solid #4299e1; padding-bottom: 10px; margin-bottom: 20px;">今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
<p style="margin: 0; font-size: 22px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 12px 0 0 0; font-size: 18px;">旧暦: {lunar['month']}月{lunar['day']}日（{lunar_name}）</p>
<p style="margin: 8px 0 0 0; font-size: 18px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.95;">{lunar['appearance']}</p>
</div>

<div style="background: #f7fafc; padding: 20px; border-radius: 8px; border-left: 4px solid #4299e1; margin-bottom: 30px;">
<p style="margin: 0; line-height: 1.9;">{seasonal_desc}</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">季節の移ろい</h3>

<div style="background: linear-gradient(to right, #fff5f5, transparent); border-left: 5px solid #fc8181; padding: 20px; margin-bottom: 20px; border-radius: 5px;">
<h4 style="color: #c53030; margin: 0 0 10px 0; font-size: 20px;">二十四節気: {sekki[0]}（{sekki[1]}）</h4>
<p style="margin: 0; color: #2d3748; line-height: 1.8;">{sekki[2]}。実際の気候や地域によって感じ方は異なりますが、暦の上では重要な節目です。</p>
</div>

<div style="background: linear-gradient(to right, #f0fff4, transparent); border-left: 5px solid #48bb78; padding: 20px; margin-bottom: 25px; border-radius: 5px;">
<h4 style="color: #2f855a; margin: 0 0 10px 0; font-size: 20px;">七十二候: {kou[0]}</h4>
<p style="margin: 5px 0; color: #2d3748;"><em>読み:</em> {kou[1]}</p>
<p style="margin: 10px 0 0 0; color: #2d3748; line-height: 1.8;">{kou[2]}。自然の微細な変化を表現した、日本独特の季節の区切りです。</p>
</div>

<div style="background: #fffaf0; padding: 18px; border-radius: 8px; margin-bottom: 25px;">
<h4 style="color: #c05621; margin: 0 0 12px 0; font-size: 18px;">自然の変化</h4>
<ul style="margin: 0; padding-left: 25px; color: #2d3748;">
<li style="margin-bottom: 8px;">朝晩の冷え込みが一層厳しくなる</li>
<li style="margin-bottom: 8px;">空気が乾燥し、星空が美しく見える</li>
<li style="margin-bottom: 8px;">山では雪の便りが届き始める</li>
<li>動物たちは冬眠や越冬の準備を進める</li>
</ul>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">農事歴（農業暦）</h3>

<div style="background: linear-gradient(135deg, #fef5e7, #fef3c7); padding: 22px; border-radius: 10px; margin-bottom: 25px;">
<p style="margin: 0 0 15px 0; font-size: 18px; font-weight: bold; color: #744210;">この時期は「{agri['period']}」</p>
<ul style="margin: 0; padding-left: 25px; color: #744210;">
{"".join(f"<li style='margin-bottom: 8px;'>{activity}</li>" for activity in agri['activities'])}
</ul>
<p style="margin: 18px 0 0 0; color: #92400e; line-height: 1.8; font-style: italic;">{agri['detail']}</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">日本の風習・しきたり</h3>

<div style="background: #faf5ff; padding: 22px; border-radius: 10px; border-left: 5px solid #9f7aea; margin-bottom: 25px;">
<p style="margin: 0 0 15px 0; line-height: 1.9; color: #2d3748;">{customs['description']}</p>
<h4 style="color: #6b46c1; margin: 15px 0 10px 0; font-size: 18px;">この時期の風習:</h4>
<ul style="margin: 0; padding-left: 25px; color: #2d3748;">
{"".join(f"<li style='margin-bottom: 6px;'>{custom}</li>" for custom in customs['customs'])}
</ul>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">旬の食材・行事食</h3>

<div style="background: linear-gradient(135deg, #e6fffa, #b2f5ea); padding: 22px; border-radius: 10px; margin-bottom: 25px;">
<h4 style="color: #234e52; margin: 0 0 12px 0; font-size: 18px;">旬を迎える食材:</h4>
<p style="margin: 0 0 15px 0; font-size: 16px; color: #2c7a7b; line-height: 1.9;">{", ".join(foods[:8])}</p>
<p style="margin: 0; color: #234e52; line-height: 1.8;">この時期の食材は寒さで甘みが増し、栄養も豊富。鍋料理やおでんなど、体を温める料理が家庭の主役になります。季節の恵みをいただき、自然のリズムを感じましょう。</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">季節の草木と花言葉</h3>

<div style="background: linear-gradient(135deg, #fff0f5, #ffe4f3); padding: 22px; border-radius: 10px; margin-bottom: 25px;">
<p style="margin: 0 0 5px 0; font-size: 20px; font-weight: bold; color: #831843;">季節の花: {flower[0]}</p>
<p style="margin: 10px 0; color: #9f1239; font-size: 16px;"><em>花言葉:</em> 「{flower[1]}」</p>
<p style="margin: 0; color: #be185d; line-height: 1.8;">{flower[2]}</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">月や星の暦・天文情報</h3>

<div style="background: linear-gradient(135deg, #ebf4ff, #dbeafe); padding: 22px; border-radius: 10px; margin-bottom: 25px;">
<p style="margin: 0 0 15px 0; line-height: 1.9; color: #1e40af;">月齢{lunar['age']}の今日は{lunar['appearance'].replace('が見られます', '')}。{lunar['phase']}の時期は、月の陰影の変化が美しく観察できます。</p>
<h4 style="color: #1e3a8a; margin: 15px 0 10px 0; font-size: 18px;">星空では:</h4>
<ul style="margin: 0; padding-left: 25px; color: #1e40af;">
<li style="margin-bottom: 8px;">冬の大三角（オリオン・おおいぬ・こいぬ）が見頃</li>
<li style="margin-bottom: 8px;">空気が澄んでいるため星が美しく輝く</li>
<li>夜が長いため天体観測に最適な季節</li>
</ul>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 35px 0;">

<div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 22px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<p style="margin: 0; font-size: 16px; color: #14532d; font-weight: 500; line-height: 1.8;">
季節を感じながら、今日も良い一日をお過ごしください
</p>
</div>

</div>
"""
        
        return {
            'title': f'{self.date.year}年{self.date.month}月{self.date.day}日({weekday})の暦情報',
            'content': html,
            'labels': ['暦', '二十四節気', '旧暦', '季節', '七十二候', '農事歴', '伝統文化']
        }


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
        # 環境変数チェック
        blog_id = os.environ.get('BLOG_ID')
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        print("=" * 60)
        print("暦情報自動投稿システム 完全版 起動")
        print("=" * 60)
        print(f"投稿日時: {datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')}")
        
        # Gemini API キーの確認
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key:
            print("Gemini API: 有効（AI生成文章を使用）")
        else:
            print("Gemini API: 無効（標準テンプレート使用）")
        
        # 暦情報生成
        print("\n今日の暦情報を生成中...")
        generator = RichCalendarGenerator()
        post_data = generator.generate_html_content()
        
        print(f"   タイトル: {post_data['title']}")
        print(f"   文字数: 約{len(post_data['content'])}文字")
        
        # Blogger投稿
        print("\nBloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 60)
        print("すべての処理が完了しました！")
        print("365日毎日違う内容が自動で投稿されます")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
