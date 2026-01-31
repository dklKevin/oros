#!/usr/bin/env python3
"""
Script to download biomedical engineering research papers from PubMed Central Open Access.
Uses NCBI E-utilities API via curl to handle SSL certificates properly.
"""

import os
import json
import time
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
import urllib.parse

# Configuration
OUTPUT_DIR = "/Users/kevinlee/Desktop/code-stuff/oros/test-data"
BASE_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Search terms for biomedical engineering topics
SEARCH_TERMS = [
    "CRISPR gene editing",
    "gene therapy clinical trial",
    "medical device implant",
    "tissue engineering scaffold",
    "biosensor diagnostic",
    "biomedical engineering neural"
]

def curl_get(url, timeout=30):
    """Use curl to make HTTP requests (handles SSL better)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout), url],
            capture_output=True,
            text=True,
            timeout=timeout + 10
        )
        return result.stdout
    except Exception as e:
        print(f"Curl error: {e}")
        return None

def curl_get_binary(url, timeout=60):
    """Use curl to get binary content."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout), url],
            capture_output=True,
            timeout=timeout + 10
        )
        return result.stdout
    except Exception as e:
        print(f"Curl error: {e}")
        return None

def search_pmc(query, retmax=10):
    """Search PubMed Central for open access articles."""
    params = {
        "db": "pmc",
        "term": f"{query} AND open access[filter]",
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance"
    }
    url = f"{BASE_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    response = curl_get(url)
    if response:
        try:
            data = json.loads(response)
            return data.get("esearchresult", {}).get("idlist", [])
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    return []

def fetch_article_metadata(pmcid):
    """Fetch article metadata from PubMed Central."""
    params = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml"
    }
    url = f"{BASE_FETCH_URL}?{urllib.parse.urlencode(params)}"
    return curl_get(url, timeout=30)

def parse_article_metadata(xml_content):
    """Parse article metadata from XML."""
    try:
        root = ET.fromstring(xml_content)
        article = root.find(".//article")
        if article is None:
            return None

        metadata = {
            "pmcid": "",
            "title": "",
            "authors": [],
            "doi": "",
            "journal": "",
            "pub_date": "",
            "abstract": ""
        }

        # Get PMCID
        for article_id in root.findall(".//article-id"):
            if article_id.get("pub-id-type") == "pmc":
                metadata["pmcid"] = f"PMC{article_id.text}"
            elif article_id.get("pub-id-type") == "doi":
                metadata["doi"] = article_id.text

        # Get title
        title_elem = root.find(".//article-title")
        if title_elem is not None:
            metadata["title"] = "".join(title_elem.itertext()).strip()

        # Get authors
        for contrib in root.findall(".//contrib[@contrib-type='author']"):
            surname = contrib.find(".//surname")
            given_names = contrib.find(".//given-names")
            if surname is not None:
                name = surname.text or ""
                if given_names is not None and given_names.text:
                    name = f"{given_names.text} {name}"
                metadata["authors"].append(name)

        # Get journal
        journal_elem = root.find(".//journal-title")
        if journal_elem is not None:
            metadata["journal"] = journal_elem.text or ""

        # Get publication date
        pub_date = root.find(".//pub-date[@pub-type='epub']") or root.find(".//pub-date")
        if pub_date is not None:
            year = pub_date.find("year")
            month = pub_date.find("month")
            day = pub_date.find("day")
            date_parts = []
            if year is not None and year.text:
                date_parts.append(year.text)
            if month is not None and month.text:
                date_parts.append(month.text.zfill(2))
            if day is not None and day.text:
                date_parts.append(day.text.zfill(2))
            metadata["pub_date"] = "-".join(date_parts)

        # Get abstract
        abstract_elem = root.find(".//abstract")
        if abstract_elem is not None:
            metadata["abstract"] = " ".join("".join(p.itertext()).strip() for p in abstract_elem.findall(".//p"))

        return metadata
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return None

def download_full_text_xml(pmcid, output_dir):
    """Download the full text XML from PMC."""
    params = {
        "db": "pmc",
        "id": pmcid.replace("PMC", ""),
        "retmode": "xml"
    }
    url = f"{BASE_FETCH_URL}?{urllib.parse.urlencode(params)}"

    content = curl_get_binary(url, timeout=60)
    if content:
        filename = f"{pmcid}.xml"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        return filename
    return None

def main():
    print("=" * 60)
    print("PubMed Central Open Access Paper Downloader")
    print("=" * 60)

    papers_dir = os.path.join(OUTPUT_DIR, "papers")
    os.makedirs(papers_dir, exist_ok=True)

    all_pmcids = set()
    manifest = {
        "download_date": datetime.now().isoformat(),
        "source": "PubMed Central Open Access",
        "papers": []
    }

    # Search for papers on different topics
    papers_per_topic = 7  # ~30-35 papers total across 6 topics

    for search_term in SEARCH_TERMS:
        print(f"\nSearching for: {search_term}")
        pmcids = search_pmc(search_term, retmax=papers_per_topic)
        print(f"  Found {len(pmcids)} papers")

        for pmcid in pmcids:
            if pmcid not in all_pmcids:
                all_pmcids.add(pmcid)

        time.sleep(0.4)  # Be nice to the API

    print(f"\nTotal unique papers found: {len(all_pmcids)}")
    print("\n" + "=" * 60)
    print("Downloading papers...")
    print("=" * 60)

    downloaded_count = 0
    target_count = 30

    for pmcid in list(all_pmcids)[:target_count + 10]:  # Get a few extra in case of failures
        if downloaded_count >= target_count:
            break

        print(f"\nProcessing PMC{pmcid}...")

        # Fetch metadata
        xml_content = fetch_article_metadata(pmcid)
        if not xml_content:
            print(f"  Skipping - could not fetch metadata")
            continue

        metadata = parse_article_metadata(xml_content)
        if not metadata or not metadata.get("title"):
            print(f"  Skipping - could not parse metadata")
            continue

        # Download full text XML
        filename = download_full_text_xml(f"PMC{pmcid}", papers_dir)
        if not filename:
            print(f"  Skipping - could not download full text")
            continue

        # Add to manifest
        paper_entry = {
            "filename": filename,
            "pmcid": metadata["pmcid"] or f"PMC{pmcid}",
            "title": metadata["title"],
            "authors": metadata["authors"],
            "doi": metadata["doi"],
            "journal": metadata["journal"],
            "pub_date": metadata["pub_date"],
            "abstract": metadata["abstract"][:500] + "..." if len(metadata.get("abstract", "")) > 500 else metadata.get("abstract", "")
        }
        manifest["papers"].append(paper_entry)

        downloaded_count += 1
        title_display = metadata['title'][:55] if len(metadata['title']) <= 55 else metadata['title'][:55] + "..."
        print(f"  [{downloaded_count}/{target_count}] Downloaded: {title_display}")

        time.sleep(0.35)  # Rate limiting

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"Total papers downloaded: {len(manifest['papers'])}")
    print(f"Papers directory: {papers_dir}")
    print(f"Manifest file: {manifest_path}")

    # Print summary by topic
    print("\n" + "=" * 60)
    print("PAPERS SUMMARY")
    print("=" * 60)
    for i, paper in enumerate(manifest["papers"], 1):
        title_truncated = paper['title'][:70] + ('...' if len(paper['title']) > 70 else '')
        print(f"\n{i}. {title_truncated}")
        print(f"   PMCID: {paper['pmcid']}")
        if paper['doi']:
            print(f"   DOI: {paper['doi']}")
        if paper['authors']:
            authors_str = ", ".join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors_str += f" et al. ({len(paper['authors'])} authors)"
            print(f"   Authors: {authors_str}")
        if paper['journal']:
            print(f"   Journal: {paper['journal']}")

if __name__ == "__main__":
    main()
