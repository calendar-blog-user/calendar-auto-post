#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - 365日毎日違う内容を自動生成
毎日決まった時間に暦情報をBloggerに自動投稿
"""

import os
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
import math
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# スコープ設定
SCOPES = ['https://www.googleapis.com/auth/blogger']

class CalendarGenerator:
    """暦情報生成クラス - 365日毎日異なる内容を生成"""
    
    def __init__(self, target_date=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        # 引数で日付指定がなければ今日の日付を使用
        self.target_date = target_date or datetime.now(self.jst)
        
    def get_lunar_calendar(self):
        """旧暦を計算 - 毎日変わります"""
        year = self.target_date.year
        month = self.target_date.month
        day = self.target_date.day
        
        # 新月の基準日（2000年1月6日）
        base_date = datetime(2000, 1, 6, tzinfo=self.jst)
        days_since = (self.target_date - base_date).days
        
        # 月齢を計算（朔望月周期: 29.530588853日）
        moon_age = days_since % 29.530588853
        
        # 旧暦の月を計算（簡易版）
        lunar_offset = -1 if month <= 2 else 0
        lunar_month = ((month + 9 + lunar_offset) % 12) or 12
        
        # 旧暦の日を月齢から推定
        lunar_day = int(moon_age) + 1
        if lunar_day > 30:
            lunar_day = 1
            lunar_month = (lunar_month % 12) + 1
        
        # 月の名前を決定
        moon_phase_names = {
            range(0, 2): "新月",
            range(2, 3): "二日月",
            range(3, 4): "三日月", 
            range(4, 7): "上弦へ向かう月",
            range(7, 9): "上弦の月",
            range(9, 13): "十三夜月",
            range(13, 16): "満月",
            range(16, 18): "十六夜",
            range(18, 23): "下弦へ向かう月",
            range(23, 24): "下弦の月",
            range(24, 29): "晦日月"
        }
        
        moon_name = "新月"
        moon_age_int = int(moon_age)
        for age_range, name in moon_phase_names.items():
            if moon_age_int in age_range:
                moon_name = name
                break
        
        # 月の見え方の説明
        moon_descriptions = {
            range(0, 2): "夜空に月は見えません",
            range(2, 4): "夕方の西空に細い月",
            range(4, 8): "夕方から宵に弓なりの月",
            range(8, 14): "宵から夜半に膨らむ月",
            range(14, 16): "夜通し輝く丸い月",
            range(16, 23): "夜半から明け方に欠けていく月",
            range(23, 30): "明け方の東空に細い月"
        }
        
        moon_desc = "美しい月"
        for age_range, desc in moon_descriptions.items():
            if moon_age_int in age_range:
                moon_desc = desc
                break
        
        return {
            'lunar_month': lunar_month,
            'lunar_day': lunar_day,
            'moon_age': round(moon_age, 1),
            'moon_name': moon_name,
            'moon_description': moon_desc
        }
    
    def get_sekki_and_kou(self):
        """二十四節気と七十二候を取得 - 毎日正確に変わります"""
        month = self.target_date.month
        day = self.target_date.day
        
        # 二十四節気の定義（2025年基準）
        sekki_dates = [
            (1, 5, "小寒", "寒さが厳しくなり始める頃"),
            (1, 20, "大寒", "一年で最も寒い時期"),
            (2, 3, "立春", "春の始まり、暦の上では春"),
            (2, 18, "雨水", "雪が雨に変わり、氷が解け始める"),
            (3, 5, "啓蟄", "冬眠していた虫が目覚める"),
            (3, 20, "春分", "昼夜の長さがほぼ等しくなる"),
            (4, 4, "清明", "万物が清らかで生き生きする"),
            (4, 20, "穀雨", "穀物を育てる春の雨が降る"),
            (5, 5, "立夏", "夏の始まり、新緑が目に鮮やか"),
            (5, 21, "小満", "草木が茂り天地に満ち始める"),
            (6, 5, "芒種", "麦を刈り、稲を植える時期"),
            (6, 21, "夏至", "一年で最も昼が長い日"),
            (7, 7, "小暑", "梅雨明け頃、本格的な暑さの始まり"),
            (7, 22, "大暑", "一年で最も暑い時期"),
            (8, 7, "立秋", "秋の始まり、暦の上では秋"),
            (8, 23, "処暑", "暑さが峠を越え、朝夕が涼しく"),
            (9, 7, "白露", "草木に白い露が宿り始める"),
            (9, 23, "秋分", "昼夜の長さがほぼ等しくなる"),
            (10, 8, "寒露", "露が冷たく感じられる頃"),
            (10, 23, "霜降", "朝霜が降り始める頃"),
            (11, 7, "立冬", "冬の始まり、暦の上では冬"),
            (11, 22, "小雪", "わずかに雪が降り始める頃"),
            (12, 7, "大雪", "雪が本格的に降り始める"),
            (12, 21, "冬至", "一年で最も昼が短い日")
        ]
        
        # 現在の節気を探す
        current_sekki = None
        for m, d, name, desc in reversed(sekki_dates):
            if month > m or (month == m and day >= d):
                current_sekki = (name, desc)
                break
        if not current_sekki:
            current_sekki = sekki_dates[-1][2:]
        
        # 七十二候の定義（各節気を3つに分けた候）
        kou_dates = [
            (1, 5, "芹乃栄", "せりすなわちさかう", "芹が盛んに生え始める"),
            (1, 10, "水泉動", "しみずあたたかをふくむ", "地中で凍った泉が動き始める"),
            (1, 15, "雉始雊", "きじはじめてなく", "雉が鳴き始める"),
            (1, 20, "款冬華", "ふきのはなさく", "蕗の花が咲く"),
            (1, 25, "水沢腹堅", "さわみずこおりつめる", "沢の水が厚く凍る"),
            (1, 30, "鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める"),
            (2, 3, "東風解凍", "はるかぜこおりをとく", "春の風が氷を解かす"),
            (2, 8, "黄鶯睍睆", "うぐいすなく", "鶯が鳴き始める"),
            (2, 13, "魚上氷", "うおこおりをいずる", "魚が氷の下から現れる"),
            (2, 18, "土脉潤起", "つちのしょううるおいおこる", "雨が降って土が潤う"),
            (2, 23, "霞始靆", "かすみはじめてたなびく", "霞がたなびき始める"),
            (2, 28, "草木萌動", "そうもくめばえいずる", "草木が芽吹き始める"),
            (3, 5, "蟄虫啓戸", "すごもりむしとをひらく", "冬眠していた虫が出てくる"),
            (3, 10, "桃始笑", "ももはじめてさく", "桃の花が咲き始める"),
            (3, 15, "菜虫化蝶", "なむしちょうとなる", "青虫が蝶になる"),
            (3, 20, "雀始巣", "すずめはじめてすくう", "雀が巣を作り始める"),
            (3, 25, "櫻始開", "さくらはじめてひらく", "桜が咲き始める"),
            (3, 30, "雷乃発声", "かみなりすなわちこえをはっす", "遠くで雷の音が聞こえ始める"),
            (4, 4, "玄鳥至", "つばめきたる", "燕が南から渡ってくる"),
            (4, 9, "鴻雁北", "こうがんかえる", "雁が北へ帰る"),
            (4, 14, "虹始見", "にじはじめてあらわる", "雨上がりに虹が出始める"),
            (4, 20, "葭始生", "あしはじめてしょうず", "葦が芽を吹き始める"),
            (4, 25, "霜止出苗", "しもやんでなえいず", "霜が終わり苗が育つ"),
            (4, 30, "牡丹華", "ぼたんはなさく", "牡丹の花が咲く"),
            (5, 5, "蛙始鳴", "かわずはじめてなく", "蛙が鳴き始める"),
            (5, 10, "蚯蚓出", "みみずいずる", "蚯蚓が地上に出てくる"),
            (5, 15, "竹笋生", "たけのこしょうず", "筍が生えてくる"),
            (5, 21, "蚕起食桑", "かいこおきてくわをはむ", "蚕が桑の葉を盛んに食べる"),
            (5, 26, "紅花栄", "べにばなさかう", "紅花が盛んに咲く"),
            (5, 31, "麦秋至", "むぎのときいたる", "麦が熟し収穫期を迎える"),
            (6, 5, "蟷螂生", "かまきりしょうず", "蟷螂が生まれる"),
            (6, 10, "腐草為蛍", "くされたるくさほたるとなる", "蛍が光り始める"),
            (6, 16, "梅子黄", "うめのみきばむ", "梅の実が黄ばむ"),
            (6, 21, "乃東枯", "なつかれくさかるる", "夏枯草が枯れる"),
            (6, 26, "菖蒲華", "あやめはなさく", "菖蒲の花が咲く"),
            (7, 2, "半夏生", "はんげしょうず", "烏柄杓が生える"),
            (7, 7, "温風至", "あつかぜいたる", "暑い風が吹く"),
            (7, 12, "蓮始開", "はすはじめてひらく", "蓮の花が開き始める"),
            (7, 17, "鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛び方を学ぶ"),
            (7, 22, "桐始結花", "きりはじめてはなをむすぶ", "桐の花が実を結ぶ"),
            (7, 28, "土潤溽暑", "つちうるおうてむしあつし", "土が湿って蒸し暑い"),
            (8, 2, "大雨時行", "たいうときどきふる", "時として大雨が降る"),
            (8, 7, "涼風至", "すずかぜいたる", "涼しい風が吹き始める"),
            (8, 12, "寒蝉鳴", "ひぐらしなく", "蜩が鳴き始める"),
            (8, 17, "蒙霧升降", "ふかききりまとう", "深い霧がまとわりつく"),
            (8, 23, "綿柎開", "わたのはなしべひらく", "綿の花のがくが開く"),
            (8, 28, "天地始粛", "てんちはじめてさむし", "天地の暑さが収まり始める"),
            (9, 2, "禾乃登", "こくものすなわちみのる", "稲が実る"),
            (9, 7, "草露白", "くさのつゆしろし", "草に降りた露が白く見える"),
            (9, 12, "鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める"),
            (9, 17, "玄鳥去", "つばめさる", "燕が南へ帰る"),
            (9, 23, "雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴らなくなる"),
            (9, 28, "蟄虫坏戸", "むしかくれてとをふさぐ", "虫が土の中に隠れる"),
            (10, 3, "水始涸", "みずはじめてかるる", "田の水を抜き始める"),
            (10, 8, "鴻雁来", "こうがんきたる", "雁が渡ってくる"),
            (10, 13, "菊花開", "きくのはなひらく", "菊の花が咲く"),
            (10, 18, "蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸口で鳴く"),
            (10, 23, "霜始降", "しもはじめてふる", "霜が降り始める"),
            (10, 28, "霎時施", "こさめときどきふる", "小雨がしとしと降る"),
            (11, 2, "楓蔦黄", "もみじつたきばむ", "紅葉や蔦が黄葉する"),
            (11, 7, "山茶始開", "つばきはじめてひらく", "山茶花が咲き始める"),
            (11, 12, "地始凍", "ちはじめてこおる", "大地が凍り始める"),
            (11, 17, "金盞香", "きんせんかさく", "水仙の花が咲く"),
            (11, 22, "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い落とす"),
            (12, 2, "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色くなる"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり冬になる"),
            (12, 12, "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る"),
            (12, 16, "鱖魚群", "さけのうおむらがる", "鮭が群がって川を上る"),
            (12, 21, "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す"),
            (12, 26, "麋角解", "さわしかつのおつる", "大鹿が角を落とす"),
            (12, 31, "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す")
        ]
        
        # 現在の候を探す
        current_kou = None
        for m, d, name, reading, desc in reversed(kou_dates):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading, desc)
                break
        if not current_kou:
            current_kou = ("朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い落とす")
        
        return {
            'sekki': current_sekki,
            'kou': current_kou
        }
    
    def get_seasonal_info(self):
        """季節の情報を取得 - 月ごとに変わります"""
        month = self.target_date.month
        
        # 旬の食材（月ごと）
        seasonal_foods = {
            1: ["白菜", "ネギ", "小松菜", "大根", "みかん", "金柑", "鱈", "寒ブリ", "牡蠣"],
            2: ["白菜", "ネギ", "ブロッコリー", "カリフラワー", "いちご", "鰆", "わかめ"],
            3: ["菜の花", "春キャベツ", "新玉ねぎ", "アスパラガス", "いちご", "桜鯛", "ホタルイカ"],
            4: ["筍", "新じゃがいも", "春キャベツ", "そら豆", "いちご", "初鰹", "桜えび"],
            5: ["新玉ねぎ", "そら豆", "グリーンピース", "さくらんぼ", "メロン", "初鰹", "アジ"],
            6: ["梅", "らっきょう", "新生姜", "ズッキーニ", "さくらんぼ", "アジ", "穴子"],
            7: ["トマト", "きゅうり", "なす", "ピーマン", "桃", "スイカ", "鰻", "アジ"],
            8: ["トマト", "きゅうり", "なす", "オクラ", "桃", "ぶどう", "鰹", "太刀魚"],
            9: ["さつまいも", "里芋", "栗", "松茸", "ぶどう", "梨", "柿", "秋刀魚", "鮭"],
            10: ["さつまいも", "里芋", "栗", "松茸", "柿", "りんご", "秋刀魚", "鮭", "鯖"],
            11: ["大根", "白菜", "春菊", "ほうれん草", "柿", "みかん", "りんご", "ブリ", "牡蠣"],
            12: ["白菜", "ネギ", "ほうれん草", "かぶ", "みかん", "ゆず", "鱈", "鰤", "ふぐ"]
        }
        
        # 季節の花（月ごと）
        seasonal_flowers = {
            1: ("福寿草", "幸せを招く", "新春を告げる黄金の花"),
            2: ("梅", "高潔・忍耐", "早春に咲く香り高い花"),
            3: ("桜", "精神の美", "日本の春を代表する花"),
            4: ("藤", "歓迎・優しさ", "紫の花房が美しい"),
            5: ("牡丹", "富貴・高貴", "百花の王と呼ばれる花"),
            6: ("紫陽花", "移り気", "梅雨を彩る色変わりの花"),
            7: ("朝顔", "はかない恋", "夏の朝を飾る花"),
            8: ("向日葵", "憧れ", "太陽に向かって咲く夏の花"),
            9: ("彼岸花", "再会・情熱", "秋の彼岸に咲く真紅の花"),
            10: ("コスモス", "調和・謙虚", "秋風に揺れる可憐な花"),
            11: ("山茶花", "困難に打ち勝つ", "霜に負けずに咲く冬の花"),
            12: ("水仙", "自己愛・神秘", "清楚な香りの冬の花")
        }
        
        return {
            'foods': seasonal_foods.get(month, []),
            'flower': seasonal_flowers.get(month, ("山茶花", "困難に打ち勝つ", "冬の花"))
        }
    
    def generate_content(self):
        """ブログ投稿用のHTML形式コンテンツを生成 - 毎日違う内容"""
        lunar = self.get_lunar_calendar()
        sekki_kou = self.get_sekki_and_kou()
        seasonal = self.get_seasonal_info()
        
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekday_names[self.target_date.weekday()]
        
        lunar_month_names = {
            1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
            7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
        }
        
        # HTML生成（絵文字を使わない）
        html_content = """
<div style="font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.8; color: #333;">

<h2 style="color: #4a5568; border-left: 4px solid #5a67d8; padding-left: 12px;">今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
<p style="margin: 0; font-size: 20px;"><strong>西暦:</strong> {year}年{month}月{day}日（{weekday}曜日）</p>
<p style="margin: 10px 0 0 0; font-size: 17px;"><strong>旧暦:</strong> {lunar_month}月{lunar_day}日 <span style="opacity: 0.9;">（{lunar_month_name}）</span></p>
<p style="margin: 10px 0 0 0; font-size: 17px;"><strong>月齢:</strong> {moon_age} <span style="opacity: 0.9;">（{moon_name}）</span></p>
<p style="margin: 10px 0 0 0; font-size: 15px; opacity: 0.95;">{moon_desc}</p>
</div>

<div style="background-color: #f7fafc; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 3px solid #4299e1;">
<p style="margin: 0; color: #2d3748;">旧暦{lunar_month}月は<strong>「{lunar_month_name}」</strong>。{moon_name}の頃は、{moon_desc}が見られる季節です。</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h3 style="color: #2d3748; font-size: 22px;">季節の移ろい</h3>

<div style="border-left: 4px solid #f6ad55; padding-left: 15px; margin: 20px 0; background: linear-gradient(to right, #fef5e7, transparent); padding: 15px;">
<h4 style="color: #dd6b20; margin-top: 0; font-size: 18px;">二十四節気: {sekki_name}</h4>
<p style="margin: 5px 0 0 0; color: #2d3748;">{sekki_desc}</p>
</div>

<div style="border-left: 4px solid #48bb78; padding-left: 15px; margin: 20px 0; background: linear-gradient(to right, #f0fff4, transparent); padding: 15px;">
<h4 style="color: #2f855a; margin-top: 0; font-size: 18px;">七十二候: {kou_name}</h4>
<p style="margin: 5px 0; color: #2d3748;"><em>読み:</em> {kou_reading}</p>
<p style="margin: 5px 0 0 0; color: #2d3748;">{kou_desc}</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h3 style="color: #2d3748; font-size: 22px;">旬の食材</h3>

<div style="background: linear-gradient(135deg, #fef5e7 0%, #fef3c7 100%); padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<p style="margin: 0 0 10px 0; font-size: 16px;"><strong>今が旬の食材:</strong></p>
<p style="margin: 0; font-size: 15px; color: #744210;">{foods}</p>
<p style="margin: 15px 0 0 0; font-size: 14px; color: #92400e;">季節の恵みをいただき、自然のリズムを感じましょう。</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h3 style="color: #2d3748; font-size: 22px;">季節の花</h3>

<div style="background: linear-gradient(135deg, #ffeef8 0%, #ffe4f3 100%); padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<p style="margin: 0; font-size: 18px; font-weight: bold; color: #831843;">{flower_name}</p>
<p style="margin: 10px 0 5px 0; color: #9f1239;"><em>花言葉:</em> <strong>{flower_meaning}</strong></p>
<p style="margin: 5px 0 0 0; font-size: 14px; color: #be185d;">{flower_desc}</p>
</div>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<div style="background: linear-gradient(135deg, #ebf8ff 0%, #dbeafe 100%); padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<p style="margin: 0; font-size: 15px; color: #1e40af; font-weight: 500;">
季節を感じながら、今日も良い一日をお過ごしください
</p>
<p style="margin: 10px 0 0 0; font-size: 13px; color: #3b82f6;">
自動投稿システムにより生成 - {date_str}
</p>
</div>

</div>
""".format(
            year=self.target_date.year,
            month=self.target_date.month,
            day=self.target_date.day,
            weekday=weekday,
            lunar_month=lunar['lunar_month'],
            lunar_day=lunar['lunar_day'],
            lunar_month_name=lunar_month_names.get(lunar['lunar_month'], ''),
            moon_age=lunar['moon_age'],
            moon_name=lunar['moon_name'],
            moon_desc=lunar['moon_description'],
            sekki_name=sekki_kou['sekki'][0],
            sekki_desc=sekki_kou['sekki'][1],
            kou_name=sekki_kou['kou'][0],
            kou_reading=sekki_kou['kou'][1],
            kou_desc=sekki_kou['kou'][2],
            foods=", ".join(seasonal['foods'][:8]),
            flower_name=seasonal['flower'][0],
            flower_meaning=seasonal['flower'][1],
            flower_desc=seasonal['flower'][2],
            date_str=self.target_date.strftime('%Y年%m月%d日')
        )
        
        return {
            'title': '{}年{}月{}日({})の暦情報'.format(
                self.target_date.year,
                self.target_date.month,
                self.target_date.day,
                weekday
            ),
            'content': html_content,
            'labels': ['暦', '二十四節気', '旧暦', '季節', '七十二候']
        }


class BloggerPoster:
    """Blogger投稿クラス"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        
    def authenticate(self):
        """Google APIの認証"""
        creds = None
        
        # 環境変数から認証情報を取得
        if os.environ.get('GOOGLE_TOKEN'):
            token_data = json.loads(os.environ['GOOGLE_TOKEN'])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        # トークンが無効な場合は再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # 初回セットアップ時のみ
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
            
            print("投稿成功: {}".format(response.get('url')))
            return response
            
        except Exception as e:
            print("投稿エラー: {}".format(str(e)))
            raise


def main():
    """メイン処理 - 毎日実行される"""
    try:
        # 環境変数から設定を取得
        blog_id = os.environ.get('BLOG_ID')
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        print("暦情報自動投稿システム起動")
        print("投稿日時: {}".format(datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')))
        
        # 暦情報を生成（今日の日付で自動生成）
        print("\n今日の暦情報を生成中...")
        generator = CalendarGenerator()
        post_data = generator.generate_content()
        
        print("   タイトル: {}".format(post_data['title']))
        
        # Bloggerに投稿
        print("\nBloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\nすべての処理が完了しました！")
        print("365日毎日違う内容が自動で投稿されます")
        
    except Exception as e:
        print("\nエラーが発生しました: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
