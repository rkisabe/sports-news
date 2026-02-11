#!/usr/bin/env python3
"""
日本プロスポーツニュースポータル - スクレイパー
各チームの最新ニュースを収集してJSON形式で保存
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import feedparser
from typing import List, Dict
import re

class SportsNewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.news_data = {
            'npb': [],
            'jleague': [],
            'bleague': [],
            'updated_at': datetime.now().isoformat()
        }
    
    def scrape_rss(self, url: str, team_name: str, league: str) -> List[Dict]:
        """RSSフィードから最新ニュースを取得"""
        try:
            feed = feedparser.parse(url)
            news_items = []
            
            for entry in feed.entries[:5]:  # 最新5件
                news_items.append({
                    'team': team_name,
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', '')[:200]
                })
            
            return news_items
        except Exception as e:
            print(f"RSS取得エラー ({team_name}): {e}")
            return []
    
    def scrape_website(self, url: str, team_name: str, league: str) -> List[Dict]:
        """Webサイトから最新ニュースを取得（RSS非対応の場合）"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            
            # 一般的なニュース要素のパターンを検索
            news_links = soup.find_all('a', href=True, limit=10)
            
            for link in news_links:
                title = link.get_text(strip=True)
                href = link['href']
                
                # URLを絶対パスに変換
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                
                if title and len(title) > 10:  # タイトルが意味のある長さ
                    news_items.append({
                        'team': team_name,
                        'title': title,
                        'link': href,
                        'published': datetime.now().strftime('%Y-%m-%d'),
                        'summary': ''
                    })
                    
                    if len(news_items) >= 3:
                        break
            
            return news_items
        except Exception as e:
            print(f"スクレイピングエラー ({team_name}): {e}")
            return []
    
    def scrape_npb(self):
        """NPB12球団のニュースを取得"""
        npb_teams = {
            '読売ジャイアンツ': 'https://www.giants.jp/',
            '阪神タイガース': 'https://hanshintigers.jp/',
            '中日ドラゴンズ': 'https://dragons.jp/',
            '横浜DeNA': 'https://www.baystars.co.jp/',
            '広島カープ': 'https://www.carp.co.jp/',
            'ヤクルト': 'https://www.yakult-swallows.co.jp/',
            'ソフトバンク': 'https://www.softbankhawks.co.jp/',
            'ロッテ': 'https://www.marines.co.jp/',
            '西武': 'https://www.seibulions.jp/',
            '楽天': 'https://www.rakuteneagles.jp/',
            '日本ハム': 'https://www.fighters.co.jp/',
            'オリックス': 'https://www.buffaloes.co.jp/'
        }
        
        print("NPBニュースを取得中...")
        for team, url in npb_teams.items():
            # RSSフィードを試す（多くのチームが対応）
            rss_url = f"{url}rss.xml"
            news = self.scrape_rss(rss_url, team, 'npb')
            
            if not news:
                # RSSがない場合は直接スクレイピング
                news = self.scrape_website(url + 'news/', team, 'npb')
            
            self.news_data['npb'].extend(news)
            time.sleep(1)  # サーバー負荷軽減
    
    def scrape_jleague(self):
        """Jリーグの主要クラブニュースを取得（全60は負荷が高いため主要クラブのみ）"""
        jleague_teams = {
            '浦和レッズ': 'https://www.urawa-reds.co.jp/',
            '鹿島アントラーズ': 'https://www.so-net.ne.jp/antlers/',
            '川崎フロンターレ': 'https://www.frontale.co.jp/',
            '横浜F・マリノス': 'https://www.f-marinos.com/',
            'FC東京': 'https://www.fctokyo.co.jp/',
            'ガンバ大阪': 'https://www.gamba-osaka.net/',
            'セレッソ大阪': 'https://www.cerezo.jp/',
            'ヴィッセル神戸': 'https://www.vissel-kobe.co.jp/',
            '名古屋グランパス': 'https://nagoya-grampus.jp/',
            'サンフレッチェ広島': 'https://www.sanfrecce.co.jp/'
        }
        
        print("Jリーグニュースを取得中...")
        for team, url in jleague_teams.items():
            news = self.scrape_website(url + 'news/', team, 'jleague')
            self.news_data['jleague'].extend(news)
            time.sleep(1)
    
    def scrape_bleague(self):
        """Bリーグの主要チームニュースを取得"""
        bleague_teams = {
            '千葉ジェッツ': 'https://chibajets.jp/',
            '宇都宮ブレックス': 'https://www.brex.jp/',
            'アルバルク東京': 'https://www.alvark-tokyo.jp/',
            '川崎ブレイブサンダース': 'https://kawasaki-bravethunders.com/',
            '横浜ビー・コルセアーズ': 'https://b-corsairs.com/',
            '琉球ゴールデンキングス': 'https://goldenkings.jp/',
            '三河シーホース': 'https://www.seahorses-mikawa.com/',
            '名古屋ダイヤモンドドルフィンズ': 'https://www.dolphins.co.jp/',
            '大阪エヴェッサ': 'https://evessa.com/',
            '広島ドラゴンフライズ': 'https://hiroshimadragonflies.com/'
        }
        
        print("Bリーグニュースを取得中...")
        for team, url in bleague_teams.items():
            news = self.scrape_website(url + 'news/', team, 'bleague')
            self.news_data['bleague'].extend(news)
            time.sleep(1)
    
    def save_data(self, filename='news_data.json'):
        """収集したデータをJSON形式で保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.news_data, f, ensure_ascii=False, indent=2)
        print(f"\nデータを {filename} に保存しました")
        print(f"NPB: {len(self.news_data['npb'])}件")
        print(f"Jリーグ: {len(self.news_data['jleague'])}件")
        print(f"Bリーグ: {len(self.news_data['bleague'])}件")

def main():
    scraper = SportsNewsScraper()
    
    print("=" * 50)
    print("日本プロスポーツニュース収集開始")
    print("=" * 50)
    
    scraper.scrape_npb()
    scraper.scrape_jleague()
    scraper.scrape_bleague()
    scraper.save_data()
    
    print("\n完了!")

if __name__ == '__main__':
    main()
