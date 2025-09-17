import os, time, requests, feedparser
from feedgen.feed import FeedGenerator
from dateutil import parser as dateparser

SOURCE = "https://feeds.megaphone.fm/tnm5702656702"
NEW_TITLE = "The Adventures of Pockets"
CHANNEL_IMAGE = "https://purplerocketpodcast.com/wp-content/uploads/2022/11/Pockets-Final-Logo-e1685984603306.png"
OUTFILE = "rss.xml"

# --- tweak these if you want different filtering rules ---
FILTER_ANY_KEYWORDS = ["pockets"]       # keep episodes whose title/summary includes any of these
MIN_ITEMS = 1                            # fail-safe: publish even if only 1 match
# ---------------------------------------------------------

def parse_pubdate(entry):
    if getattr(entry, "published_parsed", None):
        ts = time.mktime(entry.published_parsed)
        iso_s = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.published_parsed)
        return ts, iso_s
    if getattr(entry, "updated_parsed", None):
        ts = time.mktime(entry.updated_parsed)
        iso_s = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.updated_parsed)
        return ts, iso_s
    for field in ("published", "pubDate", "updated"):
        if getattr(entry, field, None):
            try:
                dt = dateparser.parse(getattr(entry, field))
                ts = dt.timestamp()
                iso_s = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
                return ts, iso_s
            except Exception:
                pass
    now = time.gmtime()
    return time.time(), time.strftime("%a, %d %b %Y %H:%M:%S +0000", now)

def keep_entry(e):
    text = (e.get("title","") + " " + e.get("summary","")).lower()
    return any(k.lower() in text for k in FILTER_ANY_KEYWORDS)

def main():
    # fetch source
    xml = requests.get(SOURCE, timeout=30).text
    d = feedparser.parse(xml)

    # build new channel
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.title(NEW_TITLE)
    fg.link(href=d.feed.get('link', 'https://purplerocketpodcast.com'), rel='alternate')
    fg.description(d.feed.get('subtitle') or d.feed.get('description') or NEW_TITLE)
    fg.image(url=CHANNEL_IMAGE)
    # also set itunes:image for podcast apps that prefer it
    fg.podcast.itunes_image(CHANNEL_IMAGE)

    # filter + collect
    entries = []
    for e in d.entries:
        if keep_entry(e):
            ts, pub_iso = parse_pubdate(e)
            entries.append((ts, pub_iso, e))

    # if filter found nothing (name differenc
