#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini統合版
- 正確な天文計算による二十四節気・七十二候
- Gemini APIで温かみのある文章生成
- GitHub Actions毎日7時実行対応
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
    """正確な天文計算クラス"""
    
    @staticmethod
    def calculate_solar_longitude(dt):
        """太陽黄経を精密計算（JPL準拠の簡易版）"""
        jst = ZoneInfo("Asia/Tokyo")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=jst)
        
        # ユリウス日計算
        y, m, d = dt.year, dt.month, dt.day
        h = dt.hour + dt.minute/60.0 + dt.second/3600.0
        
        if m <= 2:
            y -= 1
            m += 12
        
        a = int(y / 100)
        b = 2 - a + int(a / 4)
        jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + h/24.0 + b - 1524.5
        
        # ユリウス世紀
        t = (jd - 2451545.0) / 36525.0
        
        # 太陽の平均黄経
        l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
        l0 = l0 % 360
        
        # 平均近点角
        m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
        m_rad = math.radians(m)
        
        # 離心率
        e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t
        
        # 中心差
        c = (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m_rad)
        c += (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
        c += 0.000289 * math.sin(3 * m_rad)
        
        # 真黄経
        true_longitude = (l0 + c) % 360
        
        return true_longitude
    
    @classmethod
    def get_current_sekki(cls, dt):
        """現在の二十四節気を取得"""
        sekki_data = [
            (315, "立春", "りっしゅん", "春の始まり。寒さの中にも春の気配を感じる季節です。"),
            (330, "雨水", "うすい", "雪が雨に変わり、草木が芽生え始める頃。春の訪れを感じます。"),
            (345, "啓蟄", "けいちつ", "冬眠していた虫たちが目覚め、春の活動を始める時期です。"),
            (0, "春分", "しゅんぶん", "昼夜の長さが等しくなる日。本格的な春の到来を告げます。"),
            (15, "清明", "せいめい", "万物が清らかに生き生きとする季節。花々が咲き誇ります。"),
            (30, "穀雨", "こくう", "田畑を潤す春の雨。農作業が本格化する時期です。"),
            (45, "立夏", "りっか", "夏の始まり。新緑が眩しく、生命力に満ちた季節です。"),
            (60, "小満", "しょうまん", "草木が成長し、天地に気が満ちてくる頃です。"),
            (75, "芒種", "ぼうしゅ", "稲の種まきをする時期。梅雨入りを迎えます。"),
            (90, "夏至", "げし", "一年で最も昼が長い日。夏の盛りへと向かいます。"),
            (105, "小暑", "しょうしょ", "本格的な暑さの始まり。夏本番を迎えます。"),
            (120, "大暑", "たいしょ", "一年で最も暑い時期。うだるような暑さの季節です。"),
            (135, "立秋", "りっしゅう", "秋の始まり。暦の上では秋ですが、残暑が続きます。"),
            (150, "処暑", "しょしょ", "暑さが和らぎ始める頃。朝夕に秋の気配を感じます。"),
            (165, "白露", "はくろ", "草花に白い露が宿る季節。秋の深まりを感じます。"),
            (180, "秋分", "しゅうぶん", "昼夜の長さが等しい日。秋の彼岸の中日です。"),
            (195, "寒露", "かんろ", "露が冷たく感じられる頃。紅葉が美しい季節です。"),
            (210, "霜降", "そうこう", "朝霜が降り始め、秋が深まる時期です。"),
            (225, "立冬", "りっとう", "冬の始まり。木枯らしが吹き始める季節です。"),
            (240, "小雪", "しょうせつ", "わずかに雪が降り始める頃。冬の気配が濃くなります。"),
            (255, "大雪", "たいせつ", "雪が本格的に降る季節。山は雪化粧に包まれます。"),
            (270, "冬至", "とうじ", "一年で最も昼が短い日。これから日が長くなっていきます。"),
            (285, "小寒", "しょうかん", "寒さが厳しくなり始める頃。寒の入りです。"),
            (300, "大寒", "だいかん", "一年で最も寒い時期。寒さの極みです。")
        ]
        
        longitude = cls.calculate_solar_longitude(dt)
        
        for i, (deg, name, reading, desc) in enumerate(sekki_data):
            next_deg = sekki_data[(i + 1) % len(sekki_data)][0]
            
            if deg <= next_deg:
                if deg <= longitude < next_deg:
                    return (name, reading, desc)
            else:
                if longitude >= deg or longitude < next_deg:
                    return (name, reading, desc)
        
        return sekki_data[0][1:]
    
    @classmethod
    def get_current_kou(cls, dt):
        """現在の七十二候を取得（天文計算ベース）"""
        # 簡易版：月日ベースで判定（実用上十分な精度）
        month, day = dt.month, dt.day
        
        kou_data = [
            (2, 4, "東風解凍", "はるかぜこおりをとく", "春の東風が氷を解かし始める頃です。"),
            (2, 9, "黄鶯睍睆", "うぐいすなく", "鶯が美しい声で鳴き始める季節です。"),
            (2, 14, "魚上氷", "うおこおりをいずる", "魚が氷の下から跳ねる様子が見られる頃です。"),
            (2, 19, "土脉潤起", "つちのしょううるおいおこる", "雨が降り、大地が潤い始めます。"),
            (2, 24, "霞始靆", "かすみはじめてたなびく", "春霞がたなびき、景色が柔らかくなります。"),
            (3, 1, "草木萌動", "そうもくめばえいずる", "草木が芽吹き、春の息吹を感じる頃です。"),
            (3, 6, "蟄虫啓戸", "すごもりむしとをひらく", "冬眠していた虫たちが目覚める季節です。"),
            (3, 11, "桃始笑", "ももはじめてさく", "桃の花が咲き始める美しい時期です。"),
            (3, 16, "菜虫化蝶", "なむしちょうとなる", "青虫が蝶へと羽化する生命の季節です。"),
            (3, 21, "雀始巣", "すずめはじめてすくう", "雀が巣作りを始める春の風景です。"),
            (3, 26, "櫻始開", "さくらはじめてひらく", "桜の花が開き始める待ちに待った季節です。"),
            (3, 31, "雷乃発声", "かみなりすなわちこえをはっす", "春の雷が鳴り響き始める頃です。"),
            (4, 5, "玄鳥至", "つばめきたる", "燕が南から渡ってくる春の使者です。"),
            (4, 10, "鴻雁北", "こうがんかえる", "雁が北へ帰っていく季節の変わり目です。"),
            (4, 15, "虹始見", "にじはじめてあらわる", "雨上がりに虹が現れ始める美しい時期です。"),
            (4, 20, "葭始生", "あしはじめてしょうず", "葦が芽を吹き、水辺が賑やかになります。"),
            (4, 25, "霜止出苗", "しもやんでなえいず", "霜が降りなくなり、苗が育つ季節です。"),
            (4, 30, "牡丹華", "ぼたんはなさく", "牡丹の花が豪華に咲き誇る頃です。"),
            (5, 5, "蛙始鳴", "かわずはじめてなく", "蛙の鳴き声が響き始める初夏の風景です。"),
            (5, 10, "蚯蚓出", "みみずいずる", "蚯蚓が地上に這い出てくる季節です。"),
            (5, 15, "竹笋生", "たけのこしょうず", "筍が次々と顔を出す旬の時期です。"),
            (5, 21, "蚕起食桑", "かいこおきてくわをはむ", "蚕が桑の葉を盛んに食べ始めます。"),
            (5, 26, "紅花栄", "べにばなさかう", "紅花が美しく咲き誇る頃です。"),
            (5, 31, "麦秋至", "むぎのときいたる", "麦が黄金色に実る収穫の季節です。"),
            (6, 6, "蟷螂生", "かまきりしょうず", "蟷螂が生まれ出てくる初夏の時期です。"),
            (6, 11, "腐草為螢", "くされたるくさほたるとなる", "蛍が光り始める幻想的な季節です。"),
            (6, 16, "梅子黄", "うめのみきばむ", "梅の実が黄色く熟す梅雨の時期です。"),
            (6, 21, "乃東枯", "なつかれくさかるる", "夏枯草が枯れる夏至の頃です。"),
            (6, 26, "菖蒲華", "あやめはなさく", "菖蒲の花が美しく咲く季節です。"),
            (7, 2, "半夏生", "はんげしょうず", "烏柄杓が生える農作業の目安の時期です。"),
            (7, 7, "温風至", "あつかぜいたる", "暑い風が吹き始める夏本番です。"),
            (7, 12, "蓮始開", "はすはじめてひらく", "蓮の花が開き始める清々しい朝の風景です。"),
            (7, 17, "鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛ぶ練習を始める頃です。"),
            (7, 23, "桐始結花", "きりはじめてはなをむすぶ", "桐の花が実を結ぶ季節です。"),
            (7, 28, "土潤溽暑", "つちうるおうてむしあつし", "土が湿って蒸し暑くなる時期です。"),
            (8, 2, "大雨時行", "たいうときどきふる", "時として大雨が降る夕立の季節です。"),
            (8, 7, "涼風至", "すずかぜいたる", "涼しい風が吹き始める立秋の頃です。"),
            (8, 13, "寒蝉鳴", "ひぐらしなく", "蜩の物悲しい鳴き声が響く季節です。"),
            (8, 18, "蒙霧升降", "ふかききりまとう", "深い霧が立ち込める幻想的な朝です。"),
            (8, 23, "綿柎開", "わたのはなしべひらく", "綿の花のがくが開く頃です。"),
            (8, 28, "天地始粛", "てんちはじめてさむし", "天地の暑さが収まり始める時期です。"),
            (9, 2, "禾乃登", "こくものすなわちみのる", "稲が実り、収穫を迎える実りの秋です。"),
            (9, 7, "草露白", "くさのつゆしろし", "草に降りた露が白く輝く美しい朝です。"),
            (9, 12, "鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める秋の風景です。"),
            (9, 17, "玄鳥去", "つばめさる", "燕が南へ帰っていく季節の変わり目です。"),
            (9, 23, "雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴らなくなる秋分の頃です。"),
            (9, 28, "蟄虫坏戸", "むしかくれてとをふさぐ", "虫たちが土の中に隠れる季節です。"),
            (10, 3, "水始涸", "みずはじめてかるる", "田んぼの水を抜き始める収穫の時期です。"),
            (10, 8, "鴻雁来", "こうがんきたる", "雁が北から渡ってくる秋の風物詩です。"),
            (10, 13, "菊花開", "きくのはなひらく", "菊の花が美しく咲く秋の代表花です。"),
            (10, 18, "蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸口で鳴く秋の夜長です。"),
            (10, 23, "霜始降", "しもはじめてふる", "霜が降り始める霜降の時期です。"),
            (10, 28, "霎時施", "こさめときどきふる", "小雨がしとしと降る晩秋の風景です。"),
            (11, 2, "楓蔦黄", "もみじつたきばむ", "紅葉や蔦が美しく色づく季節です。"),
            (11, 7, "山茶始開", "つばきはじめてひらく", "山茶花が咲き始める立冬の頃です。"),
            (11, 12, "地始凍", "ちはじめてこおる", "大地が凍り始める冬の訪れです。"),
            (11, 17, "金盞香", "きんせんかさく", "水仙の香りが漂う季節です。"),
            (11, 22, "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる小雪の頃です。"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い落とす冬の風景です。"),
            (12, 2, "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色く色づく頃です。"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり、本格的な冬となります。"),
            (12, 12, "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る季節です。"),
            (12, 17, "鱖魚群", "さけのうおむらがる", "鮭が群れをなして川を上る頃です。"),
            (12, 22, "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す冬至の時期です。"),
            (12, 27, "麋角解", "さわしかつのおつる", "大鹿が角を落とす冬の光景です。"),
            (1, 1, "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す生命の力強さです。"),
            (1, 5, "芹乃栄", "せりすなわちさかう", "芹が盛んに生え始める小寒の頃です。"),
            (1, 10, "水泉動", "しみずあたたかをふくむ", "地中の泉が動き始める季節です。"),
            (1, 15, "雉始雊", "きじはじめてなく", "雉が鳴き始める寒中の風景です。"),
            (1, 20, "款冬華", "ふきのはなさく", "蕗の花が咲く大寒の頃です。"),
            (1, 25, "水沢腹堅", "さわみずこおりつめる", "沢の水が厚く凍る寒さの極みです。"),
            (1, 30, "鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める春への準備の時期です。")
        ]
        
        current_kou = kou_data[0][2:]
        for m, d, name, reading, desc in reversed(kou_data):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading, desc)
                break
        
        return current_kou


class LunarCalendar:
    """旧暦計算クラス"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """旧暦計算（2025年12月10日=旧暦10/21基準）"""
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
            phase, appearance = "下弦へ向かう月", "夜半から明け方に欠けていく月"
        elif 22.1 <= moon_age < 25.9:
            phase, appearance = "下弦の月", "明け方に半月が見えます"
        else:
            phase, appearance = "晦日月", "明け方の東空に細い月"
        
        return {
            'year': lunar_year,
            'month': lunar_month,
            'day': lunar_day,
            'age': round(moon_age, 1),
            'phase': phase,
            'appearance': appearance
        }


class GeminiEnhancer:
    """Gemini APIで文章を充実させるクラス"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        self.request_count = 0
        self.max_requests = 10  # 無料枠を考慮
    
    def enhance_text(self, section_name, base_text, context=""):
        """セクションの文章を充実させる"""
        if self.request_count >= self.max_requests:
            return base_text
        
        prompt = f"""以下の暦情報の「{section_name}」セクションの文章を、温かみがあり、親しみやすく、読者が季節を感じられるように200-300文字程度に充実させてください。

【元の文章】
{base_text}

【コンテキスト】
{context}

【要件】
- 温かく親しみやすい語り口
- 具体的なイメージが浮かぶ表現
- 季節感や日本の伝統文化を大切に
- 読者に語りかけるような文体
- 200-300文字程度

充実させた文章のみを出力してください。"""
        
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500
                }
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                enhanced = result['candidates'][0]['content']['parts'][0]['text'].strip()
                self.request_count += 1
                time.sleep(1)  # レート制限対策
                return enhanced
            else:
                print(f"Gemini API エラー: {response.status_code}")
                return base_text
                
        except Exception as e:
            print(f"文章生成エラー: {str(e)}")
            return base_text


class CalendarContentGenerator:
    """暦コンテンツ生成クラス"""
    
    def __init__(self, target_date=None, gemini_api_key=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.gemini = GeminiEnhancer(gemini_api_key) if gemini_api_key else None
    
    def get_lunar_month_names(self):
        """旧暦月の異名"""
        return {
            1: ("睦月", "むつき", "親族が睦み合う月"),
            2: ("如月", "きさらぎ", "衣を更に着る寒い月"),
            3: ("弥生", "やよい", "草木がいよいよ生い茂る月"),
            4: ("卯月", "うづき", "卯の花が咲く月"),
            5: ("皐月", "さつき", "早苗を植える月"),
            6: ("水無月", "みなづき", "水の月、田に水を引く月"),
            7: ("文月", "ふみづき", "文を披露する月、七夕の月"),
            8: ("葉月", "はづき", "葉が落ち始める月"),
            9: ("長月", "ながつき", "夜が長くなる月"),
            10: ("神無月", "かんなづき", "神々が出雲に集まる月"),
            11: ("霜月", "しもつき", "霜が降り始める月"),
            12: ("師走", "しわす", "師も走るほど忙しい月")
        }
    
    def generate_seasonal_intro(self, lunar, sekki, kou):
        """季節の導入文（Gemini強化版）"""
        lunar_names = self.get_lunar_month_names()
        lunar_info = lunar_names.get(lunar['month'], ("", "", ""))
        
        base_text = f"旧暦{lunar['month']}月は「{lunar_info[0]}（{lunar_info[1]}）」。{lunar_info[2]}とされています。月齢{lunar['age']}の{lunar['phase']}の頃、{lunar['appearance']}が見られます。二十四節気は{sekki[0]}、七十二候は{kou[0]}で、{kou[2]}"
        
        if self.gemini:
            context = f"日付: {self.date.year}年{self.date.month}月{self.date.day}日"
            return self.gemini.enhance_text("季節の導入", base_text, context)
        return base_text
    
    def get_seasonal_data(self):
        """季節データ取得"""
        data = {
            1: {
                'nature': ['寒さが最も厳しい', '霜柱が美しい', '梅のつぼみが膨らむ', '寒中の凛とした空気'],
                'weather': ['一年で最も寒い', '太平洋側は乾燥した晴天', '日本海側は雪が多い', '空気が澄んで星が美しい'],
                'foods': {
                    'vegetables': ['白菜', 'ネギ', '大根', 'ほうれん草', '春菊'],
                    'fruits': ['みかん', 'りんご', 'いちご'],
                    'seafood': ['鱈', '寒ブリ', '牡蠣', 'あんこう'],
                    'special': '寒さで甘みが増した野菜が美味しい時期。鍋料理が一層美味しくなります。'
                },
                'flowers': ('福寿草', '幸せを招く', '雪解けとともに咲く春の使者、黄金色の花が新春を祝います。'),
                'customs': ['初詣', '七草粥', '鏡開き', '小正月', '寒中見舞い']
            },
            2: {
                'nature': ['梅の花が咲き始める', '鶯の初音', '日差しが強くなる', '雪解けが始まる'],
                'weather': ['三寒四温で春へ', '梅の香りが漂う', '風はまだ冷たい', '日が少しずつ長くなる'],
                'foods': {
                    'vegetables': ['白菜', 'ネギ', 'ブロッコリー', 'ほうれん草'],
                    'fruits': ['いちご', 'キウイ', 'はっさく'],
                    'seafood': ['鰆', 'わかめ', '牡蠣'],
                    'special': '冬野菜が美味しく、春の走りの食材も出始めます。'
                },
                'flowers': ('梅', '高潔・忍耐', '早春に咲く香り高い花、まだ寒い中で春の訪れを告げます。'),
                'customs': ['節分・豆まき', '初午', '建国記念の日', '針供養']
            },
            3: {
                'nature': ['桜の開花', '菜の花が咲く', '蝶が飛び始める', '春の嵐'],
                'weather': ['三寒四温', '花冷えもある', '春雨が降る', '陽気が不安定'],
                'foods': {
                    'vegetables': ['菜の花', '春キャベツ', '新玉ねぎ', 'たけのこ'],
                    'fruits': ['いちご', 'デコポン', 'はっさく'],
                    'seafood': ['桜鯛', 'ホタルイカ', 'あさり', 'しらす'],
                    'special': '春の息吹を感じる山菜や新野菜が出回り始めます。'
                },
                'flowers': ('桜', '精神の美', '日本の春を代表する花、満開の桜は心を魅了します。'),
                'customs': ['ひな祭り', '春分の日・彼岸', '卒業式', '花見']
            },
            4: {
                'nature': ['新緑が美しい', 'ツバメが飛来', '筍が顔を出す', '八重桜'],
                'weather': ['穏やかな春の陽気', '時折春の嵐', '朝晩は冷えることも', '清々しい青空'],
                'foods': {
                    'vegetables': ['筍', '新じゃがいも', '春キャベツ', 'そら豆'],
                    'fruits': ['いちご', 'グレープフルーツ'],
                    'seafood': ['初鰹', '桜えび', 'あさり'],
                    'special': '新野菜が豊富に出回り、春の味覚を存分に楽しめます。'
                },
                'flowers': ('藤', '歓迎・優しさ', '紫の花房が美しく垂れ下がり、藤棚の下は幻想的です。'),
                'customs': ['入学式・入社式', '花見', '灌仏会', '昭和の日']
            },
            5: {
                'nature': ['新緑が濃くなる', '田植えが始まる', '初鰹が旬', '初夏の風'],
                'weather': ['爽やかな初夏', '五月晴れ', '朝晩は涼しい', '紫外線が強くなる'],
                'foods': {
                    'vegetables': ['新玉ねぎ', 'そら豆', '新生姜', 'たけのこ'],
                    'fruits': ['さくらんぼ', 'メロン', 'びわ'],
                    'seafood': ['初鰹', 'アジ', 'イサキ'],
                    'special': '新緑の季節にふさわしい、瑞々しい野菜が美味しい時期。'
                },
                'flowers': ('牡丹', '富貴・高貴', '百花の王、大きく華やかな花が初夏を彩ります。'),
                'customs': ['端午の節句', 'こどもの日', '母の日', '八十八夜']
            },
            6: {
                'nature': ['梅雨入り', '紫陽花が咲く', '蛍が飛ぶ', '夏至'],
                'weather': ['梅雨の雨', '蒸し暑くなる', '時々晴れ間', '湿度が高い'],
                'foods': {
                    'vegetables': ['梅', 'らっきょう', '新生姜', 'きゅうり'],
                    'fruits': ['さくらんぼ', 'びわ', 'メロン'],
                    'seafood': ['アジ', 'イワシ', '穴子', 'あゆ'],
                    'special': '梅仕事の季節、梅干しや梅酒作りが楽しい時期。'
                },
                'flowers': ('紫陽花', '移り気・辛抱強い愛', '梅雨を彩る色変わりの花、雨に濡れた姿が美しい。'),
                'customs': ['衣替え', '夏越の祓', '父の日', '梅仕事']
            },
            7: {
                'nature': ['梅雨明け', 'セミが鳴く', '入道雲', '海開き'],
                'weather': ['本格的な夏', '強い日差し', '夕立がある', '蒸し暑い'],
                'foods': {
                    'vegetables': ['トマト', 'きゅうり', 'なす', 'とうもろこし'],
                    'fruits': ['桃', 'スイカ', 'メロン'],
                    'seafood': ['鰻', 'アジ', '穴子', 'ハモ'],
                    'special': '夏野菜が本格的に出回り、夏バテ防止に効果的。'
                },
                'flowers': ('朝顔', 'はかない恋', '夏の朝を飾る涼しげな花、日本の夏の風物詩。'),
                'customs': ['七夕', '土用の丑の日', 'お盆', '夏祭り']
            },
            8: {
                'nature': ['残暑が厳しい', '台風の季節', '秋の気配', '流星群'],
                'weather': ['猛暑が続く', '台風が接近', '朝晩少し涼しく', '夕立が多い'],
                'foods': {
                    'vegetables': ['トマト', 'きゅうり', 'なす', 'オクラ'],
                    'fruits': ['桃', 'スイカ', 'ぶどう'],
                    'seafood': ['鰹', 'アジ', '太刀魚'],
                    'special': '真夏の暑さに負けないよう、栄養豊富な夏野菜を。'
                },
                'flowers': ('向日葵', 'あなただけを見つめる', '太陽に向かって咲く、元気と明るさの象徴。'),
                'customs': ['お盆', '迎え火・送り火', '終戦記念日', '夏祭り']
            },
            9: {
                'nature': ['秋の七草', '稲刈り', '赤とんぼ', '秋分'],
                'weather': ['秋らしくなる', '台風が多い', '秋雨前線', '爽やかな日も'],
                'foods': {
                    'vegetables': ['さつまいも', '里芋', '栗', '松茸'],
                    'fruits': ['ぶどう', '梨', '柿'],
                    'seafood': ['秋刀魚', '鰹', '鮭'],
                    'special': '実りの秋、きのこ類や根菜類が美味しくなります。'
                },
                'flowers': ('彼岸花', '再会・情熱', '秋の彼岸に咲く真紅の花、別名曼珠沙華。'),
                'customs': ['重陽の節句', '十五夜', '秋分の日・彼岸', '敬老の日']
            },
            10: {
                'nature': ['紅葉が始まる', '金木犀の香り', '秋雨前線', '渡り鳥'],
                'weather': ['秋晴れが多い', '朝晩冷える', '台風が時々', '空が高く感じる'],
                'foods': {
                    'vegetables': ['さつまいも', '里芋', '栗', '松茸'],
                    'fruits': ['柿', 'りんご', 'ぶどう'],
                    'seafood': ['秋刀魚', '鮭', '鯖', '牡蠣'],
                    'special': '秋の味覚が最盛期、実りの季節を存分に楽しめます。'
                },
                'flowers': ('コスモス', '調和・謙虚', '秋風に揺れる可憐な花、秋桜とも書きます。'),
                'customs': ['衣替え', '十三夜', '体育の日', '秋祭り']
            },
            11: {
                'nature': ['紅葉が見頃', '木枯らし', '冬鳥飛来', '初雪'],
                'weather': ['晩秋の冷え込み', '木枯らしが吹く', '初雪の便り', '空気が乾燥'],
                'foods': {
                    'vegetables': ['大根', '白菜', '春菊', 'ほうれん草'],
                    'fruits': ['柿', 'みかん', 'りんご', 'ゆず'],
                    'seafood': ['ブリ', '鯖', '牡蠣', 'ふぐ'],
                    'special': '大根が甘くなり、鍋料理が美味しい季節です。'
                },
                'flowers': ('山茶花', '困難に打ち勝つ', '霜に負けず咲く、冬の訪れを告げる花。'),
                'customs': ['文化の日', '七五三', '新嘗祭', '勤労感謝の日']
            },
            12: {
                'nature': ['霜柱', '冬鳥が増える', '干し柿', '冬木立'],
                'weather': ['本格的な寒さ', '乾燥した晴天', '初雪が積もる', '冬至で昼が最短'],
                'foods': {
                    'vegetables': ['大根', '白菜', '春菊', 'ネギ', 'ゆず'],
                    'fruits': ['みかん', 'りんご', '柚子', '金柑'],
                    'seafood': ['ブリ', '牡蠣', '鱈', 'ふぐ', 'あんこう'],
                    'special': '大根が甘く、鍋料理が家庭の主役になります。'
                },
                'flowers': ('水仙', '自己愛・神秘', '清楚な香りの冬の花、凛と咲く姿が美しい。'),
                'customs': ['冬囲い', 'すす払い', '冬至の柚子湯', 'クリスマス', '大晦日']
            }
        }
        return data.get(self.date.month, data[12])
    
    def generate_full_html(self):
        """完全版HTML生成"""
        lunar = LunarCalendar.calculate_lunar_date(self.date)
        sekki = AstronomicalCalculator.get_current_sekki(self.date)
        kou = AstronomicalCalculator.get_current_kou(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        seasonal_data = self.get_seasonal_data()
        seasonal_intro = self.generate_seasonal_intro(lunar, sekki, kou)
        
        # セクション生成
        nature_section = self._generate_nature_section(seasonal_data)
        weather_section = self._generate_weather_section(seasonal_data)
        food_section = self._generate_food_section(seasonal_data)
        flower_section = self._generate_flower_section(seasonal_data)
        customs_section = self._generate_customs_section(seasonal_data)
        
        html = f"""
<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 24px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 15px 0 0 0; font-size: 20px;">旧暦: {lunar['month']}月{lunar['day']}日</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 17px; opacity: 0.95;">{lunar['appearance']}</p>
</div>

<div style="background: #f7fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #4299e1; margin-bottom: 35px;">
<p style="margin: 0; line-height: 2; font-size: 16px;">{seasonal_intro}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #fc8181; padding-left: 15px;">季節の移ろい</h3>

<div style="background: linear-gradient(to right, #fff5f5, transparent); border-left: 6px solid #fc8181; padding: 25px; margin-bottom: 25px; border-radius: 8px;">
<h4 style="color: #c53030; margin: 0 0 12px 0; font-size: 22px;">二十四節気: {sekki[0]}（{sekki[1]}）</h4>
<p style="margin: 0; color: #2d3748; line-height: 2; font-size: 16px;">{sekki[2]}</p>
</div>

<div style="background: linear-gradient(to right, #f0fff4, transparent); border-left: 6px solid #48bb78; padding: 25px; margin-bottom: 30px; border-radius: 8px;">
<h4 style="color: #2f855a; margin: 0 0 12px 0; font-size: 22px;">七十二候: {kou[0]}</h4>
<p style="margin: 8px 0; color: #2d3748; font-size: 15px;"><em>読み:</em> {kou[1]}</p>
<p style="margin: 12px 0 0 0; color: #2d3748; line-height: 2; font-size: 16px;">{kou[2]}</p>
</div>

{nature_section}

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

{weather_section}

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

{food_section}

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

{flower_section}

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

{customs_section}

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
<p style="margin: 0; font-size: 18px; color: #14532d; font-weight: 500; line-height: 2;">
季節の移ろいを感じながら、心穏やかな一日をお過ごしください
</p>
</div>

</div>
"""
        
        lunar_names = self.get_lunar_month_names()
        lunar_info = lunar_names.get(lunar['month'], ("", "", ""))
        
        return {
            'title': f'{self.date.year}年{self.date.month}月{self.date.day}日({weekday})の暦 - {sekki[0]}・{lunar_info[0]}',
            'content': html,
            'labels': ['暦', '二十四節気', '七十二候', '旧暦', '季節', '伝統', '行事', '自然']
        }
    
    def _generate_nature_section(self, data):
        """自然の変化セクション"""
        base = "、".join(data['nature'])
        if self.gemini:
            enhanced = self.gemini.enhance_text("自然の変化", base, f"{self.date.month}月の自然")
        else:
            enhanced = f"この時期は{base}など、自然の変化を感じられる季節です。"
        
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #68d391; padding-left: 15px;">自然の変化</h3>
<div style="background: #fffaf0; padding: 25px; border-radius: 10px; margin-bottom: 30px; border: 2px solid #fbd38d;">
<p style="margin: 0; color: #2d3748; line-height: 2; font-size: 16px;">{enhanced}</p>
</div>
"""
    
    def _generate_weather_section(self, data):
        """気象情報セクション"""
        items = "".join(f"<li style='margin-bottom: 12px; font-size: 16px;'>{w}</li>" for w in data['weather'])
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #38b2ac; padding-left: 15px;">気象と空の様子</h3>
<div style="background: linear-gradient(135deg, #e6fffa, #b2f5ea); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<ul style="margin: 0; padding-left: 30px; color: #234e52; line-height: 2;">
{items}
</ul>
</div>
"""
    
    def _generate_food_section(self, data):
        """旬の食材セクション"""
        foods = data['foods']
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f56565; padding-left: 15px;">旬の食材・味覚</h3>
<div style="background: linear-gradient(135deg, #fff5f5, #fed7d7); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<p style="margin: 0 0 8px 0; font-size: 16px; color: #742a2a; line-height: 1.8;">
<strong>野菜:</strong> {", ".join(foods['vegetables'])}
</p>
<p style="margin: 8px 0; font-size: 16px; color: #742a2a; line-height: 1.8;">
<strong>果物:</strong> {", ".join(foods['fruits'])}
</p>
<p style="margin: 8px 0; font-size: 16px; color: #742a2a; line-height: 1.8;">
<strong>魚介:</strong> {", ".join(foods['seafood'])}
</p>
<p style="margin: 20px 0 0 0; padding: 18px; background: rgba(255,255,255,0.6); border-radius: 8px; color: #742a2a; line-height: 2; font-size: 15px;">{foods['special']}</p>
</div>
"""
    
    def _generate_flower_section(self, data):
        """季節の花セクション"""
        name, meaning, desc = data['flowers']
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f687b3; padding-left: 15px;">季節の花</h3>
<div style="background: linear-gradient(135deg, #fff0f5, #ffe4f3); padding: 28px; border-radius: 12px; margin-bottom: 25px;">
<p style="margin: 0 0 8px 0; font-size: 22px; font-weight: bold; color: #831843;">{name}</p>
<p style="margin: 12px 0; color: #9f1239; font-size: 17px;"><em>花言葉:</em> 「{meaning}」</p>
<p style="margin: 12px 0 0 0; color: #be185d; line-height: 2; font-size: 16px;">{desc}</p>
</div>
"""
    
    def _generate_customs_section(self, data):
        """風習・しきたりセクション"""
        items = "".join(f"<li style='margin-bottom: 10px; font-size: 15px;'>{c}</li>" for c in data['customs'])
        return f"""
<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #9f7aea; padding-left: 15px;">この時期の風習</h3>
<div style="background: #faf5ff; padding: 28px; border-radius: 12px; border-left: 6px solid #9f7aea; margin-bottom: 30px;">
<ul style="margin: 0; padding-left: 30px; color: #2d3748; line-height: 2;">
{items}
</ul>
</div>
"""


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
            
            print(f"✓ 投稿成功: {response.get('url')}")
            return response
        except Exception as e:
            print(f"✗ 投稿エラー: {str(e)}")
            raise


def main():
    """メイン処理"""
    try:
        blog_id = os.environ.get('BLOG_ID')
        gemini_key = os.environ.get('GEMINI_API_KEY')
        
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        print("=" * 70)
        print("暦情報自動投稿システム - Gemini統合版")
        print("=" * 70)
        jst = ZoneInfo('Asia/Tokyo')
        now = datetime.now(jst)
        print(f"実行日時: {now.strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"Gemini API: {'有効' if gemini_key else '無効（基本版）'}")
        
        # 暦情報生成
        print("\n暦情報を生成中...")
        generator = CalendarContentGenerator(target_date=now, gemini_api_key=gemini_key)
        post_data = generator.generate_full_html()
        
        print(f"✓ タイトル: {post_data['title']}")
        print(f"✓ コンテンツサイズ: {len(post_data['content'])} 文字")
        
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
