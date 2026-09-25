#!/usr/bin/env python3
"""Fetch NAF's images, per its own README: a plain HTTPS download, no account, no browser.

Usage: fetch.py --naf-dir NAF_DIR [--tarball PATH] [--extract-dir PATH]

NAF_DIR is a clone of https://github.com/herobd/NAF_dataset (its JSON annotations are committed
to that repo; its images are gitignored and shipped separately as a GitHub release asset, per the
repo's own README "Setup" section). This script:

1. Downloads `labeled_images.tar.gz` from
   https://github.com/herobd/NAF_dataset/releases/download/v1.0/labeled_images.tar.gz
   (skipped if already present at --tarball, so a rerun does not re-download 790 MB).
2. Extracts it to --extract-dir (a flat directory of <image_id>.jpg files).
3. Moves each image into NAF_DIR/groups/<group>/<image_id>.jpg, matched by basename against the
   JSON annotation already sitting in that group directory (NAF_DIR/groups/<group>/<image_id>.json):
   this reproduces move_images.sh's own effect without depending on its hardcoded /tmp path or
   its literal (and easy to go stale) list of `mv` lines.

Idempotent: an image already in place is left alone. Prints how many of the 865 expected images
were placed, and every JSON annotation with no matching image (a fetch gap, reported, not hidden).
"""
import argparse
import os
import shutil
import sys
import tarfile
import urllib.request

from .annotations import is_annotation_file

RELEASE_URL = "https://github.com/herobd/NAF_dataset/releases/download/v1.0/labeled_images.tar.gz"


def download(url, dest):
    if os.path.exists(dest):
        print("tarball already present at %s, skipping download" % dest)
        return
    tmp = dest + ".part"
    print("downloading %s" % url)
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    os.rename(tmp, dest)
    print("downloaded %s (%d bytes)" % (dest, os.path.getsize(dest)))


def extract(tarball, extract_dir):
    marker = os.path.join(extract_dir, "labeled_images")
    if os.path.isdir(marker) and os.listdir(marker):
        print("already extracted at %s, skipping" % marker)
        return marker
    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as tf:
        tf.extractall(extract_dir)  # noqa: S202, a same-origin release asset, not untrusted input
    return marker


def place_images(naf_dir, flat_dir):
    groups_dir = os.path.join(naf_dir, "groups")
    placed = 0
    already = 0
    missing = []
    for group in sorted(os.listdir(groups_dir)):
        group_path = os.path.join(groups_dir, group)
        if not os.path.isdir(group_path):
            continue
        for name in sorted(os.listdir(group_path)):
            if not is_annotation_file(name):
                continue
            image_id = name[: -len(".json")]
            dest = os.path.join(group_path, image_id + ".jpg")
            if os.path.exists(dest):
                already += 1
                continue
            src = os.path.join(flat_dir, image_id + ".jpg")
            if not os.path.exists(src):
                missing.append(image_id)
                continue
            shutil.copy2(src, dest)
            placed += 1
    return placed, already, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--naf-dir", required=True)
    parser.add_argument("--tarball", default=None,
                         help="where to keep the downloaded tarball (default: NAF_DIR/labeled_images.tar.gz)")
    parser.add_argument("--extract-dir", default=None,
                         help="scratch directory to extract into (default: NAF_DIR/.extract)")
    args = parser.parse_args()

    tarball = args.tarball or os.path.join(args.naf_dir, "labeled_images.tar.gz")
    extract_dir = args.extract_dir or os.path.join(args.naf_dir, ".extract")

    download(RELEASE_URL, tarball)
    flat_dir = extract(tarball, extract_dir)
    placed, already, missing = place_images(args.naf_dir, flat_dir)

    print("placed %d new images, %d already present, %d missing" % (placed, already, len(missing)))
    if missing:
        print("missing image ids: %s" % ", ".join(missing[:20]))
        if len(missing) > 20:
            print("... and %d more" % (len(missing) - 20))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
