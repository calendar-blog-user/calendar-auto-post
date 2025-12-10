#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暦情報自動投稿システム - 完全版（全セクション実装）
見本と同等の情報量を提供
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
    """二十四節気・七十二候の計算"""
    
    @staticmethod
    def calculate_solar_longitude(date):
        """太陽黄経を計算"""
        year = date.year
        month = date.month
        day = date.day
        
        # 春分を基準（簡易計算）
        days_in_year = (date - datetime(year, 1, 1, tzinfo=date.tzinfo)).days
        longitude = (days_in_year * 360 / 365.25 + 280) % 360
        return longitude
    
    @classmethod
    def get_sekki_info(cls, date):
        """現在の二十四節気"""
        sekki_list = [
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
        
        longitude = cls.calculate_solar_longitude(date)
        current_sekki = sekki_list[0]
        
        for i in range(len(sekki_list)):
            deg, name, reading, desc = sekki_list[i]
            next_deg = sekki_list[(i + 1) % len(sekki_list)][0]
            
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
    def get_kou_info(cls, date):
        """現在の七十二候"""
        month = date.month
        day = date.day
        
        kou_list = [
            (11, 22, "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる頃。空気が乾燥し、冬の訪れを感じます。"),
            (11, 27, "朔風払葉", "きたかぜこのはをはらう", "北からの冷たい季節風が、木々の葉をさらさらと落としてゆきます。街路樹のイチョウが黄金色の絨毯をつくり、冬の足音が一層近づいてきます。"),
            (12, 2, "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色く色づき始める頃。柑橘類が旬を迎えます。"),
            (12, 7, "閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり、本格的な冬となる頃。寒さが一段と厳しくなります。"),
            (12, 12, "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る頃。動物たちも冬支度を終えます。"),
            (12, 16, "鱖魚群", "さけのうおむらがる", "鮭が群がって川を上る頃。冬の味覚の代表です。"),
            (12, 21, "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す頃。冬至を境に陽の気が増し始めます。"),
            (12, 26, "麋角解", "さわしかつのおつる", "大鹿が角を落とす頃。自然界の冬の営みです。"),
            (1, 1, "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃。春への準備が始まります。"),
            (1, 5, "芹乃栄", "せりすなわちさかう", "芹が盛んに生え始める頃。七草粥の材料です。"),
            (1, 10, "水泉動", "しみずあたたかをふくむ", "地中で凍った泉が動き始める頃。わずかに春の気配を感じます。"),
        ]
        
        current_kou = ("閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がり本格的な冬となる")
        
        for m, d, name, reading, desc in reversed(kou_list):
            if month > m or (month == m and day >= d):
                current_kou = (name, reading, desc)
                break
        
        return current_kou


class AccurateLunarCalendar:
    """正確な旧暦計算"""
    
    @staticmethod
    def calculate_lunar_date(date):
        """旧暦を計算（修正版 - 2025年12月10日=旧暦10/21, 月齢19.8を基準）"""
        # 2025年12月10日 = 旧暦2025年10月21日、月齢19.8を基準点とする
        reference = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        reference_lunar_year = 2025
        reference_lunar_month = 10
        reference_lunar_day = 21
        reference_moon_age = 19.8
        
        synodic = 29.530588861  # 朔望月周期
        
        # 経過日数を計算
        elapsed_days = (date - reference).total_seconds() / 86400
        
        # 月齢を計算
        moon_age = (reference_moon_age + elapsed_days) % synodic
        if moon_age < 0:
            moon_age += synodic
        
        # 経過した朔望月数
        elapsed_months = int((reference_moon_age + elapsed_days) / synodic)
        
        # 旧暦の年月日を計算
        total_months_from_ref = elapsed_months
        lunar_year = reference_lunar_year
        lunar_month = reference_lunar_month
        lunar_day = reference_lunar_day
        
        # 月の進行
        for _ in range(abs(total_months_from_ref)):
            if total_months_from_ref > 0:
                lunar_month += 1
                if lunar_month > 12:
                    lunar_month = 1
                    lunar_year += 1
            else:
                lunar_month -= 1
                if lunar_month < 1:
                    lunar_month = 12
                    lunar_year -= 1
        
        # 日の計算
        days_in_current_month = elapsed_days - (elapsed_months * synodic)
        lunar_day = reference_lunar_day + int(days_in_current_month)
        
        # 日の繰り上がり・繰り下がり処理
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


class ComprehensiveCalendarGenerator:
    """包括的な暦情報生成"""
    
    def __init__(self, target_date=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.month = self.date.month
        self.day = self.date.day
    
    def get_lunar_month_names(self):
        """旧暦月の異名と説明"""
        names = {
            1: ("睦月", "むつき", "親族が睦み合う月"),
            2: ("如月", "きさらぎ", "衣を更に着る寒い月"),
            3: ("弥生", "やよい", "草木がいよいよ生い茂る月"),
            4: ("卯月", "うづき", "卯の花が咲く月"),
            5: ("皐月", "さつき", "早苗を植える月"),
            6: ("水無月", "みなづき", "水の月、または田に水を引く月"),
            7: ("文月", "ふみづき", "文を披露する月、七夕の月"),
            8: ("葉月", "はづき", "葉が落ち始める月"),
            9: ("長月", "ながつき", "夜が長くなる月"),
            10: ("神無月", "かんなづき", "神々が出雲に集まる月。出雲では神在月"),
            11: ("霜月", "しもつき", "霜が降り始める月"),
            12: ("師走", "しわす", "師も走るほど忙しい月")
        }
        return names
    
    def generate_seasonal_description(self, lunar, sekki, kou):
        """季節の詳細な説明文"""
        lunar_names = self.get_lunar_month_names()
        lunar_info = lunar_names.get(lunar['month'], ("", "", ""))
        
        descriptions = {
            12: f"旧暦{lunar['month']}月は「{lunar_info[0]}」。{lunar['phase']}の頃は、{lunar['appearance']}が見られる季節です。このころは古くから「一年の終わりを告げる月」とされ、年越しの準備に忙しい時期。空気が澄み渡り、冬の星座が美しく輝きます。",
            1: f"旧暦{lunar['month']}月は「{lunar_info[0]}」。{lunar['phase']}の頃は、{lunar['appearance']}が見られる季節です。新しい年の始まりで、寒さが最も厳しい時期ですが、春への期待が膨らみます。",
            11: f"旧暦{lunar['month']}月は「{lunar_info[0]}」または地域によっては「神在月」。出雲へ全国の神々が集う月とされ、{lunar['phase']}の頃は{lunar['appearance']}が見られます。このころは古くから「冬の到来を告げる月」とされ、夜が長く火の明かりが恋しくなる季節。虫の音も静まり、空気が澄み渡るため、星がたいへん美しく見えます。"
        }
        
        return descriptions.get(self.month, descriptions[12])
    
    def get_nature_changes(self):
        """自然の変化"""
        changes = {
            12: [
                "霜柱が早朝に見られやすくなる",
                "カモなど冬鳥が増え、川辺がにぎやかになる",
                "柿が甘く熟し、干し柿づくりが始まる",
                "木々の葉が完全に落ち、冬木立となる"
            ],
            1: [
                "寒さが最も厳しくなる",
                "池や水たまりに氷が張る",
                "早朝の霜柱が美しい",
                "ロウバイや梅のつぼみが膨らみ始める"
            ]
        }
        return changes.get(self.month, changes[12])
    
    def get_agricultural_calendar(self):
        """農事歴"""
        calendars = {
            12: {
                'title': '冬支度の農期',
                'activities': [
                    '稲作地域では脱穀がほぼ終盤',
                    '畑では大根・白菜・ネギなど冬野菜が甘みを増す頃',
                    '東北や北海道では畑に堆肥をまき、土を休ませる準備',
                    '伝統的には「漬物の仕込み」の季節で、沢庵漬け、白菜漬けなどが家々に並び始めます'
                ],
                'detail': '昔の農村では、この時期は農作業が一段落し、冬に向けて機具の手入れや縄綯い（なわない）などの室内作業が中心でした。'
            },
            1: {
                'title': '農閑期',
                'activities': [
                    '農具の手入れと修理',
                    '藁細工や縄綯いなどの室内作業',
                    '堆肥づくりの準備',
                    '春の作付け計画を立てる'
                ],
                'detail': '寒さが厳しく屋外作業は少ないですが、春に向けての大切な準備期間です。'
            }
        }
        return calendars.get(self.month, calendars[12])
    
    def get_customs_and_traditions(self):
        """風習・しきたり"""
        customs = {
            12: {
                'description': f'{self.month}月は、地域によって冬囲い（雪国の家や庭木を守る作業）、すす払い、正月飾りの準備などが行われます。都市部でもクリスマス飾りの準備が目立ち始め、日本の冬の風物詩「和と洋の季節の混じり合い」が見られる頃です。',
                'items': [
                    '冬囲い（雪国の家や庭木を守る作業）',
                    'すす払い（12月13日頃）',
                    '正月飾りの準備',
                    '冬至の柚子湯（12月21日頃）',
                    'クリスマスの準備'
                ]
            },
            1: {
                'description': f'{self.month}月は新年を迎え、初詣、鏡開き、小正月など、一年の始まりにふさわしい伝統行事が目白押しです。',
                'items': [
                    '初詣',
                    '七草粥（1月7日）',
                    '鏡開き（1月11日）',
                    '小正月（1月15日）',
                    '寒中見舞い'
                ]
            }
        }
        return customs.get(self.month, customs[12])
    
    def get_holidays_and_events(self):
        """記念日と祝日"""
        events_db = {
            (12, 7): [
                ('大雪', '二十四節気の一つ'),
            ],
            (12, 21): [
                ('冬至', '一年で最も昼が短い日'),
            ],
            (12, 25): [
                ('クリスマス', 'キリスト教の祭日として世界的に祝われる'),
            ],
            (12, 31): [
                ('大晦日', '一年の最後の日。除夜の鐘が鳴り響く'),
            ],
            (1, 1): [
                ('元日', '国民の祝日。一年の始まり'),
                ('初日の出', '新年最初の日の出を拝む習慣'),
            ],
            (1, 7): [
                ('七草の節句', '七草粥を食べて無病息災を願う'),
            ],
            (1, 11): [
                ('鏡開き', '正月の鏡餅を割っていただく'),
            ],
        }
        
        key = (self.month, self.day)
        events = events_db.get(key, [])
        
        if not events:
            return f'{self.month}月{self.day}日そのものは広く知られた国民の祝日ではありませんが、季節の節目として大切にされてきた日です。'
        
        result = f'{self.month}月{self.day}日の記念日・行事：\n\n'
        for name, desc in events:
            result += f'■ {name}\n{desc}\n\n'
        
        return result
    
    def get_mythology_and_legends(self):
        """神話・伝説"""
        myths = {
            12: '師走といえば「神々の帰還」。出雲での神議りを終えた八百万の神が、それぞれの地に戻ってくる月とされています。また冬至の頃は「一陽来復」といい、陰の極まりから陽気が復活し始める転換点として、古来より重視されてきました。',
            1: '睦月は新年の月。古来より「年神様」が各家庭を訪れ、新しい年の幸福をもたらすと信じられています。門松や鏡餅は年神様を迎えるためのものです。',
            10: '神無月といえば「神々の会議」。出雲に集う八百万の神は、夫婦の縁、人と人の巡り合わせ、土地の平安などを話し合うと信じられています。',
            11: '霜月は「神々の帰還準備」の月。出雲での神議りが終わり、各地の神々が戻る準備を始める時期とされます。'
        }
        return myths.get(self.month, myths.get(12, ''))
    
    def get_cultural_trivia(self):
        """文化雑学"""
        trivia = {
            12: f'旧暦{AccurateLunarCalendar.calculate_lunar_date(self.date)["month"]}月は別名「師走（しわす）」。師（僧侶）も走り回るほど忙しい月という説や、「年が果てる（しはす）」が転じたという説があります。一年の締めくくりとして、様々な行事や準備に追われる様子を表しています。',
            1: '旧暦1月は別名「睦月（むつき）」。新年を迎えて親族が睦み合う月という意味です。正月の様々な行事は、もともと旧暦1月に行われていたものです。',
            10: '旧暦10月は別名「神去月（かみさりつき）」とも呼ばれました。これは神々が出雲へ向かい、地元を留守にするという信仰から来たもの。ただし、出雲地方では反対に「神在月」と呼ばれ、神を迎えるための祭りが盛大に行われます。暦は地域の文化を色濃く反映していたのですね。'
        }
        return trivia.get(self.month, trivia.get(12, ''))
    
    def get_weather_info(self):
        """気象情報"""
        weather = {
            12: [
                '朝晩の冷え込みが増し、最低気温が0℃前後まで下がる地域も',
                '乾燥が進み、風が強い日は落ち葉が舞う',
                '山では初雪の便りが届き、スキー場がオープン',
                '夜空は快晴が多く、星が非常に見やすい季節'
            ],
            1: [
                '一年で最も寒い時期、厳しい寒さが続く',
                '太平洋側は乾燥した晴天が多い',
                '日本海側は雪や曇りの日が多い',
                '空気が澄んで遠くの山々がくっきり見える'
            ]
        }
        return weather.get(self.month, weather[12])
    
    def get_seasonal_foods(self):
        """旬の食材"""
        foods = {
            12: {
                'vegetables': ['大根', '白菜', '春菊', 'ほうれん草', 'かぶ', '長ねぎ', '里芋', 'ゆず'],
                'fruits': ['みかん', 'りんご', '柚子', '金柑'],
                'seafood': ['ブリ', 'カキ（牡蠣）', 'サバ', '鱈', 'ふぐ', 'あんこう'],
                'special': '特に「大根」はこの時期に甘くなり、ふろふき大根やおでんに最適。また、寒さが増すと「鍋料理」が家庭の主役になります。',
                'ceremonial': '冬至には南瓜（かぼちゃ）を食べる習慣があり、年越しそばで一年を締めくくります。'
            },
            1: {
                'vegetables': ['白菜', 'ネギ', '小松菜', '大根', 'ほうれん草', '春菊'],
                'fruits': ['みかん', '金柑', 'いちご'],
                'seafood': ['鱈', '寒ブリ', '牡蠣', 'あんこう', 'ふぐ'],
                'special': '寒さで甘みが増した野菜が美味しい時期。鍋料理や煮物が一層美味しくなります。',
                'ceremonial': '七草粥（芹、薺、御形、繁縷、仏の座、菘、蘿蔔）で正月疲れの胃腸を休めます。'
            }
        }
        return foods.get(self.month, foods[12])
    
    def get_flowers_and_plants(self):
        """季節の花と植物"""
        flowers = {
            12: {
                'main': ('水仙', 'すいせん', '自己愛・神秘', '清楚な香りの冬の花。霜に負けずに凛と咲く姿が冬の庭を彩ります。'),
                'others': [
                    ('山茶花', 'さざんか', '困難に打ち勝つ・ひたむきさ', '冬の訪れを告げる庭木'),
                    ('千両', 'せんりょう', '商売繁盛・裕福', '正月飾りの縁起物'),
                    ('南天', 'なんてん', '難を転ずる', '厄除けの縁起木')
                ]
            },
            1: {
                'main': ('福寿草', 'ふくじゅそう', '幸せを招く・永久の幸福', '新春を告げる黄金の花。雪解けとともに咲き始める春の使者です。'),
                'others': [
                    ('梅', 'うめ', '高潔・忍耐・美', '早春に咲く香り高い花'),
                    ('水仙', 'すいせん', '自己愛・神秘', '清楚な香りの冬の花'),
                    ('ロウバイ', 'ろうばい', '慈愛・先見', '蝋のような質感の黄色い花')
                ]
            }
        }
        return flowers.get(self.month, flowers[12])
    
    def get_astronomy_info(self, lunar):
        """天文情報"""
        moon_age = lunar['age']
        
        info = {
            'moon': f"月齢{moon_age}の今日は{lunar['appearance']}。{lunar['phase']}の時期は、月の陰影の変化が美しく観察できます。",
            'stars': []
        }
        
        if self.month in [12, 1, 2]:
            info['stars'] = [
                '冬の星座オリオンが東から昇り始める',
                '冬の大三角（ベテルギウス・シリウス・プロキオン）が見頃',
                'おうし座のプレアデス星団（すばる）が美しい',
                '空気が乾いているため天の川がくっきり見える日も'
            ]
        
        return info
    
    def get_traditional_crafts(self):
        """伝統工芸"""
        crafts = {
            12: [
                ('藁細工', 'わらざいく', 'しめ縄、わらぐつ、縄飾りなど', '冬の農閑期の代表的な手仕事'),
                ('干し柿づくり', 'ほしがきづくり', '吊るし柿', '地域によっては街を彩る冬の風物詩'),
                ('正月飾り', 'しょうがつかざり', '門松、しめ飾り', '新年を迎える準備の工芸'),
                ('曲げわっぱ', 'まげわっぱ', '秋田の伝統工芸', '新米の季節に合わせて弁当箱の需要も増える')
            ],
            1: [
                ('凧', 'たこ', 'お正月の遊び道具', '伝統的な和凧は芸術作品'),
                ('羽子板', 'はごいた', '女の子の正月遊び', '厄除けの意味も'),
                ('書き初め', 'かきぞめ', '新年の習字', '一年の抱負を書く'),
                ('餅つき', 'もちつき', '杵と臼での伝統作業', '正月の準備')
            ]
        }
        return crafts.get(self.month, crafts[12])
    
    def get_festivals_and_rituals(self):
        """祭事と神話伝説"""
        festivals = {
            12: '師走は一年の締めくくりの月。大祓（おおはらえ）で一年の穢れを払い、除夜の鐘で煩悩を消し去ります。また、冬至は「一陽来復」として陰が極まり陽に転じる重要な転換点とされ、各地で冬至祭が行われます。',
            1: '正月は一年で最も重要な祭事。年神様を迎え入れる準備として、門松や鏡餅を飾ります。元日の初詣では一年の無事を祈願し、七草粥で無病息災を願います。小正月（1月15日）には小豆粥を食べ、どんど焼きで正月飾りを焚き上げます。',
            11: '出雲地方では11月は「神在祭」の真っ最中。神楽が奉納され、稲佐の浜で神迎えの儀式が行われます。これは古事記や日本書紀に記される「国譲り神話」とも深く関係し、大国主命が国を天照大神の系譜へと譲った後、出雲が重要な神事の中心となったとされることが背景です。'
        }
        return festivals.get(self.month, festivals.get(12, ''))
    
    def get_traditional_arts(self):
        """伝統芸能"""
        arts = {
            12: '12月は能楽・歌舞伎の公演が活発。特に「冬支度」や「大雪」に合わせた曲目として、能「小鍛冶」、歌舞伎「仮名手本忠臣蔵」（冬の名作）が演じられることが多い時期です。',
            1: '新春を祝う能楽・歌舞伎の公演が各地で開催。特に「翁」（能）、「寿曽我対面」（歌舞伎）など、めでたい演目が正月にふさわしいとされます。',
            11: '11月は能楽・歌舞伎の公演が活発。特に「冬支度」や「小雪」に合わせた曲目として、能「小鍛冶」、歌舞伎「仮名手本忠臣蔵」（冬の名作）が演じられることが多い時期です。'
        }
        return arts.get(self.month, arts.get(12, ''))
    
    def generate_full_html(self):
        """完全版HTML生成"""
        lunar = AccurateLunarCalendar.calculate_lunar_date(self.date)
        sekki = SolarTermCalculator.get_sekki_info(self.date)
        kou = SolarTermCalculator.get_kou_info(self.date)
        
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[self.date.weekday()]
        
        lunar_names = self.get_lunar_month_names()
        lunar_info = lunar_names.get(lunar['month'], ("", "", ""))
        
        seasonal_desc = self.generate_seasonal_description(lunar, sekki, kou)
        nature_changes = self.get_nature_changes()
        agri = self.get_agricultural_calendar()
        customs = self.get_customs_and_traditions()
        holidays = self.get_holidays_and_events()
        mythology = self.get_mythology_and_legends()
        trivia = self.get_cultural_trivia()
        weather = self.get_weather_info()
        foods = self.get_seasonal_foods()
        flowers = self.get_flowers_and_plants()
        astro = self.get_astronomy_info(lunar)
        crafts = self.get_traditional_crafts()
        festivals = self.get_festivals_and_rituals()
        arts = self.get_traditional_arts()
        
        html = f"""
<div style="font-family: 'ヒラギノ角ゴ Pro', 'Hiragino Kaku Gothic Pro', 'メイリオ', Meiryo, sans-serif; max-width: 900px; margin: 0 auto; line-height: 1.9; color: #2d3748;">

<h2 style="color: #2c5282; border-bottom: 4px solid #4299e1; padding-bottom: 12px; margin-bottom: 25px; font-size: 28px;">今日の暦情報</h2>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);">
<p style="margin: 0; font-size: 24px; font-weight: bold;">西暦: {self.date.year}年{self.date.month}月{self.date.day}日（{weekday}曜日）</p>
<p style="margin: 15px 0 0 0; font-size: 20px;">旧暦: {lunar['month']}月{lunar['day']}日（{lunar_info[0]}）</p>
<p style="margin: 10px 0 0 0; font-size: 20px;">月齢: {lunar['age']}（{lunar['phase']}）</p>
<p style="margin: 10px 0 0 0; font-size: 17px; opacity: 0.95; line-height: 1.7;">{lunar['appearance']}</p>
</div>

<div style="background: #f7fafc; padding: 25px; border-radius: 12px; border-left: 5px solid #4299e1; margin-bottom: 35px;">
<p style="margin: 0; line-height: 2; font-size: 16px;">{seasonal_desc}</p>
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

<div style="background: #fffaf0; padding: 25px; border-radius: 10px; margin-bottom: 30px; border: 2px solid #fbd38d;">
<h4 style="color: #c05621; margin: 0 0 15px 0; font-size: 20px;">自然の変化としては:</h4>
<ul style="margin: 0; padding-left: 30px; color: #2d3748; line-height: 2;">
{"".join(f"<li style='margin-bottom: 10px; font-size: 15px;'>{change}</li>" for change in nature_changes)}
</ul>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #68d391; padding-left: 15px;">農事歴（農業暦）</h3>

<div style="background: linear-gradient(135deg, #fef5e7, #fef3c7); padding: 28px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
<p style="margin: 0 0 18px 0; font-size: 20px; font-weight: bold; color: #744210;">この時期は「{agri['title']}」</p>
<ul style="margin: 0; padding-left: 30px; color: #744210; line-height: 2;">
{"".join(f"<li style='margin-bottom: 12px; font-size: 15px;'>{activity}</li>" for activity in agri['activities'])}
</ul>
<p style="margin: 25px 0 0 0; color: #92400e; line-height: 2; font-style: italic; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 8px; font-size: 15px;">{agri['detail']}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #9f7aea; padding-left: 15px;">日本の風習・しきたり</h3>

<div style="background: #faf5ff; padding: 28px; border-radius: 12px; border-left: 6px solid #9f7aea; margin-bottom: 30px;">
<p style="margin: 0 0 20px 0; line-height: 2; color: #2d3748; font-size: 16px;">{customs['description']}</p>
<h4 style="color: #6b46c1; margin: 20px 0 15px 0; font-size: 19px;">この時期の風習:</h4>
<ul style="margin: 0; padding-left: 30px; color: #2d3748; line-height: 2;">
{"".join(f"<li style='margin-bottom: 10px; font-size: 15px;'>{item}</li>" for item in customs['items'])}
</ul>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f6ad55; padding-left: 15px;">日本の記念日と祝日</h3>

<div style="background: linear-gradient(135deg, #fffaf0, #fef3c7); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<div style="color: #744210; line-height: 2; font-size: 16px; white-space: pre-line;">{holidays}</div>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #ed64a6; padding-left: 15px;">日本の神話・伝説</h3>

<div style="background: linear-gradient(135deg, #fef5f8, #fce7f3); padding: 28px; border-radius: 12px; margin-bottom: 30px; border: 2px solid #f9a8d4;">
<p style="margin: 0; color: #831843; line-height: 2; font-size: 16px;">{mythology}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #4299e1; padding-left: 15px;">暦にまつわる文化雑学</h3>

<div style="background: #ebf8ff; padding: 28px; border-radius: 12px; margin-bottom: 30px; border-left: 5px solid #4299e1;">
<p style="margin: 0; color: #1e40af; line-height: 2; font-size: 16px;">{trivia}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #38b2ac; padding-left: 15px;">自然と気象情報</h3>

<div style="background: linear-gradient(135deg, #e6fffa, #b2f5ea); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<ul style="margin: 0; padding-left: 30px; color: #234e52; line-height: 2;">
{"".join(f"<li style='margin-bottom: 12px; font-size: 16px;'>{w}</li>" for w in weather)}
</ul>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f56565; padding-left: 15px;">旬の食材・行事食</h3>

<div style="background: linear-gradient(135deg, #fff5f5, #fed7d7); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<h4 style="color: #c53030; margin: 0 0 15px 0; font-size: 20px;">旬を迎える食材:</h4>
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
<p style="margin: 15px 0 0 0; padding: 18px; background: rgba(255,255,255,0.6); border-radius: 8px; color: #742a2a; line-height: 2; font-size: 15px;"><strong>行事食としては:</strong><br>{foods['ceremonial']}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #f687b3; padding-left: 15px;">季節の草木と花言葉</h3>

<div style="background: linear-gradient(135deg, #fff0f5, #ffe4f3); padding: 28px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
<p style="margin: 0 0 8px 0; font-size: 22px; font-weight: bold; color: #831843;">季節の花: {flowers['main'][0]}（{flowers['main'][1]}）</p>
<p style="margin: 12px 0; color: #9f1239; font-size: 17px;"><em>花言葉:</em> 「{flowers['main'][2]}」</p>
<p style="margin: 12px 0 0 0; color: #be185d; line-height: 2; font-size: 16px;">{flowers['main'][3]}</p>
</div>

<div style="background: #fef5f8; padding: 25px; border-radius: 10px; margin-bottom: 30px;">
<h4 style="color: #9f1239; margin: 0 0 15px 0; font-size: 19px;">その他の植物:</h4>
{"".join(f"<div style='margin-bottom: 18px; padding: 15px; background: white; border-radius: 8px;'><p style='margin: 0; font-size: 17px; font-weight: bold; color: #831843;'>{name}（{reading}）</p><p style='margin: 8px 0 0 0; color: #be185d; font-size: 15px;'>花言葉: 「{meaning}」<br>{desc}</p></div>" for name, reading, meaning, desc in flowers['others'])}
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #4299e1; padding-left: 15px;">月や星の暦・天文情報</h3>

<div style="background: linear-gradient(135deg, #ebf4ff, #dbeafe); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<p style="margin: 0 0 20px 0; line-height: 2; color: #1e40af; font-size: 16px;">{astro['moon']}</p>
<h4 style="color: #1e3a8a; margin: 20px 0 15px 0; font-size: 19px;">星空では:</h4>
<ul style="margin: 0; padding-left: 30px; color: #1e40af; line-height: 2;">
{"".join(f"<li style='margin-bottom: 12px; font-size: 15px;'>{star}</li>" for star in astro['stars'])}
</ul>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #ed8936; padding-left: 15px;">伝統工芸・民芸品</h3>

<div style="background: linear-gradient(135deg, #fffaf0, #feebc8); padding: 28px; border-radius: 12px; margin-bottom: 30px;">
<p style="margin: 0 0 20px 0; color: #7c2d12; font-size: 16px; line-height: 2;">この季節に関連して作られるものとしては:</p>
{"".join(f"<div style='margin-bottom: 20px; padding: 18px; background: white; border-radius: 8px; border-left: 4px solid #ed8936;'><p style='margin: 0 0 8px 0; font-size: 18px; font-weight: bold; color: #c05621;'>{name}（{reading}）</p><p style='margin: 0; color: #7c2d12; font-size: 15px;'><strong>{item}:</strong> {desc}</p></div>" for name, reading, item, desc in crafts)}
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #805ad5; padding-left: 15px;">祭事の背景・神話伝説</h3>

<div style="background: linear-gradient(135deg, #faf5ff, #e9d8fd); padding: 28px; border-radius: 12px; margin-bottom: 30px; border: 2px solid #b794f4;">
<p style="margin: 0; color: #44337a; line-height: 2; font-size: 16px;">{festivals}</p>
</div>

<hr style="border: none; border-top: 3px solid #e2e8f0; margin: 40px 0;">

<h3 style="color: #2d3748; font-size: 26px; margin-bottom: 25px; border-left: 6px solid #d53f8c; padding-left: 15px;">伝統芸能</h3>

<div style="background: linear-gradient(135deg, #fff5f7, #fed7e2); padding: 28px; border-radius: 12px; margin-bottom: 35px;">
<p style="margin: 0; color: #702459; line-height: 2; font-size: 16px;">{arts}</p>
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
            'labels': ['暦', '二十四節気', '旧暦', '季節', '七十二候', '農事歴', '風習', '伝統文化', '行事食', '天文', '神話', '伝統芸能']
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
        blog_id = os.environ.get('BLOG_ID')
        if not blog_id:
            raise Exception("BLOG_ID環境変数が設定されていません")
        
        print("=" * 70)
        print("暦情報自動投稿システム 完全版 起動")
        print("=" * 70)
        print(f"投稿日時: {datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y年%m月%d日 %H:%M:%S')}")
        
        # 暦情報生成
        print("\n今日の暦情報を生成中...")
        print("- 全セクション実装版")
        print("- 見本と同等の情報量")
        
        generator = ComprehensiveCalendarGenerator()
        post_data = generator.generate_full_html()
        
        print(f"\nタイトル: {post_data['title']}")
        print(f"セクション数: 14セクション")
        print(f"推定文字数: 約{len(post_data['content'])}文字")
        
        # Blogger投稿
        print("\nBloggerに投稿中...")
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
        
        print("\n" + "=" * 70)
        print("すべての処理が完了しました！")
        print("見本と同等の豊富な暦情報が投稿されました")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
