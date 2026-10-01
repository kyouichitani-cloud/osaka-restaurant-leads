"""Osaka's 43 municipalities and conservative previous-list matching."""
import re
import unicodedata
from pathlib import Path
import json

REGIONS = {
    "north": ["豊中市", "池田市", "箕面市", "豊能町", "能勢町", "吹田市", "高槻市", "茨木市", "摂津市", "島本町"],
    "northeast": ["守口市", "枚方市", "寝屋川市", "門真市", "大東市", "四條畷市", "交野市"],
    "east": ["東大阪市", "八尾市", "柏原市"],
    "city": ["大阪市"],
    "sakai": ["堺市", "泉大津市", "高石市", "和泉市", "忠岡町", "岸和田市", "貝塚市", "泉佐野市", "泉南市", "阪南市", "熊取町", "田尻町", "岬町"],
    "south": ["松原市", "藤井寺市", "羽曳野市", "富田林市", "河内長野市", "大阪狭山市", "太子町", "河南町", "千早赤阪村"],
}
CITIES = {city: region for region, cities in REGIONS.items() for city in cities}

def norm(value):
    return unicodedata.normalize("NFKC", str(value or "")).strip()

def namekey(value):
    value = norm(value).lower().replace("ヶ", "ケ").replace("髙", "高")
    return re.sub(r"[\s・･.,。、「」()（）&＆'’‘\-]+", "", value)

def place(address, authority=""):
    address = norm(address).replace("四条畷市", "四條畷市").replace("千早赤坂村", "千早赤阪村")
    address = re.sub(r"^〒?\d{3}-?\d{4}\s*", "", address)
    address = re.sub(r"^大阪府", "", address)
    if authority in ("大阪市", "堺市") and not address.startswith(authority) and re.match(r"[^区市町村]{1,5}区", address):
        address = authority + address
    # Match only the beginning, not an owner address or a building name.
    match = re.match(r"(?:(?:豊能|三島|泉北|泉南|南河内)郡)?(" + "|".join(sorted(CITIES, key=len, reverse=True)) + r")", address)
    if not match:
        return None, None, address
    city = match.group(1)
    return CITIES[city], city, address

def addresskey(address):
    value = norm(address).lower()
    value = re.sub(r"[\s　,，、]+", "", value)
    value = re.sub(r"([0-9])(?:丁目|番地の|番地|番|号)(?=[0-9])", r"\1-", value)
    value = re.sub(r"([0-9])(?:丁目|番地の|番地|番|号)(?=[0-9])", r"\1-", value)
    value = re.sub(r"[−ー―‐－]", "-", value)
    value = re.sub(r"([0-9])(?:号|番地)$", r"\1", value)
    return value

# Wards copied in the original 100-row order; generic names are not excluded
# across the whole prefecture just because an unrelated Osaka-city shop matches.
WARDS = ("東淀川 北 旭 港 東成 福島 平野 住之江 淀川 中央 旭 旭 旭 港 港 鶴見 鶴見 生野 生野 生野 東住吉 東住吉 東住吉 平野 平野 平野 住之江 住之江 住之江 淀川 淀川 淀川 天王寺 天王寺 天王寺 阿倍野 阿倍野 阿倍野 中央 中央 中央 都島 都島 都島 都島 東淀川 東淀川 東淀川 東淀川 此花 西成 西成 住吉 西淀川 西淀川 西淀川 大正 浪速 福島 福島 東住吉 此花 此花 此花 此花 此花 西成 西成 西成 住吉 住吉 住吉 住吉 西淀川 西淀川 西淀川 西淀川 西淀川 城東 城東 城東 城東 大正 大正 浪速 浪速 浪速 東住吉 東住吉 旭 旭 港 港 港 阿倍野 阿倍野 平野 平野 福島 東成").split()
NAMES = json.loads(Path(__file__).with_name("prior-100.json").read_text())
assert len(WARDS) == len(NAMES) == 100
PRIOR = [(namekey(name), "大阪市" + ward + "区") for name, ward in zip(NAMES, WARDS)]
PREFIXES = r"^(?:大衆食堂|お食事処|お食事|食事処|レストハウス|居酒屋|居酒や|洋風居酒屋|洋食屋さん|洋食堂|洋食|グリル|キッチン)"

def prior_match(name, address):
    value = namekey(name)
    for old, ward in PRIOR:
        if not address.startswith(ward):
            continue
        if value == old:
            return True
        short = re.sub(PREFIXES, "", old)
        if len(short) >= 3 and (value == short or old in value):
            return True
    return False
