#!/usr/bin/env python3
"""Build a compact, sourced human-review shortlist from the full snapshot."""
import json, re, html
from pathlib import Path

root=Path(__file__).resolve().parent
snapshot=json.loads((root/"products.json").read_text())
assert snapshot.get("complete") is True
products=snapshot["products"]
brand_re=re.compile(r"COMME des GARCONS|CDG|YOHJI|GROUND Y|SACAI|UNDERCOVER|JUNYA WATANABE|STONE ISLAND|RICK OWENS|KOLOR|OAMC|FACETASM|BED J.W.|F/CE|ISSEY MIYAKE|Y-3|N.HOOLYWOOD|NEEDLES|POST ARCHIVE|PAF|ACRONYM|SOPHNET|WHITE MOUNTAINEERING|SOUTH2 WEST8|ENGINEERED GARMENTS|AURALEE|OUR LEGACY|DRIES VAN NOTEN|PRADA|JIL SANDER|HELMUT LANG|RAF SIMONS|CRAIG GREEN|TAKAHIROMIYASHITA|NUMBER (N)INE|CAV EMPT|C.E|KAPITAL|MAISON MARGIELA|ACW|A-COLD-WALL|TAIGA TAKAHASHI|ANREALAGE|DESCENDANT|VISVIM|WOOLRICH|MEANSWHILE|ATTACHMENT|LAD MUSICIAN",re.I)
def parse(p):
    body=html.unescape(re.sub(r"<[^>]+>"," ",p.get("body_html") or ""))
    body=re.sub(r"\s+"," ",body)
    def field(k):
        m=re.search(r"\["+re.escape(k)+r"\]\s*(.*?)(?=\s*\[|$)",body,re.I)
        return m.group(1).strip() if m else ""
    def cm(k):
        m=re.search(r"(?<![A-Za-z])"+re.escape(k)+r"\s*:\s*([0-9.]+)\s*cm",body,re.I)
        return float(m.group(1)) if m else None
    color=field("Color")
    if not re.search(r"\b(?:black|charcoal|dark gr[ae]y|gr[ae]y)\b",color,re.I):return None
    if re.search(r"khaki|olive|camouflage|camo|green|brown|beige|yellow|orange|pink|purple|red",color,re.I):return None
    variants=[v for v in p.get("variants",[]) if v.get("available") is True]
    if not variants:return None
    width,length,sleeve=cm("Width"),cm("Length"),cm("Sleeve length")
    if width is None or length is None: return None
    if length>78 or width<52 or width/length<0.81:return None
    size=field("Size")
    tags=p.get("tags") or []
    if isinstance(tags,str):tags=[tags]
    if not re.search(r"\b(?:s|m|l|small|medium|large|1|2|3|44|46|48|50)\b",size,re.I) and not any(re.fullmatch("size_[sml]",str(x),re.I) for x in tags):return None
    details=field("Other details")
    padding_match=re.search(r"\b(?:padding|filling|insulation)\s*:\s*(none|no|yes|present|absent|down|[A-Za-z ]{1,30})",details,re.I)
    padding=padding_match.group(1).strip() if padding_match else "not specified"
    if re.search(r"\b(?:yes|present|down|filled|padded)\b",padding,re.I):return None
    material=field("Material")
    season=("spring/summer" if any(str(t).lower()=="season_spring/summer" for t in tags) else "autumn/winter" if any(str(t).lower()=="season_autumn/winter" for t in tags) else "unknown")
    brand=p.get("vendor") or ""
    notable=bool(brand_re.search(brand+" "+(p.get("title") or "")))
    ratio=round(width/length,3)
    score=(25 if notable else 0)+(22 if ratio>=1 else 13 if ratio>=.93 else 5)+(15 if length<=65 else 8 if length<=70 else 0)+(10 if width>=60 else 5 if width>=56 else 0)+(8 if season=="spring/summer" else 0)+(6 if re.search(r"nylon|polyester|cotton|cupro|rayon",material,re.I) else 0)
    return {"id":str(p["id"]),"brand":brand,"title":p.get("title"),"handle":p.get("handle"),"url":"https://ragtag-global.com/products/"+str(p.get("handle")),"color":color,"size":size,"width_cm":width,"length_cm":length,"sleeve_cm":sleeve,"ratio":ratio,"material":material[:240],"other_details":details[:260],"padding":padding,"season":season,"price_raw":variants[0].get("price"),"currency":"unverified","tags":tags,"image_url":(p.get("images") or [{}])[0].get("src"),"notable":notable,"score":score}
candidates=[x for p in products if (x:=parse(p))]
candidates.sort(key=lambda x:(-x["score"],x["brand"],x["handle"]))
out=root/"catalog"
(out/"shortlist-summary.json").write_text(json.dumps({"total_scanned":len(products),"matching_filters":len(candidates),"notable_matches":sum(x["notable"] for x in candidates),"top":candidates[:40]},ensure_ascii=False,indent=2)+"\n")
(out/"shortlist-designers.json").write_text(json.dumps({"total_scanned":len(products),"matches":[x for x in candidates if x["notable"]][:180]},ensure_ascii=False,indent=2)+"\n")
(out/"shortlist-other.json").write_text(json.dumps({"matches":[x for x in candidates if not x["notable"]][:65]},ensure_ascii=False,indent=2)+"\n")
print(f"Candidate shortlist: {len(candidates)}, designers: {sum(x['notable'] for x in candidates)}")
