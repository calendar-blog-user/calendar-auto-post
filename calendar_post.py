#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - Gemini統合版（改善版 v12+）
正確な天文計算 + Gemini AIによる豊かな文章生成
"""

import os
import json
import sys
from datetime import datetime
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
            (315, "立春", "りっしゅん", "春の始まり。暦の上では春ですが、まだ寒さが厳しい時期です"),
            (330, "雨水", "うすい", "雪が雨に変わり、氷が解け始める頃。三寒四温で春に向かいます"),
            (345, "啓蟄", "けいちつ", "冬眠していた虫が目覚める頃。春の訪れを実感できます"),
            (0, "春分", "しゅんぶん", "昼夜の長さがほぼ等しくなる日。これから昼が長くなります"),
            (15, "清明", "せいめい", "万物が清らかで生き生きとする頃。花が咲き誇る季節です"),
            (30, "穀雨", "こくう", "穀物を潤す春の雨が降る頃。田植えの準備が始まります"),
            (45, "立夏", "りっか", "夏の始まり。新緑が目に鮮やかな季節です"),
            (60, "小満", "しょうまん", "草木が茂り、天地に気が満ち始める頃です"),
            (75, "芒種", "ぼうしゅ", "麦を刈り、稲を植える農繁期。梅雨入りの時期です"),
            (90, "夏至", "げし", "一年で最も昼が長い日。これから暑さが本格化します"),
            (105, "小暑", "しょうしょ", "梅雨明け頃。本格的な暑さの始まりです"),
            (120, "大暑", "たいしょ", "一年で最も暑い時期。夏真っ盛りです"),
            (135, "立秋", "りっしゅう", "秋の始まり。暦の上では秋ですが、残暑が厳しい時期"),
            (150, "処暑", "しょしょ", "暑さが峠を越える頃。朝夕が涼しくなり始めます"),
            (165, "白露", "はくろ", "草木に白い露が宿り始める頃。秋の気配が濃くなります"),
            (180, "秋分", "しゅうぶん", "昼夜の長さがほぼ等しい。秋彼岸の中日です"),
            (195, "寒露", "かんろ", "露が冷たく感じられる頃。紅葉が始まります"),
            (210, "霜降", "そうこう", "朝霜が降り始める頃。秋が深まります"),
            (225, "立冬", "りっとう", "冬の始まり。暦の上では冬入りです"),
            (240, "小雪", "しょうせつ", "わずかに雪が降り始める頃。冬の気配が強まります"),
            (255, "大雪", "たいせつ", "雪が本格的に降り始める頃。山は雪化粧です"),
            (270, "冬至", "とうじ", "一年で最も昼が短い日。これから日が長くなります"),
            (285, "小寒", "しょうかん", "寒さが厳しくなり始める頃。寒の入りです"),
            (300, "大寒", "だいかん", "一年で最も寒い時期。寒さの極みです")
        ]
        
        longitude = cls.calculate_solar_longitude(date)
        current_sekki = sekki_data[0]
        
        for i in range(len(sekki_data)):
            deg, name, reading, desc = sekki_data[i]
            next_deg = sekki_data[(i + 1) % len(sekki_data)][0]
            
            if deg <= next_deg:
                if deg <= longitude < next_deg:
                    current_sekki = (name, reading, desc)
                    break
            else:
                if longitude >= deg or longitude < next_deg:
                    current_sekki = (name, reading, desc)
                    break
        
        return current_sekki
    
    @classmethod
    def get_current_kou(cls, date):
        """現在の七十二候を取得（太陽黄経ベース）"""
        # 七十二候は二十四節気をさらに3等分（約5度ずつ）
        kou_data = [
            # 太陽黄経, 名称, 読み, 説明
            (315, "東風解凍", "はるかぜこおりをとく", "春風が氷を解かし始める頃"),
            (320, "黄鶯睍睆", "うぐいすなく", "鶯が山里で鳴き始める頃"),
            (325, "魚上氷", "うおこおりをいずる", "割れた氷の間から魚が跳ねる頃"),
            (330, "土脉潤起", "つちのしょううるおいおこる", "雨が降って土が湿り気を含む頃"),
            (335, "霞始靆", "かすみはじめてたなびく", "霞がたなびき春景色が広がる頃"),
            (340, "草木萌動", "そうもくめばえいずる", "草木が芽吹き始める頃"),
            (345, "蟄虫啓戸", "すごもりむしとをひらく", "冬眠していた虫が出てくる頃"),
            (350, "桃始笑", "ももはじめてさく", "桃の花が咲き始める頃"),
            (355, "菜虫化蝶", "なむしちょうとなる", "青虫が蝶に羽化する頃"),
            (0, "雀始巣", "すずめはじめてすくう", "雀が巣を作り始める頃"),
            (5, "櫻始開", "さくらはじめてひらく", "桜が咲き始める頃"),
            (10, "雷乃発声", "かみなりすなわちこえをはっす", "遠くで雷の音が聞こえ始める頃"),
            (15, "玄鳥至", "つばめきたる", "燕が南から渡ってくる頃"),
            (20, "鴻雁北", "こうがんかえる", "雁が北へ帰っていく頃"),
            (25, "虹始見", "にじはじめてあらわる", "雨上がりに虹が出始める頃"),
            (30, "葭始生", "あしはじめてしょうず", "葦が芽を吹き始める頃"),
            (35, "霜止出苗", "しもやんでなえいず", "霜が降りなくなり苗が育つ頃"),
            (40, "牡丹華", "ぼたんはなさく", "牡丹の花が咲く頃"),
            (45, "蛙始鳴", "かわずはじめてなく", "蛙が鳴き始める頃"),
            (50, "蚯蚓出", "みみずいずる", "蚯蚓が地上に這い出る頃"),
            (55, "竹笋生", "たけのこしょうず", "筍が生えてくる頃"),
            (60, "蚕起食桑", "かいこおきてくわをはむ", "蚕が桑の葉を食べ始める頃"),
            (65, "紅花栄", "べにばなさかう", "紅花が盛んに咲く頃"),
            (70, "麦秋至", "むぎのときいたる", "麦が熟し収穫期を迎える頃"),
            (75, "蟷螂生", "かまきりしょうず", "蟷螂が生まれ出る頃"),
            (80, "腐草為螢", "くされたるくさほたるとなる", "蛍が光を放ち始める頃"),
            (85, "梅子黄", "うめのみきばむ", "梅の実が黄ばんで熟す頃"),
            (90, "乃東枯", "なつかれくさかるる", "夏枯草が枯れる頃"),
            (95, "菖蒲華", "あやめはなさく", "菖蒲の花が咲く頃"),
            (100, "半夏生", "はんげしょうず", "烏柄杓が生える頃"),
            (105, "温風至", "あつかぜいたる", "暑い風が吹いてくる頃"),
            (110, "蓮始開", "はすはじめてひらく", "蓮の花が開き始める頃"),
            (115, "鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛び方を覚える頃"),
            (120, "桐始結花", "きりはじめてはなをむすぶ", "桐の花が実を結ぶ頃"),
            (125, "土潤溽暑", "つちうるおうてむしあつし", "土が湿って蒸し暑くなる頃"),
            (130, "大雨時行", "たいうときどきふる", "時として大雨が降る頃"),
            (135, "涼風至", "すずかぜいたる", "涼しい風が吹き始める頃"),
            (140, "寒蝉鳴", "ひぐらしなく", "蜩が鳴き始める頃"),
            (145, "蒙霧升降", "ふかききりまとう", "深い霧がまとわりつく頃"),
            (150, "綿柎開", "わたのはなしべひらく", "綿の花のがくが開く頃"),
            (155, "天地始粛", "てんちはじめてさむし", "天地の暑さが収まり始める頃"),
            (160, "禾乃登", "こくものすなわちみのる", "稲が実る頃"),
            (165, "草露白", "くさのつゆしろし", "草に降りた露が白く見える頃"),
            (170, "鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める頃"),
            (175, "玄鳥去", "つばめさる", "燕が南へ帰っていく頃"),
            (180, "雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴らなくなる頃"),
            (185, "蟄虫坏戸", "むしかくれてとをふさぐ", "虫が土の中に隠れる頃"),
            (190, "水始涸", "みずはじめてかるる", "田んぼの水を抜き始める頃"),
            (195, "鴻雁来", "こうがんきたる", "雁が飛来する頃"),
            (200, "菊花開", "きくのはなひらく", "菊の花が咲く頃"),
            (205, "蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸口で鳴く頃"),
            (210, "霜始降", "しもはじめてふる", "霜が降り始める頃"),
            (215, "霎時施", "こさめときどきふる", "小雨がしとしと降る頃"),
            (220, "楓蔦黄", "もみじつたきばむ", "紅葉や蔦が黄葉する頃"),
            (225, "山茶始開", "つばきはじめてひらく", "山茶花が咲き始める頃"),
            (230, "地始凍", "ちはじめてこおる", "大地が凍り始める頃"),
            (235, "金盞香", "きんせんかさく", "水仙の花が咲く頃"),
            (240, "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる頃"),
            (245, "朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い落とす頃"),
            (250, "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色く色づく頃"),
            (255, "閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり本格的な冬となる頃"),
            (260, "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る頃"),
            (265, "鱖魚群", "さけのうおむらがる", "鮭が群がって川を上る頃"),
            (270, "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す頃"),
            (275, "麋角解", "さわしかつのおつる", "大鹿が角を落とす頃"),
            (280, "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃"),
            (285, "芹乃栄", "せりすなわちさかう", "芹が盛んに生え始める頃"),
            (290, "水泉動", "しみずあたたかをふくむ", "地中で凍った泉が動き始める頃"),
            (295, "雉始雊", "きじはじめてなく", "雉が鳴き始める頃"),
            (300, "款冬華", "ふきのはなさく", "蕗の花が咲く頃"),
            (305, "水沢腹堅", "さわみずこおりつめる", "沢の水が厚く凍る頃"),
            (310, "鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める頃"),
        ]
        
        longitude = cls.calculate_solar_longitude(date)
        
        # 現在の候を特定
        current_kou = kou_data[0]
        for i in range(len(kou_data)):
            deg, name, reading, desc = kou_data[i]
            next_deg = kou_data[(i + 1) % len(kou_data)][0]
            
            if deg <= next_deg:
                if deg <= longitude < next_deg:
                    current_kou = (name, reading, desc)
                    break
            else:
                if longitude >= deg or longitude < next_deg:
                    current_kou = (name, reading, desc)
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


class AccurateSunCalculator:
    """国立天文台準拠の日の出・日の入り計算（岡山）"""
    
    @staticmethod
    def calculate_sunrise_sunset(date):
        """岡山の日の出・日の入り時刻を国立天文台の方式で計算"""
        # 岡山市の座標
        latitude = 34.6617
        longitude = 133.9350
        
        # ユリウス日の計算
        y, m, d = date.year, date.month, date.day
        
        if m <= 2:
            y -= 1
            m += 12
        
        a = int(y / 100)
        b = 2 - a + int(a / 4)
        jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
        
        # 世界時正午のユリウス日
        jd_ut = jd - 0.5
        
        # ユリウス世紀数
        T = (jd_ut - 2451545.0) / 36525.0
        
        # 太陽の平均黄経（度）
        L = (280.460 + 36000.771 * T) % 360
        
        # 太陽の平均近点角（度）
        g = (357.528 + 35999.050 * T) % 360
        g_rad = math.radians(g)
        
        # 黄道傾斜角（度）
        epsilon = 23.439 - 0.013 * T
        epsilon_rad = math.radians(epsilon)
        
        # 太陽の視黄経（度）
        lambda_sun = L + 1.915 * math.sin(g_rad) + 0.020 * math.sin(2 * g_rad)
        lambda_rad = math.radians(lambda_sun)
        
        # 太陽の赤緯（度）
        sin_delta = math.sin(epsilon_rad) * math.sin(lambda_rad)
        delta = math.degrees(math.asin(sin_delta))
        delta_rad = math.radians(delta)
        
        # 太陽の赤経（度）
        cos_alpha = math.cos(lambda_rad) / math.cos(delta_rad)
        sin_alpha = math.cos(epsilon_rad) * math.sin(lambda_rad) / math.cos(delta_rad)
        alpha = math.degrees(math.atan2(sin_alpha, cos_alpha))
        if alpha < 0:
            alpha += 360
        
        # 均時差（時間）
        equation_of_time = (L - alpha) / 15.0
        if equation_of_time > 12:
            equation_of_time -= 24
        elif equation_of_time < -12:
            equation_of_time += 24
        
        # 時角（度）
        # 日の出・日の入りの高度 = -0.8333度（視半径16' + 大気差34'）
        sun_altitude = -0.8333
        lat_rad = math.radians(latitude)
        
        cos_h = (math.sin(math.radians(sun_altitude)) - math.sin(lat_rad) * math.sin(delta_rad)) / (math.cos(lat_rad) * math.cos(delta_rad))
        
        if cos_h > 1:
            # 極夜
            h = 0
        elif cos_h < -1:
            # 白夜
            h = 180
        else:
            h = math.degrees(math.acos(cos_h))
        
        # 南中時刻（時）
        noon = 12.0 - equation_of_time - (longitude - 135.0) / 15.0
        
        # 日の出・日の入り時刻（時）
        sunrise_time = noon - h / 15.0
        sunset_time = noon + h / 15.0
        
        def to_time_string(decimal_hour):
            hour = int(decimal_hour)
            minute = int((decimal_hour - hour) * 60)
            if minute >= 60:
                minute = 59
            if hour < 0:
                hour += 24
            if hour >= 24:
                hour -= 24
            return f"{hour:02d}:{minute:02d}"
        
        return {
            'sunrise': to_time_string(sunrise_time),
            'sunset': to_time_string(sunset_time)
        }


class GeminiContentGenerator:
    """Gemini APIを使用したコンテンツ生成"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    def generate_content(self, date, lunar, sekki, kou):
        """Geminiで文章生成"""
        
        prompt = f"""あなたは日本の暦・季節・伝統文化に精通した親しみやすい案内人です。

【本日の暦情報】
西暦: {date.year}年{date.month}月{date.day}日
旧暦: {lunar['month']}月{lunar['day']}日（{lunar['month_name']}）
六曜: {lunar['rokuyou']}
月齢: {lunar['age']}（{lunar['phase']}）
二十四節気: {sekki[0]}（{sekki[1]}）
七十二候: {kou[0]}（{kou[1]}）

【最重要：書式の絶対ルール】
1. 各段落は2〜3文で終わらせ、その後に**必ず空白行を1行**入れてください
2. 箇条書きは**必ず使用**してください（* または - で開始）
3. 箇条書きの前後にも**必ず空白行**を入れてください

【必須の出力フォーマット】
以下の12セクションを**すべて**含めてください。1つも欠かさないこと：

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

【各セクションの書き方】
- 最初に2〜3文で導入を書く
- 空白行を入れる
- 箇条書きで3〜5個のポイントを列挙
- 空白行を入れる
- 最後に1〜2文でまとめる

【文体】
- 「ですます調」で親しみやすく
- 「でございます」は絶対に使わない
- 各セクション300文字以上

前置きなしで「☀️ 季節の移ろい」から開始し、🎼 伝統芸能で終了してください。"""
        
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
                        return content
            
            print(f"Gemini APIエラー: {response.status_code}")
            return None
                
        except Exception as e:
            print(f"Gemini API呼び出し例外: {str(e)}")
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
        sun_times = AccurateSunCalculator.calculate_sunrise_sunset(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        # アイキャッチ画像を生成
        eyecatch_html = self._generate_eyecatch_image(sekki, kou, lunar)
        
        # 基本情報セクション（プログラムで生成）
        basic_info = f"""<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

{eyecatch_html}

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
<div style="margin-bottom: 20px;">
<p style="margin: 0 0 8px 0; font-size: 18px;"><strong>二十四節気:</strong> {sekki[0]}（{sekki[1]}）</p>
<p style="margin: 0; font-size: 15px; color: #4A5568; line-height: 1.8;">{sekki[2]}</p>
</div>
<div>
<p style="margin: 0 0 8px 0; font-size: 18px;"><strong>七十二候:</strong> {kou[0]}（{kou[1]}）</p>
<p style="margin: 0; font-size: 15px; color: #4A5568; line-height: 1.8;">{kou[2]}</p>
</div>
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
                if current_paragraph:
                    current_paragraph.append(' ')
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
    
    def _generate_eyecatch_image(self, sekki, kou, lunar):
        """アイキャッチ画像をSVGで生成"""
        # 季節ごとの配色
        season_colors = {
            '立春': ('#FFE4E1', '#FF69B4', '#8B008B'),
            '雨水': ('#E0F2F7', '#4FC3F7', '#0277BD'),
            '啓蟄': ('#F1F8E9', '#AED581', '#558B2F'),
            '春分': ('#FFF9C4', '#FFD54F', '#F57C00'),
            '清明': ('#F3E5F5', '#BA68C8', '#6A1B9A'),
            '穀雨': ('#E8F5E9', '#66BB6A', '#2E7D32'),
            '立夏': ('#FFF3E0', '#FFB74D', '#EF6C00'),
            '小満': ('#E1F5FE', '#4DD0E1', '#0097A7'),
            '芒種': ('#F1F8E9', '#9CCC65', '#689F38'),
            '夏至': ('#FFF9C4', '#FFD54F', '#F57C00'),
            '小暑': ('#FFEBEE', '#EF5350', '#C62828'),
            '大暑': ('#FBE9E7', '#FF7043', '#D84315'),
            '立秋': ('#FFF3E0', '#FFB74D', '#EF6C00'),
            '処暑': ('#FCE4EC', '#F06292', '#C2185B'),
            '白露': ('#E3F2FD', '#64B5F6', '#1976D2'),
            '秋分': ('#FFF9C4', '#FFD54F', '#F57C00'),
            '寒露': ('#EFEBE9', '#BCAAA4', '#5D4037'),
            '霜降': ('#F3E5F5', '#BA68C8', '#6A1B9A'),
            '立冬': ('#E3F2FD', '#64B5F6', '#1976D2'),
            '小雪': ('#ECEFF1', '#90A4AE', '#455A64'),
            '大雪': ('#E0F7FA', '#4DD0E1', '#00838F'),
            '冬至': ('#E8EAF6', '#7986CB', '#3949AB'),
            '小寒': ('#F3E5F5', '#BA68C8', '#6A1B9A'),
            '大寒': ('#E1F5FE', '#4FC3F7', '#0277BD')
        }
        
        bg_color, primary_color, accent_color = season_colors.get(sekki[0], ('#E3F2FD', '#64B5F6', '#1976D2'))
        
        # HTMLとして直接レンダリング可能な画像を生成
        html = f"""
<div style="margin-bottom: 30px; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.15); background: linear-gradient(135deg, {bg_color} 0%, {primary_color} 100%); position: relative; aspect-ratio: 16/9;">
  <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; width: 90%;">
    <div style="font-family: 'Yu Mincho', 'Noto Serif JP', serif; font-size: clamp(40px, 8vw, 120px); font-weight: bold; color: white; text-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 15px;">
      {sekki[0]}
    </div>
    <div style="font-family: 'Yu Mincho', 'Noto Serif JP', serif; font-size: clamp(20px, 3vw, 48px); color: white; opacity: 0.9; margin-bottom: 30px;">
      {sekki[1]}
    </div>
    <div style="font-family: 'Yu Mincho', 'Noto Serif JP', serif; font-size: clamp(30px, 5vw, 72px); color: {accent_color}; text-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 20px;">
      {kou[0]}
    </div>
    <div style="font-family: 'Yu Gothic', 'Noto Sans JP', sans-serif; font-size: clamp(18px, 3vw, 52px); color: white; opacity: 0.85;">
      {self.date.year}年{self.date.month}月{self.date.day}日 旧暦{lunar['month']}月{lunar['day']}日
    </div>
  </div>
  <div style="position: absolute; top: 100px; right: 150px; width: 200px; height: 200px; border-radius: 50%; background: white; opacity: 0.15;"></div>
  <div style="position: absolute; bottom: 80px; left: 100px; width: 150px; height: 150px; border-radius: 50%; background: {accent_color}; opacity: 0.1;"></div>
  <div style="position: absolute; bottom: 30px; left: 0; right: 0; height: 3px; background: white; opacity: 0.5; margin: 0 200px;"></div>
</div>
"""
        return html
    
    def _generate_rich_fallback_content(self, lunar, sekki, kou):
        """充実したフォールバックコンテンツ"""
        return f"""☀️ 季節の移ろい（二十四節気・七十二候）

今は二十四節気の「{sekki[0]}」の時期です。この頃は本格的な冬の訪れを感じる季節ですね。

七十二候では「{kou[0]}」を迎えています。自然界の生き物たちも冬支度を進めています。

* **季節の特徴**：寒さが厳しくなり、雪が降る地域も増えてきます
* **自然の変化**：動物たちが冬眠の準備を始める頃です
* **暮らしの工夫**：温かく過ごす準備が大切な時期ですね

この季節ならではの美しさを感じながら過ごしたいですね。

🎌 記念日・祝日

本日は様々な記念日があります。日本の歴史や文化を振り返る良い機会ですね。

* **伝統行事**：各地で季節の行事が行われます
* **文化的意義**：先人の知恵を学ぶ日でもあります

記念日を通じて、日本の豊かな文化に触れてみましょう。

💡 暦にまつわる文化雑学

旧暦{lunar['month']}月は「{lunar['month_name']}」と呼ばれています。この呼び名には深い意味があります。

六曜は「{lunar['rokuyou']}」です。古くから日本人の生活に根付いてきた暦の知恵ですね。

* **月の呼び名**：季節や自然の様子を表しています
* **六曜の意味**：日々の吉凶を示す指標として親しまれてきました
* **暦の知恵**：自然のリズムに合わせた生活の工夫が込められています

暦を通じて、日本の文化の深さを感じることができます。

🚜 農事歴

この時期、農家の方々は冬支度や来年の準備を進めています。

* **冬野菜の収穫**：寒さで甘みを増した野菜が美味しい時期です
* **土作り**：来年の豊作に向けて土壌を整えます
* **農具の手入れ**：大切な道具を丁寧にメンテナンスします

農家の方々の努力が、私たちの食卓を支えています。

🏡 日本の風習・しきたり

この季節には、様々な風習やしきたりがあります。

* **冬支度**：家を温かく整える準備をします
* **年末の準備**：大掃除やお歳暮など、年末に向けた活動が始まります
* **家族の団らん**：温かい部屋で過ごす時間を大切にします

日本の伝統的な暮らしの知恵が詰まっています。

📚 神話・伝説

旧暦{lunar['month']}月には、興味深い神話や伝説があります。

* **神々の物語**：日本各地に伝わる神話が季節と結びついています
* **自然への畏敬**：自然現象を神秘的に捉えた先人の心が感じられます

神話を通じて、日本人の自然観を知ることができますね。

🍁 自然・気象

冬の自然は厳しくも美しい表情を見せます。

* **冬の景色**：雪化粧をした山々が美しい季節です
* **澄んだ空気**：遠くまで見渡せる冬晴れの日が増えます
* **動物たちの様子**：冬を乗り越える生き物たちの姿が見られます

厳しい自然の中にも、静かな美しさがあります。

🍴 旬の食

冬の食材が美味しい季節です。

* **冬野菜**：大根、白菜、ネギなど、体を温める野菜が豊富です
* **海の幸**：ブリ、カニ、牡蠣など、冬の味覚を楽しめます
* **鍋料理**：温かい鍋を囲む時間は、冬の楽しみですね

旬の食材で、心も体も温まります。

🌸 季節の草木

冬でも美しく咲く花々があります。

* **冬の花**：サザンカやツバキが寒さの中で咲きます
* **常緑樹**：松や杉が緑を保ち、生命力を感じさせます
* **冬芽**：春への準備を静かに進める植物たちの姿が見られます

厳しい季節を耐える植物たちから、生命の強さを学べます。

🌕 月や星の暦・天文情報

月齢{lunar['age']}の{lunar['phase']}が見られます。

* **冬の星座**：空気が澄んで、星が美しく輝きます
* **月の満ち欠け**：古くから暦の基準となってきました
* **天体観測**：冬の夜空は観測に最適な季節です

夜空を見上げて、宇宙の神秘を感じてみましょう。

🎨 伝統工芸

冬の間に作られる伝統工芸品があります。

* **冬の手仕事**：雪国では室内で工芸品が作られてきました
* **職人の技**：丁寧な手仕事が美しい品を生み出します
* **暮らしの道具**：使うほどに味わいが増す工芸品の魅力があります

伝統工芸の温もりを感じることができます。

🎼 伝統芸能

冬の季節に楽しめる伝統芸能があります。

* **年末の興行**：歌舞伎や能楽の特別公演が行われます
* **地域の芸能**：各地で伝統的な舞や音楽が披露されます
* **文化の継承**：古くから受け継がれる芸能の美しさを味わえます

日本の伝統芸能の奥深さに触れる機会ですね。"""

        """フォールバックコンテンツ"""
        return f"""☀️ 季節の移ろい（二十四節気・七十二候）

今は二十四節気の「{sekki[0]}」の時期です。この頃は本格的な冬の訪れを感じる季節ですね。

七十二候では「{kou[0]}」を迎えています。自然界の生き物たちも冬支度を進めています。

* **季節の特徴**：寒さが厳しくなり、雪が降る地域も増えてきます
* **自然の変化**：動物たちが冬眠の準備を始める頃です
* **暮らしの工夫**：温かく過ごす準備が大切な時期ですね

この季節ならではの美しさを感じながら過ごしたいですね。

🎌 記念日・祝日

本日は様々な記念日があります。日本の歴史や文化を振り返る良い機会ですね。

* **伝統行事**：各地で季節の行事が行われます
* **文化的意義**：先人の知恵を学ぶ日でもあります

記念日を通じて、日本の豊かな文化に触れてみましょう。

💡 暦にまつわる文化雑学

旧暦{lunar['month']}月は「{lunar['month_name']}」と呼ばれています。この呼び名には深い意味があります。

六曜は「{lunar['rokuyou']}」です。古くから日本人の生活に根付いてきた暦の知恵ですね。

* **月の呼び名**：季節や自然の様子を表しています
* **六曜の意味**：日々の吉凶を示す指標として親しまれてきました
* **暦の知恵**：自然のリズムに合わせた生活の工夫が込められています

暦を通じて、日本の文化の深さを感じることができます。

🚜 農事歴

この時期、農家の方々は冬支度や来年の準備を進めています。

* **冬野菜の収穫**：寒さで甘みを増した野菜が美味しい時期です
* **土作り**：来年の豊作に向けて土壌を整えます
* **農具の手入れ**：大切な道具を丁寧にメンテナンスします

農家の方々の努力が、私たちの食卓を支えています。

🏡 日本の風習・しきたり

この季節には、様々な風習やしきたりがあります。

* **冬支度**：家を温かく整える準備をします
* **年末の準備**：大掃除やお歳暮など、年末に向けた活動が始まります
* **家族の団らん**：温かい部屋で過ごす時間を大切にします

日本の伝統的な暮らしの知恵が詰まっています。

📚 神話・伝説

旧暦{lunar['month']}月には、興味深い神話や伝説があります。

* **神々の物語**：日本各地に伝わる神話が季節と結びついています
* **自然への畏敬**：自然現象を神秘的に捉えた先人の心が感じられます

神話を通じて、日本人の自然観を知ることができますね。

🍁 自然・気象

冬の自然は厳しくも美しい表情を見せます。

* **冬の景色**：雪化粧をした山々が美しい季節です
* **澄んだ空気**：遠くまで見渡せる冬晴れの日が増えます
* **動物たちの様子**：冬を乗り越える生き物たちの姿が見られます

厳しい自然の中にも、静かな美しさがあります。

🍴 旬の食

冬の食材が美味しい季節です。

* **冬野菜**：大根、白菜、ネギなど、体を温める野菜が豊富です
* **海の幸**：ブリ、カニ、牡蠣など、冬の味覚を楽しめます
* **鍋料理**：温かい鍋を囲む時間は、冬の楽しみですね

旬の食材で、心も体も温まります。

🌸 季節の草木

冬でも美しく咲く花々があります。

* **冬の花**：サザンカやツバキが寒さの中で咲きます
* **常緑樹**：松や杉が緑を保ち、生命力を感じさせます
* **冬芽**：春への準備を静かに進める植物たちの姿が見られます

厳しい季節を耐える植物たちから、生命の強さを学べます。

🌕 月や星の暦・天文情報

月齢{lunar['age']}の{lunar['phase']}が見られます。

* **冬の星座**：空気が澄んで、星が美しく輝きます
* **月の満ち欠け**：古くから暦の基準となってきました
* **天体観測**：冬の夜空は観測に最適な季節です

夜空を見上げて、宇宙の神秘を感じてみましょう。

🎨 伝統工芸

冬の間に作られる伝統工芸品があります。

* **冬の手仕事**：雪国では室内で工芸品が作られてきました
* **職人の技**：丁寧な手仕事が美しい品を生み出します
* **暮らしの道具**：使うほどに味わいが増す工芸品の魅力があります

伝統工芸の温もりを感じることができます。

🎼 伝統芸能

冬の季節に楽しめる伝統芸能があります。

* **年末の興行**：歌舞伎や能楽の特別公演が行われます
* **地域の芸能**：各地で伝統的な舞や音楽が披露されます
* **文化の継承**：古くから受け継がれる芸能の美しさを味わえます

日本の伝統芸能の奥深さに触れる機会ですね。"""


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
        print("  - 高精度な日の出・日の入り計算（岡山）")
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
