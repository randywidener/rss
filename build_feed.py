import time, requests, feedparser
from feedgen.feed import FeedGenerator
from dateutil import parser as dateparser

SOURCE = "https://feeds.megaphone.fm/tnm5702656702"
NEW_TITLE = "The Adventures of Pockets"
CHANNEL_IMAGE = "https://purplerocketpodcast.com/wp-content/uploads/2022/11/Pockets-Final-Logo-e1685984603306.png"
OUTFILE = "rss.xml"

KEYWORDS = ["pockets", "the adventures of pockets"]  # case-insensitive match in title/summary/categories

def parse_pubdate(entry):
    if getattr(entry, "published_parsed", None):
        ts = time.mktime(entry.published_parsed)
        rfc = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.published_parsed)
        return ts, rfc
    if getattr(entry, "updated_parsed", None):
        ts = time.mktime(entry.updated_parsed)
        rfc = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.updated_parsed)
        return ts, rfc
    for f in ("published", "pubDate", "updated"):
        if getattr(entry, f, None):
            try:
                dt = dateparser.parse(getattr(entry, f))
                return dt.timestamp(), dt.strftime("%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                pass
    now = time.gmtime()
    return time.time(), time.strftime("%a, %d %b %Y %H:%M:%S +0000", now)

def matches_keywords(e):
    hay = " ".join([
        e.get("title",""),
        e.get("summary",""),
        e.get("subtitle",""),
    ]).lower()
    if getattr(e, "tags", None):
        cats = " ".join([t.get("term","") for t in e.tags if isinstance(t, dict)])
        hay += " " + cats.lower()
    return any(k in hay for k in KEYWORDS)

def main():
    xml = requests.get(SOURCE, timeout=30).text
    d = feedparser.parse(xml)

    # channel
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.title(NEW_TITLE)
    fg.link(href=d.feed.get('link', 'https://purplerocketpodcast.com'), rel='alternate')
    fg.description(d.feed.get('subtitle') or d.feed.get('description') or NEW_TITLE)
    fg.image(url=CHANNEL_IMAGE)
    fg.podcast.itunes_image(CHANNEL_IMAGE)

    # filter + sort
    entries = []
    for e in d.entries:
        if matches_keywords(e):
            ts, pub_iso = parse_pubdate(e)
            entries.append((ts, pub_iso, e))
    # If nothing matched, comment out the next 4 lines if you prefer an empty feed instead of fallback
    if not entries:
        for e in d.entries:
            ts, pub_iso = parse_pubdate(e)
            entries.append((ts, pub_iso, e))

    entries.sort(key=lambda x: x[0])  # oldest → newest

    # items
    for _, pub_iso, e in entries:
        fe = fg.add_entry()
        fe.title(e.get('title', 'Untitled'))
        fe.link(href=e.get('link') or d.feed.get('link') or 'https://purplerocketpodcast.com')
        fe.description(e.get('summary') or e.get('subtitle') or '')
        fe.pubDate(pub_iso)
        guid = e.get('id') or e.get('guid') or (e.get('link') or '') + pub_iso
        fe.guid(guid, permalink=False)

        encs = getattr(e, 'enclosures', []) or []
        if encs:
            href = encs[0].get('href')
            mime = encs[0].get('type', 'audio/mpeg')
            length = encs[0].get('length') or '0'
            if href:
                fe.enclosure(href, length, mime)

        # item-level iTunes duration (if present)
        itunes_duration = e.get('itunes_duration') or e.get('itunes:duration')
        if itunes_duration:
            fe.podcast.itunes_duration(itunes_duration)

    fg.rss_file(OUTFILE, pretty=True)

if __name__ == "__main__":
    main()
