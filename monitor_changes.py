#!/usr/bin/env python3
"""Compare two COMPLETE Shopify snapshots and emit a compact change report."""
import json, re, html
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CURRENT=ROOT/"products.json"
PREVIOUS=Path("/tmp/ragtag-previous.json")
REPORT=ROOT/"catalog/changes.json"

def read_products(path):
    if not path.is_file(): return None
    obj=json.loads(path.read_text())
    if not isinstance(obj,dict) or not isinstance(obj.get("products"),list):
        raise ValueError(f"Invalid snapshot: {path}")
    items=obj["products"]
    ids=[str(p["id"]) for p in items]
    if len(ids)!=len(set(ids)): raise ValueError(f"Duplicate product IDs: {path}")
    return items

def details(product):
    body=html.unescape(re.sub(r"<[^>]+>", " ", product.get("body_html") or ""))
    body=re.sub(r"\s+"," ",body)
    def field(name):
        m=re.search(r"\["+re.escape(name)+r"\]\s*(.*?)(?=\s*\[|$)",body,re.I)
        return m.group(1).strip() if m else ""
    def dimension(name):
        m=re.search(r"(?<![A-Za-z])"+re.escape(name)+r"\s*:\s*([0-9.]+)\s*cm",body,re.I)
        return float(m.group(1)) if m else None
    return body, field, dimension

def eligible(p):
    if not any(v.get("available") is True for v in p.get("variants",[])): return None
    body,field,dim=details(p)
    color=field("Color").lower()
    if not re.search(r"\b(black|charcoal|gr[ae]y|dark gray|dark grey)\b",color): return None
    if re.search(r"khaki|olive|green|brown|beige|camo|zebra|leopard|orange|yellow|pink|red|purple",color): return None
    tags=p.get("tags") or []
    if isinstance(tags,str): tags=[tags]
    tags=[str(t).lower() for t in tags]
    size=field("Size")
    size_tags=" ".join(tags)
    if not re.search(r"\b(s|m|l|small|medium|large|1|2|3|44|46|48|50)\b",size.lower()) and not re.search(r"size_[sml]\b",size_tags):
        return None
    width,length=dim("Width"),dim("Length")
    if width is not None and length is not None:
        if width<53 or width/length<0.89 or length>75: return None
    padding_field=re.search(r"\b(?:padding|filling|insulation)\s*:\s*([^\[.;]{1,70})",body,re.I)
    padding=padding_field.group(1).strip() if padding_field else "Unknown"
    if re.search(r"\b(yes|present|padded|down|feather|polyester filling)\b",padding,re.I):
        return None
    season="Spring/Summer" if "season_spring/summer" in tags else ("Autumn/Winter" if "season_autumn/winter" in tags else "Unknown")
    variant=next(v for v in p["variants"] if v.get("available") is True)
    return {
        "id":str(p["id"]),"handle":p.get("handle"),"brand":p.get("vendor"),"title":p.get("title"),
        "url":"https://ragtag-global.com/products/"+str(p.get("handle","")),
        "color":field("Color"),"size":size,"width_cm":width,"length_cm":length,
        "sleeve_cm":dim("Sleeve length"),"material":field("Material")[:350],
        "padding":padding,"season":season,"price_raw":variant.get("price"),
        "currency":"unverified","image_url":(p.get("images") or [{}])[0].get("src")
    }

def main():
    current=read_products(CURRENT)
    if current is None: raise ValueError("Missing current full snapshot")
    before=read_products(PREVIOUS)
    # Existing repository already had a snapshot. On the first run of this script,
    # establish the baseline without claiming that all catalog differences are new.
    # Collection expansion changes coverage. Establish a fresh baseline rather than
    # reporting every previously unmonitored listing as a new arrival.
    prior_meta=json.loads(PREVIOUS.read_text()) if PREVIOUS.is_file() else {}
    current_meta=json.loads(CURRENT.read_text())
    same_coverage=(prior_meta.get("collections") == current_meta.get("collections"))
    initialized=(ROOT/"catalog/changes.json").exists() and before is not None and same_coverage
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"total_products":len(current),
            "complete":True,"baseline_only":not initialized,"matches":[]}
    if initialized and before is not None:
        old={str(p["id"]):p for p in before}
        for p in current:
            prior=old.get(str(p["id"]))
            available=[str(v.get("id")) for v in p.get("variants",[]) if v.get("available") is True]
            if not available: continue
            if prior is None:
                reason="new_product"
            else:
                old_available={str(v.get("id")) for v in prior.get("variants",[]) if v.get("available") is True}
                if not (set(available)-old_available): continue
                reason="newly_available_variant"
            item=eligible(p)
            if item: report["matches"].append({"reason":reason,**item})
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"Report: {len(report['matches'])} eligible changes; baseline_only={report['baseline_only']}")
if __name__=="__main__":main()
