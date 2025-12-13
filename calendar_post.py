#!/usr/bin/env python3
"""
Gemini API利用可能モデル確認スクリプト
"""
import os
import requests

api_key = os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("GEMINI_API_KEYが設定されていません")
    exit(1)

# 利用可能なモデルをリスト
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

response = requests.get(url)

if response.status_code == 200:
    models = response.json()
    print("利用可能なモデル:")
    print("=" * 60)
    for model in models.get('models', []):
        name = model.get('name', '')
        display_name = model.get('displayName', '')
        supported_methods = model.get('supportedGenerationMethods', [])
        
        if 'generateContent' in supported_methods:
            print(f"✓ {name}")
            print(f"  表示名: {display_name}")
            print(f"  サポート: {', '.join(supported_methods)}")
            print()
else:
    print(f"エラー: {response.status_code}")
    print(response.text)
