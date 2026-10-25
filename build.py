import datetime as dt
import email.utils
import os
import pathlib
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import requests

REPO = os.environ['GITHUB_REPOSITORY']
BASE = 'https://jnradio.oss-cn-hangzhou.aliyuncs.com/jnrjj'
SITE = pathlib.Path('site')
SITE.mkdir(exist_ok=True)
FEED = SITE / 'feed.xml'
CN = dt.timezone(dt.timedelta(hours=8))


def candidate(day):
    s = day.isoformat()
    return f'{BASE}/{day:%Y/%m/}{day:%d}_{s}T110000Z_{s}T123000Z.m3u8'


def valid_playlist(url):
    try:
        r = requests.get(url, timeout=20)
        return r.ok and r.text.lstrip().startswith('#EXTM3U') and '#EXTINF' in r.text
    except requests.RequestException:
        return False


def release_exists(tag):
    p = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO], capture_output=True)
    return p.returncode == 0


def publish(day, url):
    tag = f'episode-{day.isoformat()}'
    if release_exists(tag):
        return
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / 'audio.mp3'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', url,
                        '-vn', '-codec:a', 'libmp3lame', '-b:a', '48k', str(path)], check=True, timeout=1200)
        if path.stat().st_size < 100_000:
            raise RuntimeError(f'Audio unexpectedly small: {day}')
        subprocess.run(['gh', 'release', 'create', tag, str(path), '--repo', REPO,
                        '--title', f'以案说法 {day.isoformat()}', '--notes', f'节目日期：{day.isoformat()}'], check=True)


def build():
    today = dt.datetime.now(CN).date()
    # Initial historical discovery is deliberately limited. Do not assume all dates exist.
    dates = [today - dt.timedelta(days=i) for i in range(15)]
    dates.reverse()
    existing = {}
    if FEED.exists():
        try:
            root = ET.parse(FEED).getroot()
            for item in root.findall('./channel/item'):
                guid = item.findtext('guid')
                if guid:
                    existing[guid] = item
        except ET.ParseError:
            pass
    new = 0
    for day in dates:
        tag = f'episode-{day.isoformat()}'
        if tag in existing:
            continue
        if new >= 3:  # Bound each scheduled run's compute/storage use.
            break
        url = candidate(day)
        if not valid_playlist(url):
            continue
        try:
            publish(day, url)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as exc:
            print(f'Skipping {day}: {exc}', flush=True)
            continue
        item = ET.Element('item')
        ET.SubElement(item, 'title').text = f'以案说法 {day:%Y-%m-%d}'
        ET.SubElement(item, 'description').text = f'《以案说法》{day:%Y年%m月%d日}节目。'
        ET.SubElement(item, 'guid', isPermaLink='false').text = tag
        ET.SubElement(item, 'pubDate').text = email.utils.format_datetime(dt.datetime.combine(day, dt.time(19), CN))
        link = f'https://github.com/{REPO}/releases/download/{tag}/audio.mp3'
        ET.SubElement(item, 'enclosure', url=link, type='audio/mpeg', length='0')
        # RSS enclosure length should be the actual file size; retrieve from release metadata.
        info = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO, '--json', 'assets', '--jq', '.assets[] | select(.name == "audio.mp3") | .size'], capture_output=True, text=True)
        if info.returncode == 0 and info.stdout.strip().isdigit():
            item.find('enclosure').set('length', info.stdout.strip())
        existing[tag] = item
        new += 1
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', '以案说法｜叮咚FM（非官方订阅）'),
                       ('link', 'https://www.dingdongfm.cn/web/wx/columnIndex?columnId=6b853bfb-28cb-5f56-1676-8993ddd9af85'),
                       ('description', '《以案说法》非官方个人使用的音频订阅源，节目版权归原权利人所有。'),
                       ('language', 'zh-cn')]:
        ET.SubElement(channel, key).text = value
    for tag in sorted(existing, reverse=True)[:60]:
        channel.append(existing[tag])
    ET.indent(rss, space='  ')
    ET.ElementTree(rss).write(FEED, encoding='utf-8', xml_declaration=True)
    print(f'Feed contains {len(existing)} known episodes; {new} newly processed.')


if __name__ == '__main__':
    build()
