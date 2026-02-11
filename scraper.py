#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本プロスポーツニュースポータル - スクレイパー（デバッグ版）
各チームの最新ニュースを収集してJSON形式で保存
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import feedparser
from typing import List, Dict
import sys

# エンコーディング設定
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class SportsNewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.news_data = {
            'npb': [],
            'jleague': [],
            'bleague': [],
            'updated_at': datetime.now().isoformat()
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def safe_request(self, url: str, timeout: int = 10) -> requests.Response:
        """安全にHTTPリクエストを実行"""
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ リクエストエラー: {e}")
            return None
    
    def scrape_rss(self, url: str, team_name: str) -> List[Dict]:
        """RSSフィードから最新ニュースを取得"""
        try:
            print(f"  📡 RSS取得中: {url}")
            feed = feedparser.parse(url)
            
            if not feed.entries:
                print(f"  ⚠️ RSSエントリーが見つかりません")
                return []
            
            news_items = []
            for entry in feed.entries[:5]:  # 最新5件
                try:
                    news_items.append({
                        'team': team_name,
                        'title': entry.get('title', '').strip(),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', datetime.now().strftime('%Y-%m-%d')),
                        'summary': entry.get('summary', '')[:200]
                    })
                except Exception as e:
                    print(f"  ⚠️ エントリー処理エラー: {e}")
                    continue
            
            print(f"  ✅ {len(news_items)}件取得")
            return news_items
            
        except Exception as e:
            print(f"  ❌ RSS取得エラー: {e}")
            return []
    
    def scrape_generic_news(self, base_url: str, team_name: str) -> List[Dict]:
        """一般的なニュースページから情報を取得"""
        news_urls = [
            f"{base_url}news/",
            f"{base_url}news.html",
            f"{base_url}information/",
            base_url
        ]
        
        for url in news_urls:
            try:
                print(f"  🔍 ページ確認中: {url}")
                response = self.safe_request(url)
                
                if not response:
                    continue
                
                response.encoding = response.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # よくあるニュースコンテナのパターン
                news_containers = (
                    soup.find_all('article', limit=5) or
                    soup.find_all('div', class_=lambda x: x and ('news' in x.lower() or 'article' in x.lower()), limit=5) or
                    soup.find_all('li', class_=lambda x: x and ('news' in x.lower() or 'item' in x.lower()), limit=5)
                )
                
                news_items = []
                for container in news_containers:
                    link_tag = container.find('a', href=True)
                    if not link_tag:
                        continue
                    
                    title = link_tag.get_text(strip=True) or container.get_text(strip=True)[:100]
                    href = link_tag['href']
                    
                    # 相対URLを絶対URLに変換
                    if href.startswith('/'):
                        from urllib.parse import urljoin
                        href = urljoin(base_url, href)
                    elif not href.startswith('http'):
                        href = base_url.rstrip('/') + '/' + href.lstrip('/')
                    
                    # 日付を探す
                    date_text = ''
                    date_elem = container.find(['time', 'span', 'div'], class_=lambda x: x and ('date' in str(x).lower() or 'time' in str(x).lower()))
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                    
                    if title and len(title) > 5:
                        news_items.append({
                            'team': team_name,
                            'title': title[:200],
                            'link': href,
                            'published': date_text or datetime.now().strftime('%Y-%m-%d'),
                            'summary': ''
                        })
                
                if news_items:
                    print(f"  ✅ {len(news_items)}件取得")
                    return news_items[:3]  # 最大3件
                    
            except Exception as e:
                print(f"  ⚠️ スクレイピングエラー ({url}): {e}")
                continue
        
        print(f"  ❌ ニュースが見つかりませんでした")
        return []
    
    def scrape_team(self, team_name: str, base_url: str, rss_paths: List[str] = None) -> List[Dict]:
        """チームのニュースを取得（RSS優先、失敗時はスクレイピング）"""
        print(f"\n🏆 {team_name}")
        
        # RSS試行
        if rss_paths:
            for rss_path in rss_paths:
                rss_url = base_url.rstrip('/') + '/' + rss_path.lstrip('/')
                news = self.scrape_rss(rss_url, team_name)
                if news:
                    return news
        
        # デフォルトRSS試行
        for rss_path in ['rss.xml', 'feed', 'news/rss', 'rss/news.xml']:
            rss_url = base_url.rstrip('/') + '/' + rss_path
            news = self.scrape_rss(rss_url, team_name)
            if news:
                return news
        
        # スクレイピング試行
        return self.scrape_generic_news(base_url, team_name)
    
    def scrape_npb(self):
        """NPB12球団のニュースを取得"""
        print("\n" + "="*60)
        print("⚾ NPB（プロ野球）ニュース収集開始")
        print("="*60)
        
        npb_teams = {
            '読売ジャイアンツ': ('https://www.giants.jp/', ['news/rss.xml']),
            '阪神タイガース': ('https://hanshintigers.jp/', ['news/rss.xml']),
            '中日ドラゴンズ': ('https://dragons.jp/', ['news/rss']),
            '横浜DeNA': ('https://www.baystars.co.jp/', ['news/rss.xml']),
            '広島カープ': ('https://www.carp.co.jp/', None),
            'ヤクルト': ('https://www.yakult-swallows.co.jp/', None),
            'ソフトバンク': ('https://www.softbankhawks.co.jp/', None),
            'ロッテ': ('https://www.marines.co.jp/', None),
            '西武': ('https://www.seibulions.jp/', None),
            '楽天': ('https://www.rakuteneagles.jp/', None),
            '日本ハム': ('https://www.fighters.co.jp/', None),
            'オリックス': ('https://www.buffaloes.co.jp/', None)
        }
        
        for team, (url, rss_paths) in npb_teams.items():
            try:
                news = self.scrape_team(team, url, rss_paths)
                self.news_data['npb'].extend(news)
                time.sleep(2)  # サーバー負荷軽減
            except Exception as e:
                print(f"  ❌ {team} でエラー: {e}")
                continue
    
    def scrape_jleague(self):
        """Jリーグの主要クラブニュースを取得"""
        print("\n" + "="*60)
        print("⚽ Jリーグニュース収集開始")
        print("="*60)
        
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
        
        for team, url in jleague_teams.items():
            try:
                news = self.scrape_team(team, url)
                self.news_data['jleague'].extend(news)
                time.sleep(2)
            except Exception as e:
                print(f"  ❌ {team} でエラー: {e}")
                continue
    
    def scrape_bleague(self):
        """Bリーグの主要チームニュースを取得"""
        print("\n" + "="*60)
        print("🏀 Bリーグニュース収集開始")
        print("="*60)
        
        bleague_teams = {
            '千葉ジェッツ': 'https://chibajets.jp/',
            '宇都宮ブレックス': 'https://www.brex.jp/',
            'アルバルク東京': 'https://www.alvark-tokyo.jp/',
            '川崎ブレイブサンダース': 'https://kawasaki-bravethunders.com/',
            '横浜ビー・コルセアーズ': 'https://b-corsairs.com/',
            '琉球ゴールデンキングス': 'https://goldenkings.jp/',
            'シーホース三河': 'https://www.seahorses-mikawa.com/',
            '名古屋ダイヤモンドドルフィンズ': 'https://www.dolphins.co.jp/',
            '大阪エヴェッサ': 'https://evessa.com/',
            '広島ドラゴンフライズ': 'https://hiroshimadragonflies.com/'
        }
        
        for team, url in bleague_teams.items():
            try:
                news = self.scrape_team(team, url)
                self.news_data['bleague'].extend(news)
                time.sleep(2)
            except Exception as e:
                print(f"  ❌ {team} でエラー: {e}")
                continue
    
    def save_data(self, filename='news_data.json'):
        """収集したデータをJSON形式で保存"""
        try:
            # 最低限のデータを確保
            if not self.news_data['npb'] and not self.news_data['jleague'] and not self.news_data['bleague']:
                print("\n⚠️ 警告: ニュースデータが1件も取得できませんでした")
                print("サンプルデータを生成します...")
                self.generate_sample_data()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.news_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n" + "="*60)
            print(f"💾 データを {filename} に保存しました")
            print(f"  NPB: {len(self.news_data['npb'])}件")
            print(f"  Jリーグ: {len(self.news_data['jleague'])}件")
            print(f"  Bリーグ: {len(self.news_data['bleague'])}件")
            print(f"  合計: {len(self.news_data['npb']) + len(self.news_data['jleague']) + len(self.news_data['bleague'])}件")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ データ保存エラー: {e}")
            sys.exit(1)
    
    def generate_sample_data(self):
        """サンプルデータを生成（エラー時のフォールバック）"""
        self.news_data = {
            'npb': [
                {
                    'team': '読売ジャイアンツ',
                    'title': 'ニュース取得に失敗しました（サンプルデータ）',
                    'link': 'https://www.giants.jp/',
                    'published': datetime.now().strftime('%Y-%m-%d'),
                    'summary': 'データ収集時にエラーが発生しました。後ほど再試行してください。'
                }
            ],
            'jleague': [
                {
                    'team': '浦和レッズ',
                    'title': 'ニュース取得に失敗しました（サンプルデータ）',
                    'link': 'https://www.urawa-reds.co.jp/',
                    'published': datetime.now().strftime('%Y-%m-%d'),
                    'summary': 'データ収集時にエラーが発生しました。後ほど再試行してください。'
                }
            ],
            'bleague': [
                {
                    'team': '千葉ジェッツ',
                    'title': 'ニュース取得に失敗しました（サンプルデータ）',
                    'link': 'https://chibajets.jp/',
                    'published': datetime.now().strftime('%Y-%m-%d'),
                    'summary': 'データ収集時にエラーが発生しました。後ほど再試行してください。'
                }
            ],
            'updated_at': datetime.now().isoformat()
        }

def main():
    print("\n" + "🏟️ "*20)
    print("   日本プロスポーツニュース収集ツール v2.0")
    print("🏟️ "*20 + "\n")
    
    try:
        scraper = SportsNewsScraper()
        scraper.scrape_npb()
        scraper.scrape_jleague()
        scraper.scrape_bleague()
        scraper.save_data()
        
        print("\n✨ 完了！ ✨")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
