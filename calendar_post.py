#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini連携版
温かみのある文章をAIで生成
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
    """二十四節気・七十二候の天文計算クラス"""
    
    @staticmethod
    def calculate_solar_term_date(year, solar_longitude):
        """指定した年と太陽黄経から節気の日付を計算"""
        sekki_params = {
            315: (5.01, 0.242778), 330: (19.70, 0.242713), 345: (6.38, 0.242627),
            0: (21.43, 0.242194), 15: (5.59, 0.241934), 30: (21.04, 0.241669),
            45: (6.30, 0.241424), 60: (22.18, 0.241176), 75: (6.62, 0.240959),
            90: (22.29, 0.240715), 105: (7.93, 0.240460), 120: (23.95, 0.240252),
            135: (8.52, 0.240014), 150: (24.30, 0.239766), 165: (8.60, 0.239527),
            180: (23.89, 0.239300), 195: (9.09, 0.239063), 210: (24.19, 0.238825),
            225: (8.19, 0.238591), 240: (23.15, 0.238355), 255: (7.93, 0.238120),
            270: (22.66, 0.237885), 285: (6.12, 0.237651), 300: (20.87, 0.237418)
        }
        
        if solar_longitude not in sekki_params:
            return None
        
        D, A = sekki_params[solar_longitude]
        
        if solar_longitude in [285, 300, 315, 330]:
            Y = year - 1900 - 1
        else:
            Y = year - 1900
        
        day = int(D + (A * Y) - int(Y / 4))
        
        month_map = {
            285: (1, 0), 300: (1, 15), 315: (2, 0), 330: (2, 14), 345: (3, 0),
            0: (3, 15), 15: (4, 0), 30: (4, 15), 45: (5, 0), 60: (5, 16),
            75: (6, 0), 90: (6, 16), 105: (7, 0), 120: (7, 16), 135: (8, 0),
            150: (8, 16), 165: (9, 0), 180: (9, 16), 195: (10, 0), 210: (10, 15),
            225: (11, 0), 240: (11, 15), 255: (12, 0), 270: (12, 15)
        }
        
        month, offset = month_map[solar_longitude]
        day += offset
        
        return (month, day)
    
    @classmethod
    def get_current_sekki(cls, date):
        """現在の二十四節気を天文計算で取得"""
        year = date.year
        month = date.month
        day = date.day
        
        sekki_definitions = [
            (315, "立春", "りっしゅん", "春の始まり。暦の上では春ですが、まだ寒さが厳しい時期です。"),
            (330, "雨水", "うすい", "雪が雨に変わり、氷が解け始める頃。三寒四温で春に向かいます。"),
            (345, "啓蟄", "けいちつ", "冬眠していた虫が目覚める頃。春の訪れを実感できます。"),
            (0, "春分", "しゅんぶん", "昼夜の長さがほぼ等しくなる日。これから昼が長くなります。"),
            (15, "清明", "せいめい", "万物が清らかで生き生きとする頃。花が咲き誇る季節です。"),
            (30, "穀雨", "こくう", "穀物を潤す春の雨が降る頃。田植えの準備が始まります。"),
            (45, "立夏", "りっか", "夏の始まり。新緑が目に鮮やかな季節です。"),
            (60, "小満", "しょうまん", "草木が茂り、天地に気が満ち始める頃です。"),
            (75, "芒種", "ぼうしゅ", "麦を刈り、稲を植える農繁期。梅雨入りの時期です。"),
            (90, "夏至", "げし", "一年で最も昼が長い日。これから暑さが本格化します。"),
            (105, "小暑", "しょうしょ", "梅雨明け頃。本格的な暑さの始まりです。"),
            (120, "大暑", "たいしょ", "一年で最も暑い時期。夏真っ盛りです。"),
            (135, "立秋", "りっしゅう", "秋の始まり。暦の上では秋ですが、残暑が厳しい時期。"),
            (150, "処暑", "しょしょ", "暑さが峠を越える頃。朝夕が涼しくなり始めます。"),
            (165, "白露", "はくろ", "草木に白い露が宿り始める頃。秋の気配が濃くなります。"),
            (180, "秋分", "しゅうぶん", "昼夜の長さがほぼ等しい。秋彼岸の中日です。"),
            (195, "寒露", "かんろ", "露が冷たく感じられる頃。紅葉が始まります。"),
            (210, "霜降", "そうこう", "朝霜が降り始める頃。秋が深まります。"),
            (225, "立冬", "りっとう", "冬の始まり。暦の上では冬入りです。"),
            (240, "小雪", "しょうせつ", "わずかに雪が降り始める頃。冬の気配が強まります。"),
            (255, "大雪", "たいせつ", "雪が本格的に降り始める頃。山は雪化粧です。"),
            (270, "冬至", "とうじ", "一年で最も昼が短い日。これから日が長くなります。"),
            (285, "小寒", "しょうかん", "寒さが厳しくなり始める頃。寒の入りです。"),
            (300, "大寒", "だいかん", "一年で最も寒い時期。寒さの極みです。")
        ]
        
        sekki_dates = []
        for longitude, name, reading, desc in sekki_definitions:
            term_date = cls.calculate_solar_term_date(year, longitude)
            if term_date:
                sekki_dates.append((term_date[0], term_date[1], name, reading, desc))
        
        for longitude in [255, 270, 285, 300]:
            term_date = cls.calculate_solar_term_date(year - 1, longitude)
            if term_date:
                for lng, name, reading, desc in sekki_definitions:
                    if lng == longitude:
                        sekki_dates.append((term_date[0], term_date[1], name, reading, desc))
        
        current_sekki = sekki_dates[0][2:]
        for m, d, name, reading, desc in sekki_dates:
            if month > m or (month == m and day >= d):
                current_sekki = (name, reading, desc)
        
        return current_sekki
    
    @classmethod
    def get_kou_info(cls, date):
        """現在の七十二候を節気から自動計算"""
        year = date.year
        month = date.month
        day = date.day
        
        kou_complete_list = [
            (2, 4, "東風解凍", "はるかぜこおりをとく", "春風が氷を解かし始める頃。立春の初候です。"),
            (2, 9, "黄鶯睍睆", "うぐいすなく", "鶯が山里で鳴き始める頃。春の訪れを告げる鳴き声です。"),
            (2, 14, "魚上氷", "うおこおりをいずる", "割れた氷の間から魚が飛び跳ねる頃です。"),
            (2, 19, "土脉潤起", "つちのしょううるおいおこる", "雨が降って土が湿り気を含む頃です。"),
            (2, 24, "霞始靆", "かすみはじめてたなびく", "霞がたなびき、春景色が広がる頃です。"),
            (2, 29, "草木萌動", "そうもくめばえいずる", "草木が芽吹き始める頃。春の息吹を感じます。"),
            (3, 5, "蟄虫啓戸", "すごもりむしとをひらく", "冬眠していた虫が外に這い出てくる頃です。"),
            (3, 10, "桃始笑", "ももはじめてさく", "桃の花が咲き始める頃。笑は咲くの意味です。"),
            (3, 15, "菜虫化蝶", "なむしちょうとなる", "青虫が蝶に羽化する頃。春の生命の躍動です。"),
            (3, 20, "雀始巣", "すずめはじめてすくう", "雀が巣を作り始める頃です。"),
            (3, 25, "櫻始開", "さくらはじめてひらく", "桜が咲き始める頃。春の代名詞です。"),
            (3, 30, "雷乃発声", "かみなりすなわちこえをはっす", "遠くで雷の音が聞こえ始める頃です。"),
            (4, 4, "玄鳥至", "つばめきたる", "燕が南から渡ってくる頃。春の使者です。"),
            (4, 9, "鴻雁北", "こうがんかえる", "雁が北へ帰っていく頃です。"),
            (4, 14, "虹始見", "にじはじめてあらわる", "雨上がりに虹が出始める頃です。"),
            (4, 20, "葭始生", "あしはじめてしょうず", "葦が芽を吹き始める頃です。"),
            (4, 25, "霜止出苗", "しもやんでなえいず", "霜が降りなくなり、苗が育つ頃です。"),
            (4, 30, "牡丹華", "ぼたんはなさく", "牡丹の花が咲く頃。華やかな春の終わりです。"),
            (5, 5, "蛙始鳴", "かわずはじめてなく", "蛙が鳴き始める頃。初夏の風物詩です。"),
            (5, 10, "蚯蚓出", "みみずいずる", "蚯蚓が地上に這い出てくる頃です。"),
            (5, 15, "竹笋生", "たけのこしょうず", "筍が生えてくる頃。旬の味覚です。"),
            (5, 21, "蚕起食桑", "かいこおきてくわをはむ", "蚕が桑の葉を盛んに食べ始める頃です。"),
            (5, 26, "紅花栄", "べにばなさかう", "紅花が盛んに咲く頃です。"),
            (5, 31, "麦秋至", "むぎのときいたる", "麦が熟し、収穫期を迎える頃です。"),
            (6, 5, "蟷螂生", "かまきりしょうず", "蟷螂が生まれ出る頃です。"),
            (6, 10, "腐草為螢", "くされたるくさほたるとなる", "蛍が光を放ち始める頃。初夏の風情です。"),
            (6, 16, "梅子黄", "うめのみきばむ", "梅の実が黄ばんで熟す頃です。"),
            (6, 21, "乃東枯", "なつかれくさかるる", "夏枯草が枯れる頃。夏至の日です。"),
            (6, 26, "菖蒲華", "あやめはなさく", "菖蒲の花が咲く頃です。"),
            (7, 2, "半夏生", "はんげしょうず", "烏柄杓が生える頃。田植えの目安とされました。"),
            (7, 7, "温風至", "あつかぜいたる", "暑い風が吹いてくる頃。夏本番です。"),
            (7, 12, "蓮始開", "はすはじめてひらく", "蓮の花が開き始める頃です。"),
            (7, 17, "鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛び方を覚える頃です。"),
            (7, 22, "桐始結花", "きりはじめてはなをむすぶ", "桐の花が実を結ぶ頃です。"),
            (7, 28, "土潤溽暑", "つちうるおうてむしあつし", "土が湿って蒸し暑くなる頃です。"),
            (8, 2, "大雨時行", "たいうときどきふる", "時として大雨が降る頃。夕立の季節です。"),
            (8, 7, "涼風至", "すずかぜいたる", "涼しい風が吹き始める頃。立秋です。"),
            (8, 12, "寒蝉鳴", "ひぐらしなく", "蜩が鳴き始める頃。秋の気配を感じます。"),
            (8, 17, "蒙霧升降", "ふかききりまとう", "深い霧がまとわりつく頃です。"),
            (8, 23, "綿柎開", "わたのはなしべひらく", "綿の花のがくが開く頃です。"),
            (8, 28, "天地始粛", "てんちはじめてさむし", "天地の暑さが収まり始める頃です。"),
            (9, 2, "禾乃登", "こくものすなわちみのる", "稲が実る頃。実りの秋です。"),
            (9, 7, "草露白", "くさのつゆしろし", "草に降りた露が白く見える頃です。"),
            (9, 12, "鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める頃です。"),
            (9, 17, "玄鳥去", "つばめさる", "燕が南へ帰っていく頃です。"),
            (9, 23, "雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴らなくなる頃。秋分です。"),
            (9, 28, "蟄虫坏戸", "むしかくれてとをふさぐ", "虫が土の中に隠れる頃です。"),
            (10, 3, "水始涸", "みずはじめてかるる", "田んぼの水を抜き始める頃です。"),
            (10, 8, "鴻雁来", "こうがんきたる", "雁が飛来する頃。冬鳥の到来です。"),
            (10, 13, "菊花開", "きくのはなひらく", "菊の花が咲く頃です。"),
            (10, 18, "蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸口で鳴く頃です。"),
            (10, 23, "霜始降", "しもはじめてふる", "霜が降り始める頃。霜降です。"),
            (10, 28, "霎時施", "こさめときどきふる", "小雨がしとしと降る頃です。"),
            (11, 2, "楓蔦黄", "もみじつたきばむ", "紅葉や蔦が黄葉する頃です。"),
            (11, 7, "山茶始開", "つばきはじめてひらく", "山茶花が咲き始める頃。立冬です。"),
            (11, 12, "地始凍", "ちはじめてこおる", "大地が凍り始める頃です。"),
            (11, 17, "金盞香", "きんせんかさく", "水仙の花が咲く頃です。"),
            (11, 22, "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる頃。小雪です。"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い落とす頃。冬の風物詩です。"),
            (12, 2, "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色く色づく頃です。"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり、本格的な冬となる頃。大雪です。"),
            (12, 12, "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る頃です。"),
            (12, 16, "鱖魚群", "さけのうおむらがる", "鮭が群がって川を上る頃です。"),
            (12, 21, "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す頃。冬至です。"),
            (12, 26, "麋角解", "さわしかつのおつる", "大鹿が角を落とす頃です。"),
            (12, 31, "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃です。"),
            (1, 5, "芹乃栄", "せりすなわちさかう", "芹が盛んに生え始める頃。小寒です。"),
            (1, 10, "水泉動", "しみずあたたかをふくむ", "地中で凍った泉が動き始める頃です。"),
            (1, 15, "雉始雊", "きじはじめてなく", "雉が鳴き始める頃です。"),
            (1, 20, "款冬華", "ふきのはなさく", "蕗の花が咲く頃。大寒です。"),
            (1, 25, "水沢腹堅", "さわみずこおりつめる", "沢の水が厚く凍る頃。寒さの極みです。"),
            (1, 30, "鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める頃です。")
        ]
        
        current_kou = kou_complete_list[0][2:]
        
        for m, d, name, reading, desc in reversed(kou_complete_list):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading, desc)
                break
        
        if month == 12 and day >= 31:
            current_kou = ("雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃です。")
        elif month == 1 and day < 5:
            current_kou = ("雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃です。")
        
        return current_kou


class AccurateLunarCalendar:
    """正確な旧暦計算"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """旧暦を計算"""
        reference = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        reference_lunar_year = 2025
        reference_lunar_month = 10
        reference_lunar_day = 21
        reference_moon_age = 19.8
        
        synodic = 29.530588861
        
        elapsed_days = (date - reference).total_seconds() / 86400
        
        moon_age = (reference_moon_age + elapsed_days) % synodic
        if moon_age < 0:
            moon_age += synodic
        
        elapsed_months = int((reference_moon_age + elapsed_days) / synodic)
        
        lunar_year = reference_lunar_year
        lunar_month = reference_lunar_month
        lunar_day = reference_lunar_day
        
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
        
        days_in_current_month = elapsed_days - (elapsed_months * synodic)
        lunar_day = reference_lunar_day + int(days_in_current_month)
        
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
        
        if lunar_day > 30:
            lunar_day = 30
        
        if moon_age < 1.5:
            phase = "新月"
            appearance = "夜空に月は見えません"
        elif moon_age < 3.7:
            phase = "二日月"
            appearance = "夕方の西空に細い月が輝きます"
        elif moon_age < 7.4:
            phase = "上弦へ向かう月"
            appearance = "夕方の空に弓なりの上弦へ向かう月"
        elif 7.4 <= moon_age < 11:
            phase = "上弦の月"
            appearance = "宵の空に半月が見えます"
        elif moon_age < 14.8:
            phase = "満月へ向かう月"
            appearance = "宵から夜半にかけて膨らむ月"
        elif 14.8 <= moon_age < 16.3:
            phase = "満月"
            appearance = "夜通し輝く丸い月"
        elif moon_age < 22.1:
            phase = "下弦へ向かう月"
            appearance = "夜半から明け方に欠けていく月"
        elif 22.1 <= moon_age < 25.9:
            phase = "下弦の月"
            appearance = "明け方に半月が見えます"
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


class GeminiEnhancer:
    """Gemini APIで文章を温かく充実させる"""
    
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise Exception("GEMINI_API_KEY環境変数が設定されていません")
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    def enhance_text(self, section_name, base_text, context):
        """セクションの文章を温かく充実させる"""
        
        prompt = f"""あなたは日本の伝統文化に詳しい、温かみのある文章を書く専門家です。
以下の暦情報のセクション「{section_name}」の文章を、より温かく、詳細で、読者が季節を感じられるように充実させてください。

【現在の文章】
{base_text}

【コンテキスト情報】
{context}

【要件】
1. 温かみのある語り口で、読者に語りかけるように書く
2. 具体的な情景描写を加える（色、音、香り、温度感など五感に訴える）
3. 日本の伝統文化や歴史的背景を自然に織り込む
4. 現代の生活との関わりも触れる
5. 文章量は元の1.5〜2倍程度に充実させる
6. 箇条書きではなく、自然な文章で
7. HTMLタグは使わず、プレーンテキストで出力

充実させた文章のみを出力してください。前置きや説明は不要です。"""

        try:
            response = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 1000
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return text.strip()
            
            print(f"Gemini API警告: {section_name} - ステータス{response.status_code}")
            return base_text
            
        except Exception as e:
            print(f"Gemini API エラー: {section_name} - {str(e)}")
            return base_text


class WarmCalendarGenerator:
    """温かみのある暦情報生成（Gemini連携版）"""
    
    def __init__(self, target_date=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.month = self.date.month
        self.day = self.date.day
        self.gemini = GeminiEnhancer()
    
    def get_base_data(self):
        """基本データ取得"""
        return {
            'lunar': AccurateLunarCalendar.calculate_lunar_date(self.date),
            'sekki': SolarTermCalculator.get_current_sekki(self.date),
            'kou': SolarTermCalculator.get_kou_info(self.date)
        }
    
    def get_context_info(self):
        """コンテキスト情報（Geminiに渡す）"""
        base = self.get_base_data()
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return f"""
日付: {self.date.year}年{self.date.month}月{self.date.day}日（{weekdays[self.date.weekday()]}）
旧暦: {base['lunar']['month']}月{base['lunar']['day']}日
月齢: {base['lunar']['age']} ({base['lunar']['phase']})
二十四節気: {base['sekki'][0]}（{base['sekki'][1]}）
七十二候: {base['kou'][0]}（{base['kou'][1]}）
"""
    
    def enhance_seasonal_description(self, lunar, sekki, kou):
        """季節の移ろいの説明を充実"""
        lunar_names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
            7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        
        base_text = f"旧暦{lunar['month']}月は「{lunar_names[lunar['month']]}」。{lunar['phase']}の頃、{lunar['appearance']}。"
        
        enhanced = self.gemini.enhance_text(
            "季節の移ろい冒頭",
            base_text,
            self.get_context_info()
        )
        
        return enhanced
    
    def enhance_nature_changes(self):
        """自然の変化を充実"""
        base_changes = {
            1: "寒さが最も厳しく、池に氷が張り、梅のつぼみが膨らみ始めます。",
            2: "梅の花が咲き、鶯が鳴き、雪解けが始まります。",
            3: "桜が開花し、菜の花が咲き誇り、蝶が飛び始めます。",
            4: "新緑が美しく、ツバメが飛来し、筍が顔を出します。",
            5: "田植えが始まり、新緑が濃くなり、初鰹が旬を迎えます。",
            6: "梅雨入りし、紫陽花が咲き、蛍が飛び交います。",
            7: "梅雨明けし、セミが鳴き、入道雲が湧きます。",
            8: "残暑が厳しく、台風の季節、秋の気配を感じ始めます。",
            9: "稲刈りが始まり、赤とんぼが飛び、秋の七草が咲きます。",
            10: "紅葉が始まり、金木犀が香り、渡り鳥が南へ向かいます。",
            11: "紅葉が見頃を迎え、木枯らしが吹き、冬鳥が飛来します。",
            12: "霜柱が立ち、冬鳥が増え、干し柿づくりが盛んになります。"
        }
        
        base = base_changes.get(self.month, base_changes[12])
        
        enhanced = self.gemini.enhance_text(
            "自然の変化",
            base,
            self.get_context_info()
        )
        
        return enhanced
    
    def enhance_agricultural_info(self):
        """農事歴を充実"""
        base_agri = {
            1: "農閑期。農具の手入れ、藁細工、春の作付け計画を立てる時期です。",
            2: "春の準備期。種籾の準備、苗床づくり、畑の土起こしが始まります。",
            3: "春の農繁期開始。じゃがいもの植え付け、春野菜の種まきの時期です。",
            4: "本格的な農繁期。田植えの準備、畑では夏野菜の植え付けが始まります。",
            5: "田植えの最盛期。苗代から田んぼへ、家族総出の大切な農作業です。",
            6: "梅雨の農作業。田の草取り、梅の収穫、らっきょうの収穫時期です。",
            7: "夏の農作業。夏野菜の収穫、田んぼの水管理が重要な時期です。",
            8: "稲の開花・実りの準備期。台風対策、野菜の夏秋栽培が始まります。",
            9: "実りの秋。稲刈りが本格化し、秋野菜の植え付けも行います。",
            10: "収穫の最盛期。新米の脱穀、秋野菜の収穫、冬野菜の植え付けです。",
            11: "収穫終盤と冬支度。大根・白菜の収穫、漬物づくり、土づくりを行います。",
            12: "冬支度の完了期。最後の収穫、農具の整理、縄綯いなど室内作業です。"
        }
        
        base = base_agri.get(self.month, base_agri[12])
        
        enhanced = self.gemini.enhance_text(
            "農事歴",
            base,
            self.get_context_info()
        )
        
        return enhanced
    
    def enhance_customs(self):
        """風習・しきたりを充実"""
        base_customs = {
            1: "新年を迎え、初詣、七草粥、鏡開き、小正月など、一年の始まりの行事が続きます。",
            2: "節分で豆まきを行い、立春を迎えます。寒さの中にも春の気配を感じる月です。",
            3: "ひな祭りで女の子の成長を祝い、春分の日には彼岸の墓参りを行います。",
            4: "入学・入社の季節で、桜の開花とともに新しい生活が始まります。",
            5: "ゴールデンウィーク、端午の節句で男の子の成長を祝います。",
            6: "衣替え、梅雨入り、夏越の祓で半年の穢れを払います。",
            7: "七夕まつり、お盆の準備、各地で夏祭りが開催されます。",
            8: "お盆で先祖を迎え、送り火を焚きます。終戦記念日もあります。",
            9: "重陽の節句、十五夜、秋分の日の彼岸、収穫祭の季節です。",
            10: "神無月として知られ、出雲では神在祭、秋祭りの季節です。",
            11: "七五三、新嘗祭、冬囲いなど、冬支度の行事が行われます。",
            12: "一年の締めくくり。すす払い、正月飾りの準備、冬至の柚子湯、大晦日と続きます。"
        }
        
        base = base_customs.get(self.month, base_customs[12])
        
        enhanced = self.gemini.enhance_text(
            "風習・しきたり",
            base,
            self.get_context_info()
        )
        
        return enhanced
    
    def enhance_mythology(self):
        """神話・伝説を充実"""
        base_myth = {
            1: "睦月は新年の月。年神様が各家庭を訪れ、新しい年の幸福をもたらすと信じられています。",
            2: "如月は立春の月。春の女神が目覚め、大地に命を吹き込み始めます。",
            3: "弥生は桜の月。木花咲耶姫の伝説が思い起こされる、花と生命の季節です。",
            10: "神無月は神々の会議の月。出雲に集う八百万の神が、人々の縁を結びます。",
            11: "霜月は神々が出雲から戻る月。各地で神迎えの行事が行われます。",
            12: "師走は一年の終わり。大祓で穢れを払い、新年を迎える準備をします。"
        }
        
        base = base_myth.get(self.month, "この月にも様々な神話や伝説が伝わっています。")
        
        enhanced = self.gemini.enhance_text(
            "神話・伝説",
            base,
            self.get_context_info()
        )
        
        return enhanced
    
    def enhance_foods(self):
        """旬の食材情報を充実"""
        foods_data = {
            1: {'veg': '白菜、ネギ、小松菜、大根', 'fruit': 'みかん、金柑', 'fish': '鱈、寒ブリ、牡蠣'},
            2: {'veg': '白菜、ネギ、ブロッコリー', 'fruit': 'いちご、はっさく', 'fish': '鰆、わかめ、牡蠣'},
            3: {'veg': '菜の花、春キャベツ、新玉ねぎ', 'fruit': 'いちご、デコポン', 'fish': '桜鯛、ホタルイカ'},
            4: {'veg': '筍、新じゃがいも、アスパラガス', 'fruit': 'いちご、グレープフルーツ', 'fish': '初鰹、桜えび'},
            5: {'veg': '新玉ねぎ、そら豆、新生姜', 'fruit': 'さくらんぼ、メロン', 'fish': '初鰹、アジ'},
            6: {'veg': '梅、らっきょう、新生姜', 'fruit': 'さくらんぼ、びわ', 'fish': 'アジ、穴子'},
            7: {'veg': 'トマト、きゅうり、なす', 'fruit': '桃、スイカ', 'fish': '鰻、アジ、ハモ'},
            8: {'veg': 'トマト、きゅうり、オクラ', 'fruit': '桃、スイカ、ぶどう', 'fish': '鰹、アジ'},
            9: {'veg': 'さつまいも、里芋、松茸', 'fruit': 'ぶどう、梨、柿', 'fish': '秋刀魚、鰹'},
            10: {'veg': 'さつまいも、里芋、栗', 'fruit': '柿、りんご、梨', 'fish': '秋刀魚、鮭'},
            11: {'veg': '大根、白菜、春菊', 'fruit': '柿、みかん、りんご', 'fish': 'ブリ、鯖、牡蠣'},
            12: {'veg': '大根、白菜、春菊', 'fruit': 'みかん、りんご、柚子', 'fish': 'ブリ、牡蠣、鱈'}
        }
        
        data = foods_data.get(self.month, foods_data[12])
        base = f"この時期の旬の食材は、野菜では{data['veg']}、果物では{data['fruit']}、魚介では{data['fish']}などです。"
        
        enhanced = self.gemini.enhance_text(
            "旬の食材",
            base,
            self.get_context_info()
        )
        
        return enhanced
    
    def generate_full_html(self):
        """完全版HTML生成（Gemini連携）"""
        print("Gemini APIで文章を充実させています...")
        
        base = self.get_base_data()
        lunar = base['lunar']
        sekki = base['sekki']
        kou = base['kou']
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        lunar_names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
            7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        
        # Geminiで各セクションを充実
        seasonal_desc = self.enhance_seasonal_description(lunar, sekki, kou)
        nature_text = self.enhance_nature_changes()
        agri_text = self.enhance_agricultural_info()
        customs_text = self.enhance_customs()
        mythology_text = self.enhance_mythology()
        foods_text = self.enhance_foods()
        
        html = f"""
<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">📅 今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 24px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 15px 0 0 0; font-size: 20px;">旧暦: {lunar['month']}月{lunar['day']}日（{lunar_names[lunar['month']]}）</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 17px; opacity: 0.95; line-height: 1.7;">{lunar['appearance']}</p>
</div>

<div style="background: #f7fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #4299e1; margin-bottom: 35px;">
<p style="margin: 0; line-height: 2; font-size: 16px;">{seasonal_desc}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #fc8181; padding-left: 15px;">☀️ 季節の移ろい</h3>

<div style="background: linear-gradient(to right, #fff5f5, transparent); border-left: 6px solid #fc8181; padding: 25px; margin-bottom: 25px; border-radius: 8px;">
<h4 style="color: #c53030; margin: 0 0 12px 0; font-size: 22px;">二十四節気: {sekki[0]}（{sekki[1]}）</h4>
<p style="margin: 0; color: #2d3748; line-height: 2; font-size: 16px;">{sekki[2]}</p>
</div>

<div style="background: linear-gradient(to right, #f0fff4, transparent); border-left: 6px solid #48bb78; padding: 25px; margin-bottom: 30px; border-radius: 8px;">
<h4 style="color: #2f855a; margin: 0 0 12px 0; font-size: 22px;">七十二候: {kou[0]}</h4>
<p style="margin: 8px 0; color: #2d3748; font-size: 15px;"><em>読み:</em> {kou[1]}</p>
<p style="margin: 12px 0 0 0; color: #2d3748; line-height: 2; font-size: 16px;">{kou[2]}</p>
</div>

<div style="background: #fffaf0; padding: 25px; border-radius: 10px; margin-bottom: 30px; border: 2px solid #fbd38d;">
<h4 style="color: #c05621; margin: 0 0 15px 0; font-size: 20px;">自然の変化としては:</h4>
<p style="margin: 0; color: #2d3748; line-height: 2; font-size: 16px;">{nature_text}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #68d391; padding-left: 15px;">🚜 農事歴（農業暦）</h3>

<div style="background: linear-gradient(135deg, #fef5e7, #fef3c7); padding: 28px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
<p style="margin: 0; color: #744210; line-height: 2; font-size: 16px;">{agri_text}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #9f7aea; padding-left: 15px;">🏡 日本の風習・しきたり</h3>

<div style="background: #faf5ff; padding: 28px; border-radius: 12px; border-left: 6px solid #9f7aea; margin-bottom: 30px;">
<p style="margin: 0; line-height: 2; color: #2d3748; font-size: 16px;">{customs_text}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #ed64a6; padding-left: 15px;">📚 日本の神話・伝説</h3>

<div style="background: linear-gradient(135deg, #fef5f8, #fce7f3); padding: 28px; border-radius: 12px; margin-bottom: 30px; border: 2px solid #f9a8d4;">
<p style="margin: 0; color: #831843; line-height: 2; font-size: 16px;">{mythology_text}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f56565; padding-left: 15px;">🍴 旬の食材・行事食</h3>

<div style="background: linear-gradient(135deg, #fff5f5, #fed7d7); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<p style="margin: 0; color: #742a2a; line-height: 2; font-size: 16px;">{foods_text}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 30px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
<p style="margin: 0; font-size: 18px; color: #14532d; font-weight: 500; line-height: 2;">
季節を感じながら、今日も良い一日をお過ごしください
</p>
</div>

</div>
"""
        
        return {
            'title': f'{self.date.year}年{self.date.month}月{self.date.day}日({weekday})の暦情報',
            'content': html,
            'labels': ['暦', '二十四節気', '旧暦', '季節', '七十二候', '農事歴', '風習', '伝統文化']
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
            
            print(f"✅ 投稿成功: {response.get('url')}")
            return response
            
        except Exception as e:
            print(f"❌ 投稿エラー: {str(e)}")
            raise


def main():
    """メイン処理"""
    try:
        blog_id = os.environ.get('BLOG_ID')
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        print("=" * 70)
        print("🌸 暦情報自動投稿システム（Gemini連携版）起動")
        print("=" * 70)
        print(f"投稿日時: {datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')}")
        
        # 暦情報生成（Geminiで文章充実）
        print("\n📝 Gemini APIで温かみのある文章を生成中...")
        print("   - 季節の移ろい")
        print("   - 自然の変化")
        print("   - 農事歴")
        print("   - 風習・しきたり")
        print("   - 神話・伝説")
        print("   - 旬の食材")
        
        generator = WarmCalendarGenerator()
        post_data = generator.generate_full_html()
        
        print(f"\n✨ 生成完了")
        print(f"タイトル: {post_data['title']}")
        print(f"推定文字数: 約{len(post_data['content'])}文字")
        
        # Blogger投稿
        print("\n📤 Bloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 70)
        print("🎉 すべての処理が完了しました！")
        print("温かみのある暦情報が投稿されました")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
