#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
暦情報自動投稿システム 改良版
- GitHub Actionsでの実行を想定
- ephemによる正確な天文計算（太陽黄経）
- Google Gemini APIによる温かみのある文章生成
"""

import os
import sys
import math
import ephem
from datetime import datetime
from zoneinfo import ZoneInfo
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Blogger API Scope
SCOPES = ['https://www.googleapis.com/auth/blogger']

class AstronomyCalculator:
    """
    天文計算クラス
    ephemライブラリを使用して正確な太陽黄経を計算し、節気・候を判定する
    """
    
    # 二十四節気リスト（太陽黄経0度=春分からスタート）
    SEKKI_LIST = [
        (0, "春分", "しゅんぶん", "昼夜の長さがほぼ等しくなる日。"),
        (15, "清明", "せいめい", "万物が清らかで生き生きとする頃。"),
        (30, "穀雨", "こくう", "穀物を潤す春の雨が降る頃。"),
        (45, "立夏", "りっか", "夏の始まり。新緑が鮮やかな季節。"),
        (60, "小満", "しょうまん", "草木が茂り、天地に気が満ちる頃。"),
        (75, "芒種", "ぼうしゅ", "稲の種をまく時期。梅雨入りの頃。"),
        (90, "夏至", "げし", "一年で最も昼が長い日。"),
        (105, "小暑", "しょうしょ", "暑さが本格化し始める頃。"),
        (120, "大暑", "たいしょ", "一年で最も暑さが厳しい頃。"),
        (135, "立秋", "りっしゅう", "秋の始まり。残暑が厳しい時期。"),
        (150, "処暑", "しょしょ", "暑さが峠を越える頃。"),
        (165, "白露", "はくろ", "草木に白い露が宿る頃。"),
        (180, "秋分", "しゅうぶん", "昼夜の長さが再びほぼ等しくなる日。"),
        (195, "寒露", "かんろ", "露が冷たく感じられる頃。"),
        (210, "霜降", "そうこう", "霜が降り始める頃。"),
        (225, "立冬", "りっとう", "冬の始まり。"),
        (240, "小雪", "しょうせつ", "わずかに雪が降り始める頃。"),
        (255, "大雪", "たいせつ", "雪が本格的に降り始める頃。"),
        (270, "冬至", "とうじ", "一年で最も昼が短い日。"),
        (285, "小寒", "しょうかん", "寒の入り。"),
        (300, "大寒", "だいかん", "一年で最も寒い時期。"),
        (315, "立春", "りっしゅん", "春の始まり。"),
        (330, "雨水", "うすい", "雪が雨に変わり、氷が解ける頃。"),
        (345, "啓蟄", "けいちつ", "冬ごもりの虫が這い出る頃。")
    ]

    # 七十二候リスト（簡易化のため主要なものを抜粋してインデックス対応させるか、全リストが必要）
    # ここでは太陽黄経5度ごとのインデックスに対応するリストとして定義
    # 0度(春分初候) ～ 355度(啓蟄末候)
    KOU_LIST_ORDERED = [
        # 春分 (0, 5, 10)
        ("雀始巣", "すずめはじめてすくう"), ("桜始開", "さくらはじめてひらく"), ("雷乃発声", "かみなりすなわちこえをはっす"),
        # 清明 (15, 20, 25)
        ("玄鳥至", "つばめきたる"), ("鴻雁北", "こうがんかえる"), ("虹始見", "にじはじめてあらわる"),
        # 穀雨
        ("葭始生", "あしはじめてしょうず"), ("霜止出苗", "しもやんでなえいずる"), ("牡丹華", "ぼたんはなさく"),
        # 立夏
        ("蛙始鳴", "かわずはじめてなく"), ("蚯蚓出", "みみずいずる"), ("竹笋生", "たけのこしょうず"),
        # 小満
        ("蚕起食桑", "かいこおきてくわをはむ"), ("紅花栄", "べにばなさかう"), ("麦秋至", "むぎのときいたる"),
        # 芒種
        ("蟷螂生", "かまきりしょうず"), ("腐草為蛍", "くされたるくさほたるとなる"), ("梅子黄", "うめのみきばむ"),
        # 夏至
        ("乃東枯", "なつかれくさかるる"), ("菖蒲華", "あやめはなさく"), ("半夏生", "はんげしょうず"),
        # 小暑
        ("温風至", "あつかぜいたる"), ("蓮始開", "はすはじめてひらく"), ("鷹乃学習", "たかすなわちわざをならう"),
        # 大暑
        ("桐始結花", "きりはじめてはなをむすぶ"), ("土潤溽暑", "つちうるおうてむしあつし"), ("大雨時行", "たいうときどきふる"),
        # 立秋
        ("涼風至", "すずかぜいたる"), ("寒蝉鳴", "ひぐらしなく"), ("蒙霧升降", "ふかききりまとう"),
        # 処暑
        ("綿柎開", "わたのはなしべひらく"), ("天地始粛", "てんちはじめてさむし"), ("禾乃登", "こくものすなわちみのる"),
        # 白露
        ("草露白", "くさのつゆしろし"), ("鶺鴒鳴", "せきれいなく"), ("玄鳥去", "つばめさる"),
        # 秋分
        ("雷乃収声", "かみなりすなわちこえをおさむ"), ("蟄虫坏戸", "むしかくれてとをふさぐ"), ("水始涸", "みずはじめてかるる"),
        # 寒露
        ("鴻雁来", "こうがんきたる"), ("菊花開", "きくのはなひらく"), ("蟋蟀在戸", "きりぎりすとにあり"),
        # 霜降
        ("霜始降", "しもはじめてふる"), ("霎時施", "こさめときどきふる"), ("楓蔦黄", "もみじつたきばむ"),
        # 立冬
        ("山茶始開", "つばきはじめてひらく"), ("地始凍", "ちはじめてこおる"), ("金盞香", "きんせんかさく"),
        # 小雪
        ("虹蔵不見", "にじかくれてみえず"), ("朔風払葉", "きたかぜこのはをはらう"), ("橘始黄", "たちばなはじめてきばむ"),
        # 大雪
        ("閉塞成冬", "そらさむくふゆとなる"), ("熊蟄穴", "くまあなにこもる"), ("鱖魚群", "さけのうおむらがる"),
        # 冬至
        ("乃東生", "なつかれくさしょうず"), ("麋角解", "さわしかつのおつる"), ("雪下出麦", "ゆきわたりてむぎのびる"),
        # 小寒
        ("芹乃栄", "せりすなわちさかう"), ("水泉動", "しみずあたたかをふくむ"), ("雉始雊", "きじはじめてなく"),
        # 大寒
        ("款冬華", "ふきのはなさく"), ("水沢腹堅", "さわみずこおりつめる"), ("鶏始乳", "にわとりはじめてとやにつく"),
        # 立春
        ("東風解凍", "はるかぜこおりをとく"), ("黄鶯睍睆", "うぐいすなく"), ("魚上氷", "うおこおりをいずる"),
        # 雨水
        ("土脉潤起", "つちのしょううるおいおこる"), ("霞始靆", "かすみはじめてたなびく"), ("草木萌動", "そうもくめばえいずる"),
        # 啓蟄
        ("蟄虫啓戸", "すごもりむしとをひらく"), ("桃始笑", "ももはじめてさく"), ("菜虫化蝶", "なむしちょうとなる")
    ]

    @classmethod
    def get_solar_info(cls, current_date):
        """ephemを使って正確な黄経を計算し、節気と候を特定する"""
        observer = ephem.Observer()
        observer.date = current_date
        sun = ephem.Sun(observer)
        
        # 太陽黄経（ラジアン -> 度）
        # ephemのhlonは黄経を返すが、J2000.0分点などの考慮が必要。
        # 簡易的にSun.lonを使用する場合、これは赤経に近い黄道座標。
        # 正確には ecliptic longitude を取得する。
        ecl = ephem.Ecliptic(sun)
        longitude_deg = math.degrees(ecl.lon)
        
        # 0-360度に正規化
        longitude_deg = longitude_deg % 360
        
        # 二十四節気の特定 (15度ごと)
        # 0度=春分, 15度=清明...
        # リストは0度始まりなので、インデックス計算で取得可能
        sekki_index = int(longitude_deg / 15)
        sekki_info = cls.SEKKI_LIST[sekki_index]
        
        # 七十二候の特定 (5度ごと)
        kou_index = int(longitude_deg / 5)
        # リストの範囲内かチェック
        if 0 <= kou_index < len(cls.KOU_LIST_ORDERED):
            kou_info = cls.KOU_LIST_ORDERED[kou_index]
        else:
            kou_info = ("不明", "ふめい")

        return {
            'longitude': longitude_deg,
            'sekki': sekki_info,
            'kou': kou_info
        }

class GeminiWriter:
    """Google Gemini APIを使って文章を生成するクラス"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None

    def generate_content(self, date_str, sekki, kou, existing_desc):
        """
        Geminiにプロンプトを投げて文章を生成
        無料枠を考慮し、Flashモデル等の軽量モデルを使用
        """
        if not self.model:
            return existing_desc + "\n(※AI生成機能は無効です)"

        prompt = f"""
あなたは日本の伝統と季節感に詳しいエッセイストです。
以下の情報を元に、ブログの読者に向けて「今日の季節の便り」を書いてください。

【日付】{date_str}
【二十四節気】{sekki[1]}（{sekki[2]}）: {sekki[3]}
【七十二候】{kou[0]}（{kou[1]}）

【要件】
- 読者がほっとするような、温かみのある優しい文体で書いてください。
- 時候の挨拶だけでなく、今の季節ならではの自然の風景、食べ物、あるいは心構えなどを絡めてください。
- 文字数は300文字〜400文字程度で充実させてください。
- 最後に、今日が読者にとって良い一日になるよう願う言葉で結んでください。
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return existing_desc + "\n(※AI生成中にエラーが発生しましたため、定型文を表示します)"

class ComprehensiveCalendarGenerator:
    """記事HTML生成クラス"""
    
    def __init__(self, target_date=None, api_key=None):
        self.jst = ZoneInfo("Asia/Tokyo")
        self.date = target_date or datetime.now(self.jst)
        self.gemini = GeminiWriter(api_key)

    def generate_full_html(self):
        # 正確な天文計算を実行
        solar_info = AstronomyCalculator.get_solar_info(self.date)
        sekki = solar_info['sekki'] # (deg, name, yomi, desc)
        kou = solar_info['kou']     # (name, yomi)
        
        date_str = self.date.strftime('%Y年%m月%d日')
        weekday = ["月", "火", "水", "木", "金", "土", "日"][self.date.weekday()]
        
        # Geminiによる温かい文章生成
        # 元のPDFにあるような静的データも良いが、充実させるためにAIを使用
        base_desc = f"{sekki[1]}、{kou[0]}の頃です。"
        ai_message = self.gemini.generate_content(date_str, sekki, kou, base_desc)
        
        # HTML組み立て
        html = f"""
        <div style="font-family: 'Hiragino Mincho ProN', 'Yu Mincho', serif; max-width: 800px; margin: 0 auto; color: #333; line-height: 1.8;">
            
            <!-- ヘッダー部分 -->
            <div style="text-align: center; padding: 40px 0; background-color: #f9f8f6; margin-bottom: 30px;">
                <p style="font-size: 1.2rem; color: #888; margin-bottom: 10px;">{date_str}（{weekday}）</p>
                <h1 style="font-size: 2.5rem; margin: 0; color: #5a4e4e; letter-spacing: 0.1em;">{sekki[1]}</h1>
                <p style="font-size: 1rem; color: #a58f8f; margin-top: 5px;">{sekki[2]}</p>
                <div style="margin-top: 20px; font-size: 1.1rem; border-top: 1px solid #ddd; border-bottom: 1px solid #ddd; display: inline-block; padding: 10px 30px;">
                    七十二候：{kou[0]} <span style="font-size: 0.9rem; color: #888;">（{kou[1]}）</span>
                </div>
            </div>

            <!-- AI生成された季節の便り -->
            <div style="padding: 0 20px; font-size: 1.05rem; text-align: justify;">
                {ai_message.replace(chr(10), '<br>')}
            </div>

            <!-- 天文データ -->
            <div style="margin-top: 50px; padding: 20px; background-color: #f0f4f8; border-radius: 8px; font-size: 0.9rem; color: #555;">
                <h3 style="margin-top: 0; color: #4a5568;">今日の天文メモ</h3>
                <ul style="list-style: none; padding: 0;">
                    <li>太陽黄経: {solar_info['longitude']:.2f}°</li>
                    <li>節気の説明: {sekki[3]}</li>
                </ul>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 40px 0;">
            <p style="text-align: center; font-size: 0.8rem; color: #aaa;">
                Digital Calendar Bot / Powered by Google Gemini
            </p>
        </div>
        """
        
        title = f"【季節の便り】{sekki[1]}・{kou[0]} ({self.date.month}月{self.date.day}日)"
        labels = ['暦', '二十四節気', '七十二候', sekki[1]]
        
        return {'title': title, 'content': html, 'labels': labels}

class BloggerPoster:
    """Blogger投稿クラス（PDFより継承・修正）"""
    def __init__(self):
        self.service = None

    def authenticate(self):
        # GitHub Actionsのシークレットから認証情報を復元することを想定
        # 環境変数 GOOGLE_CREDENTIALS_JSON にサービスアカウントキーまたはOAuthトークンJSONが入っていると仮定
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not creds_json:
            raise Exception("環境変数 GOOGLE_CREDENTIALS_JSON が設定されていません")
            
        # ここでは簡易的にService Accountまたは保存済みTokenを使用するロジック
        # 実際にはOAuth2.0のリフレッシュトークンフローなどがGitHub Actionsでは一般的
        try:
            from google.oauth2 import service_account
            import json
            info = json.loads(creds_json)
            # サービスアカウントの場合
            if 'type' in info and info['type'] == 'service_account':
                 creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            else:
                # ユーザー認証情報（token.jsonの中身など）の場合
                creds = Credentials.from_authorized_user_info(info, SCOPES)
            
            self.service = build('blogger', 'v3', credentials=creds)
        except Exception as e:
            print(f"認証エラー: {e}")
            raise

    def post_to_blog(self, blog_id, title, content, labels):
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
        except Exception as e:
            print(f"投稿エラー: {e}")
            raise

def main():
    # 環境変数のチェック
    blog_id = os.environ.get('BLOG_ID')
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    
    if not blog_id:
        print("Error: BLOG_ID is missing.")
        return # テスト実行のためExitしない場合もあるが、本番はExit

    print("--- 暦自動投稿システム起動 ---")
    
    generator = ComprehensiveCalendarGenerator(api_key=gemini_api_key)
    post_data = generator.generate_full_html()
    
    print(f"記事生成完了: {post_data['title']}")
    
    # 投稿処理
    # ローカルテストなどで認証情報がない場合はスキップ
    if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
        poster = BloggerPoster()
        poster.authenticate()
        poster.post_to_blog(blog_id, post_data['title'], post_data['content'], post_data['labels'])
    else:
        print("認証情報がないため、投稿をスキップしました（ドライラン）。")
        # デバッグ用にHTMLファイルを出力してもよい
        # with open("debug_post.html", "w") as f: f.write(post_data['content'])

if __name__ == "__main__":
    main()
