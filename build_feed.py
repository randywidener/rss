import os
import time
import requests
import feedparser
from feedgen.feed import FeedGenerator
from dateutil import parser as dateparser

SOURCE = "https://feeds.megaphone.fm/tnm5702656702"
NEW_TITLE = "The Adventures of Pockets"
CHANNEL_IMAGE = "https://purplerocketpodcast.com/wp-content/uploads/2022/11/Pockets-Final-Logo-e1685984603306.png"
OUTFILE = "rss.xml"

def parse_pubdate(entry):
    """
    Returns a tuple (timestamp, iso_string) best-effort from RSS entry.
    Falls back through published, updated, or None.
    """
    # 1) Try structured published_parsed
    if getattr(entry, "published_parsed", None):
        ts = time.mktime(entry.published_parsed)
        iso_s = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.published_parsed)
        return ts, iso_s
    # 2) Try updated_parsed
    if getattr(entry, "updated_parsed", None):
        ts = time.mktime(entry.updated_parsed)
        iso_s = time.strftime("%a, %d %b %Y %H:%M:%S %z", entry.updated_parsed)
        return ts, iso_s
    # 3) Try raw strings
    for field in ("published", "pubDate", "updated"):
        if getattr(entry, field, None):
            try:
                dt = dateparser.parse(getattr(entry, field))
                ts = dt.timestamp()
                # RFC 2822 format
                iso_s = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
                return ts, iso_s
            except Exception:
                pass
    # 4) No date -> use now (stable but last resort)
    now = time.gmtime()
    ts = time.time()
    iso_s = time.strftime("%a, %d %b %Y %H:%M:%S +0000", now)
    return ts, iso_s

def main():
    # Fetch source feed (no caching)
    r = requests.get(SOURCE, timeout=30)
    r.raise_for_status()
    src_xml = r.text

    d = feedparser.parse(src_xml)

    # Build new feed
    fg = FeedGenerator()
    fg.load_extension('podcast')

    # Channel-level metadata
    fg.title(NEW_TITLE)
    fg.link(href=d.feed.get('link', 'https://purplerocketpodcast.com'), rel='alternate')
    fg.description(d.feed.get('subtitle') or d.feed.get('description') or NEW_TITLE)
    fg.image(url=CHANNEL_IMAGE)

    # Optional: self link (helps some readers)
    # Note: Replace the placeholder URL below *after* your first publish if you want to include it.
    # fg.link(href='https://<your-username>.github.io/<your-repo>/rss.xml', rel='self')

    # Collect entries with parsed dates
    entries = []
    for e in d.entries:
        ts, pub_iso = parse_pubdate(e)
        entries.append((ts, pub_iso, e))

    # Sort oldest -> newest
    entries.sort(key=lambda x: x[0])

    for _, pub_iso, e in entries:
        fe = fg.add_entry()
        fe.title(e.get('title', 'Untitled'))
        fe.link(href=e.get('link') or d.feed.get('link') or 'https://purplerocketpodcast.com')

        # Episode description
        desc = e.get('summary') or e.get('subtitle') or ''
        fe.description(desc)

        # Pub date
        fe.pubDate(pub_iso)

        # GUID: prefer the original guid/id; otherwise fall back to link+date combo
        guid = e.get('id') or e.get('guid') or (e.get('link') or '') + pub_iso
        fe.guid(guid, permalink=False)

        # Enclosures (audio)
        # feedparser exposes a list at e.enclosures with dicts: href, type, length
        encs = getattr(e, 'enclosures', []) or []
        if encs:
            href = encs[0].get('href')
            mime = encs[0].get('type', 'audio/mpeg')
            length = encs[0].get('length') or '0'
            if href:
                fe.enclosure(href, length, mime)

        # iTunes / podcast extras (optional; carry through if present)
        # Example: duration
        itunes_duration = e.get('itunes_duration') or e.get('itunes:duration')
        if itunes_duration:
            fe.podcast.itunes_duration(itunes_duration)

    # Write to file
    fg.rss_file(OUTFILE, pretty=True)

if __name__ == "__main__":
    main()
