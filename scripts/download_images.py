#!/usr/bin/env python3
"""
Download a list of image URLs into a target directory and produce a JSON manifest

Usage:
  python3 scripts/download_images.py --input candidates.json --target images/03_the_guillotine/02_regicide

Input JSON format (array of objects):
  [
    {"url":"https://.../File.jpg", "commons_page":"https://commons.wikimedia.org/wiki/File:...", "caption":"..."},
    ...
  ]

The script will create the target directory (if needed), download each file, try
to fetch Wikimedia Commons metadata for the file (license, artist, credit) when
possible, compute file size and sha256, and write `manifest.json` in the target.
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request


USER_AGENT = 'Mozilla/5.0 (X11; Linux)'


def download_file(url, dest_path):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as r:
        data = r.read()
    with open(dest_path, 'wb') as f:
        f.write(data)
    return len(data)


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def commons_metadata_from_url(url):
    """If the URL looks like a Wikimedia upload URL, attempt to query Commons for extmetadata."""
    parsed = urllib.parse.urlparse(url)
    if 'upload.wikimedia.org' not in parsed.netloc:
        return {}
    # last path segment is the filename
    filename = os.path.basename(parsed.path)
    # URL-decode and replace spaces with underscores
    filename = urllib.parse.unquote(filename)
    filename = filename.replace(' ', '_')
    # Build a File: title
    file_title = 'File:' + filename
    api = 'https://commons.wikimedia.org/w/api.php'
    params = {
        'action': 'query',
        'format': 'json',
        'titles': file_title,
        'prop': 'imageinfo',
        'iiprop': 'extmetadata'
    }
    urlq = api + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(urlq, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            obj = json.load(r)
    except Exception:
        return {}
    pages = obj.get('query', {}).get('pages', {})
    for p in pages.values():
        ii = p.get('imageinfo', [{}])[0]
        md = ii.get('extmetadata', {})
        # extract a few useful fields
        out = {}
        def get(mdkey):
            return md.get(mdkey, {}).get('value', '')
        out['LicenseShortName'] = get('LicenseShortName')
        out['LicenseUrl'] = get('LicenseUrl')
        out['Artist'] = get('Artist')
        out['Credit'] = get('Credit')
        out['ImageDescription'] = get('ImageDescription')
        return out
    return {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', '-i', required=True, help='Input JSON file with candidate images')
    p.add_argument('--target', '-t', required=True, help='Target directory to save images')
    args = p.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    target = pathlib.Path(args.target)
    target.mkdir(parents=True, exist_ok=True)

    manifest = {
        'chapter_target': str(target),
        'downloaded_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'images': []
    }

    for idx, c in enumerate(candidates, start=1):
        url = c.get('url')
        if not url:
            continue
        # pick a filename prefix and preserve extension
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
        safe_ext = ext if ext else '.jpg'
        filename = f"{idx:02d}_{os.path.basename(urllib.parse.unquote(url)).replace(' ','_')}"
        dest_path = target / filename
        print('Downloading', url, '->', dest_path)
        try:
            size = download_file(url, dest_path)
        except Exception as e:
            print('  ERROR downloading', url, e)
            continue
        sha = sha256_of_file(dest_path)
        file_meta = commons_metadata_from_url(url)

        entry = {
            'filename': str(dest_path.name),
            'source_url': url,
            'commons_page': c.get('commons_page', ''),
            'caption': c.get('caption', ''),
            'filesize': size,
            'sha256': sha,
            'license': file_meta.get('LicenseShortName', ''),
            'license_url': file_meta.get('LicenseUrl', ''),
            'artist': file_meta.get('Artist', ''),
            'credit': file_meta.get('Credit', ''),
            'image_description': file_meta.get('ImageDescription', ''),
        }
        manifest['images'].append(entry)

    manifest_path = target / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print('\nWrote manifest to', manifest_path)


if __name__ == '__main__':
    main()
