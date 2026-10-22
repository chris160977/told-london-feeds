#!/usr/bin/env python3
"""Builds Told London's product feed files from the live shop (toldlondon.com): the Awin CSV files, and Google-format
TSV files for networks that read Google's column names (Addrevenue, from 20 Oct 2026: brand, shipping).

Each feed is rendered by the shop's theme from the shop's live products, prices, stock and translations. This script
fetches each one, refuses it unless it is complete (right header, at least 25 rows, no error line), and only then
replaces the file here. GitHub Pages serves the folder, so partners always read a complete, current file.
Runs daily from .github/workflows/build.yml. Nothing here is private: it is the same data the public shop shows.
"""
import csv, io, os, subprocess, sys, time, datetime

FEEDS = {
    'told-feed-awin-gbp-eng.csv': 'https://toldlondon.com/collections/all?view=told-feed-awin&country=GB',
    'told-feed-awin-usd-eng.csv': 'https://toldlondon.com/collections/all?view=told-feed-awin&country=US',
    'told-feed-awin-eur-eng.csv': 'https://toldlondon.com/collections/all?view=told-feed-awin&country=IE',
    'told-feed-awin-eur-ita.csv': 'https://toldlondon.com/it/collections/all?view=told-feed-awin&country=IT',
    'told-feed-awin-eur-fra.csv': 'https://toldlondon.com/fr/collections/all?view=told-feed-awin&country=FR',
    'told-feed-awin-eur-nld.csv': 'https://toldlondon.com/nl/collections/all?view=told-feed-awin&country=NL',
    'told-feed-awin-eur-spa.csv': 'https://toldlondon.com/es/collections/all?view=told-feed-awin&country=ES',
    'told-feed-awin-eur-fin.csv': 'https://toldlondon.com/fi/collections/all?view=told-feed-awin&country=FI',
    'told-feed-awin-dkk-dan.csv': 'https://toldlondon.com/da/collections/all?view=told-feed-awin&country=DK',
    'told-feed-awin-sek-swe.csv': 'https://toldlondon.com/sv/collections/all?view=told-feed-awin&country=SE',
    'told-feed-awin-eur-deu.csv': 'https://toldlondon.com/de/collections/all?view=told-feed-awin&country=DE',
    'told-feed-awin-nok-nor.csv': 'https://toldlondon.com/nb/collections/all?view=told-feed-awin&country=NO',
}
# Google-format TSV (theme template collection.told-feed-awin-google), same products and prices as the Awin files.
GOOGLE_FEEDS = {
    'told-feed-google-gbp-eng.tsv': 'https://toldlondon.com/collections/all?view=told-feed-awin-google&country=GB',
    'told-feed-google-eur-fra.tsv': 'https://toldlondon.com/fr/collections/all?view=told-feed-awin-google&country=FR',
    'told-feed-google-eur-deu.tsv': 'https://toldlondon.com/de/collections/all?view=told-feed-awin-google&country=DE',
    'told-feed-google-eur-ita.tsv': 'https://toldlondon.com/it/collections/all?view=told-feed-awin-google&country=IT',
    'told-feed-google-eur-nld.tsv': 'https://toldlondon.com/nl/collections/all?view=told-feed-awin-google&country=NL',
    'told-feed-google-eur-spa.tsv': 'https://toldlondon.com/es/collections/all?view=told-feed-awin-google&country=ES',
    # Added 20 Oct 2026 for Addrevenue (Christopher's approval via the Addrevenue session). SE and DK are priced in
    # local currency, so their shipping column is blank; Addrevenue's per-market shipping field covers it.
    'told-feed-google-sek-swe.tsv': 'https://toldlondon.com/sv/collections/all?view=told-feed-awin-google&country=SE',
    'told-feed-google-dkk-dan.tsv': 'https://toldlondon.com/da/collections/all?view=told-feed-awin-google&country=DK',
    'told-feed-google-eur-eng.tsv': 'https://toldlondon.com/collections/all?view=told-feed-awin-google&country=IE',
    # Added 21 Oct 2026 for Addrevenue (Christopher's approval via the Addrevenue session); NO is priced in NOK,
    # so its shipping column is blank.
    'told-feed-google-eur-fin.tsv': 'https://toldlondon.com/fi/collections/all?view=told-feed-awin-google&country=FI',
    'told-feed-google-nok-nor.tsv': 'https://toldlondon.com/nb/collections/all?view=told-feed-awin-google&country=NO',
    # Google Merchant Centre supplemental (product highlights, details, material), English; keyed on Merchant Centre's
    # own ids (shopify_ZZ_<product>_<variant>). Theme template collection.told-feed-google-extra, 20 Oct 2026.
    'told-feed-google-extra-eng.tsv': 'https://toldlondon.com/collections/all?view=told-feed-google-extra&country=GB',
    # Translated (Translations 10, 22 Oct 2026); same ids, highlights in each language.
    'told-feed-google-extra-ita.tsv': 'https://toldlondon.com/it/collections/all?view=told-feed-google-extra&country=IT',
    'told-feed-google-extra-fra.tsv': 'https://toldlondon.com/fr/collections/all?view=told-feed-google-extra&country=FR',
    'told-feed-google-extra-deu.tsv': 'https://toldlondon.com/de/collections/all?view=told-feed-google-extra&country=DE',
    'told-feed-google-extra-spa.tsv': 'https://toldlondon.com/es/collections/all?view=told-feed-google-extra&country=ES',
    'told-feed-google-extra-nld.tsv': 'https://toldlondon.com/nl/collections/all?view=told-feed-google-extra&country=NL',
    'told-feed-google-extra-fin.tsv': 'https://toldlondon.com/fi/collections/all?view=told-feed-google-extra&country=FI',
    'told-feed-google-extra-dan.tsv': 'https://toldlondon.com/da/collections/all?view=told-feed-google-extra&country=DK',
    'told-feed-google-extra-swe.tsv': 'https://toldlondon.com/sv/collections/all?view=told-feed-google-extra&country=SE',
    'told-feed-google-extra-nor.tsv': 'https://toldlondon.com/nb/collections/all?view=told-feed-google-extra&country=NO',
    # The last eight published languages (Translations 10, 22 Oct 2026). zho-hans is Simplified, zho-hant Traditional.
    'told-feed-google-extra-por.tsv': 'https://toldlondon.com/pt/collections/all?view=told-feed-google-extra&country=PT',
    'told-feed-google-extra-lit.tsv': 'https://toldlondon.com/lt/collections/all?view=told-feed-google-extra&country=LT',
    'told-feed-google-extra-pol.tsv': 'https://toldlondon.com/pl/collections/all?view=told-feed-google-extra&country=PL',
    'told-feed-google-extra-ara.tsv': 'https://toldlondon.com/ar/collections/all?view=told-feed-google-extra&country=AE',
    'told-feed-google-extra-jpn.tsv': 'https://toldlondon.com/ja/collections/all?view=told-feed-google-extra&country=JP',
    'told-feed-google-extra-kor.tsv': 'https://toldlondon.com/ko/collections/all?view=told-feed-google-extra&country=KR',
    'told-feed-google-extra-zho-hans.tsv': 'https://toldlondon.com/zh-hans/collections/all?view=told-feed-google-extra&country=SG',
    'told-feed-google-extra-zho-hant.tsv': 'https://toldlondon.com/zh-hant/collections/all?view=told-feed-google-extra&country=HK',
}
UA = 'Mozilla/5.0 (Told London feed builder)'
MIN_ROWS = 25


def fetch(url):
    for attempt in range(4):
        r = subprocess.run(['curl', '-s', '-L', '--max-time', '60', '-A', UA, '-w', '\n%{http_code}', url],
                           capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        code = int(code or 0)
        if code in (429, 502, 503, 504) and attempt < 3:
            time.sleep(20 * (attempt + 1))
            continue
        return code, body
    return 0, ''


def main():
    failed = []
    for name, url in list(FEEDS.items()) + list(GOOGLE_FEEDS.items()):
        code, body = fetch(url)
        problem = None
        if code != 200 or not body.strip() or body.startswith('ERROR'):
            problem = 'HTTP %s: %r' % (code, body[:80])
        elif name.endswith('.tsv'):
            lines = [l for l in body.splitlines() if l.strip()]
            head = lines[0].split('\t') if lines else []
            if name.startswith('told-feed-google-extra'):
                if head[:3] != ['id', 'material', 'product_highlight'] or 'product_detail' not in head:
                    problem = 'unexpected header'
            elif head[:5] != ['id', 'item_group_id', 'title', 'description', 'link'] or 'brand' not in head \
                    or 'shipping' not in head:
                problem = 'unexpected header'
            elif len(lines) - 1 < MIN_ROWS:
                problem = 'only %d rows' % (len(lines) - 1)
            elif any(len(l.split('\t')) != len(head) for l in lines[1:]):
                problem = 'a row has the wrong number of columns'
        else:
            rows = list(csv.reader(io.StringIO(body)))
            if not rows or rows[0][:3] != ['product_id', 'product_name', 'description']:
                problem = 'unexpected header'
            elif len([r for r in rows[1:] if r]) < MIN_ROWS:
                problem = 'only %d rows' % len(rows[1:])
        if problem:
            print('%s: NOT replaced (%s); the previous file stays' % (name, problem))
            failed.append(name)
            continue
        if name.endswith('.tsv'):
            # The theme template leaves a blank line after every row; some importers (Addrevenue) count each one
            # as an empty product, so write only the non-empty lines.
            body = '\n'.join(l for l in body.splitlines() if l.strip()) + '\n'
        with open(name, 'w', encoding='utf-8', newline='') as f:
            f.write(body)
        print('%s: %d bytes' % (name, len(body.encode())))
        time.sleep(1)
    with open('last-built.txt', 'w') as f:
        f.write(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + '\n')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
