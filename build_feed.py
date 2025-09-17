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

    # if filter found nothing (name differences), fall back to all items
    if len(entries) < MIN_ITEMS:
        entries = []
        for e in d.entries:
            ts, pub_iso = parse_pubdate(e)
            entries.append((ts, pub_iso, e))

    # sort oldest -> newest
    entries.sort(key=lambda x: x[0])

    # write items
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

        itunes_duration = e.get('itunes_duration') or e.get('itunes:duration')
        if itunes_duration:
            fg.podcast.itunes_duration(itunes_duration)

    fg.rss_file(OUTFILE, pretty=True)

if __name__ == "__main__":
    main()
