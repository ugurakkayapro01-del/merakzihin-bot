"""Merak Zihin — içerik üretimi + bağımsız doğrulama.

Claude API ile bir carousel içeriği üretir, ikinci bir çağrıyla doğruluğunu
denetler ve geçmişte kullanılmış konulara benzeyenleri eler.
"""
import difflib
import json
import os
import re
import sys
import time

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")

# Gün içindeki 5 zaman dilimi ve her birinin içerik yönü (TR saati)
SLOTS = {
    "sabah": "Güne başlarken işe yarayan psikoloji bilgisi (alışkanlık, odak, motivasyonun bilimi, sabah rutini)",
    "ogle": "Şaşırtıcı bilim gerçeği (insan vücudu, beyin, doğa, hayvanlar) — 'bunu bilmiyordum' dedirten",
    "aksam": "İnsan davranışı ve sosyal psikoloji (ilişkiler, iletişim, karar verme, bilişsel yanılgılar)",
    "gece": "Uyku, rüyalar, duygular ve zihnin gece hali",
    "gece_gec": "Evren, zaman ve tarihten zihin açan bir gerçek",
}

CATEGORIES = ["beyin", "psikoloji", "uyku", "duygu", "davranis", "bilim", "uzay", "tarih", "vucut", "fikir"]

GEN_SYSTEM = """Sen "Merak Zihin" (@merakzihin) adlı Türkçe Instagram hesabının baş editörüsün.
Hesap psikoloji, bilim ve şaşırtıcı gerçekler hakkında carousel gönderiler paylaşır.
Slogan: "Merak eden zihin büyür."

MUTLAK KURALLAR:
1. Sadece bilimsel olarak iyi yerleşmiş, tekrarlanmış, kaynağı güvenilir (hakemli çalışma, üniversite, NIH, WHO, NASA vb.) bilgiler kullan. Emin değilsen o konuyu seçme.
2. Popüler mitleri ASLA gerçek gibi sunma (ör. "beynin %10'unu kullanırız", "sol beyin/sağ beyin kişiliği", "öğrenme stilleri", "Japon balığının 3 saniyelik hafızası", "21 günde alışkanlık"). İstersen bir miti "yanlış bilinen" olarak çürütebilirsin.
3. Replikasyon krizi yaşamış bulguları (ego tükenmesi, güç pozu, marshmallow testinin abartılı yorumu vb.) kesin gerçek gibi sunma.
4. Tıbbi teşhis, tedavi veya ilaç tavsiyesi verme. İntihar, kendine zarar, yeme bozukluğu konularını işleme.
5. Siyaset, din, ünlü kişiler, markalar, güncel haberler yok.
6. Sayıları kaynaktaki gibi ve yaklaşık ifade et ("yaklaşık", "ortalama"). Uydurma istatistik yok.
7. Doğal, akıcı, günlük Türkçe yaz. Çeviri kokan cümle yok. Okura "sen" diye hitap edebilirsin.
8. Türkçe yazım ve noktalamaya tam uy.

FORMAT (sadece geçerli JSON döndür, başka hiçbir şey yazma):
{
  "topic_key": "kısa-kebab-case-konu-anahtari",
  "category": "<beyin|psikoloji|uyku|duygu|davranis|bilim|uzay|tarih|vucut|fikir>",
  "headline": "Kapak başlığı, en fazla 9 kelime. Vurgulanacak 1-2 kelimeyi [[çift köşeli parantez]] içine al.",
  "subline": "Kapakta başlığın altındaki merak uyandıran kısa cümle (en fazla 9 kelime)",
  "slides": [
    {"title": "Kısa ara başlık (1-3 kelime, ör. NEDEN?, NASIL?, PEKİ YA SEN?)", "body": "En fazla 38 kelime. Vurgu için en fazla bir ifadeyi [[ ]] içine al."}
  ],
  "caption": "Instagram açıklaması: 2-4 kısa paragraf, konuyu biraz daha açan, sonunda yorum yapmaya davet eden bir soru. Emoji ölçülü (en fazla 3).",
  "hashtags": ["#psikoloji", "... toplam 8-12 Türkçe/ilgili etiket"],
  "source": "Bilginin dayandığı güvenilir kaynak türü ve kurum (ör. 'Walker, Why We Sleep; NIH uyku araştırmaları')"
}
slides dizisi 3 veya 4 eleman içersin. Son slayt okuru düşünmeye veya kendini gözlemlemeye davet etsin."""

VERIFY_SYSTEM = """Sen titiz bir bilim editörü ve Türkçe düzeltmenisin. Sana bir Instagram carousel içeriği (JSON) verilecek.
Görevin:
1. Her iddiayı bilimsel doğruluk açısından denetle. Mit, abartı, replikasyonu zayıf bulgu, uydurma/şüpheli sayı, yanlış kaynak var mı?
2. Tıbbi tavsiye, hassas konu, siyaset/din/ünlü içeriği var mı?
3. Türkçe yazım, dil bilgisi ve noktalama hatalarını düzelt; anlamı değiştirme.
Sadece JSON döndür:
{"verdict": "PASS" veya "FAIL", "problems": ["..."], "fixed": <aynı şemada düzeltilmiş içerik; FAIL ise null>}
Küçük dil hataları varsa düzelt ve PASS ver. Bilimsel olarak şüpheli tek bir iddia bile varsa FAIL ver."""


def call_claude(system, user, max_tokens=4000):
    key = os.environ["ANTHROPIC_API_KEY"]
    for attempt in range(4):
        r = requests.post(
            API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=180,
        )
        if r.status_code in (429, 500, 502, 503, 529):
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
    raise RuntimeError(f"Claude API yanıt vermedi: {r.status_code} {r.text[:300]}")


def extract_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON bulunamadı: " + text[:300])
    return json.loads(m.group(0))


def load_history():
    with open(HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def strip_marks(s):
    return re.sub(r"\[\[|\]\]", "", s or "").lower()


def too_similar(item, history):
    key = item.get("topic_key", "")
    head = strip_marks(item.get("headline", ""))
    for p in history["posts"]:
        if p.get("topic_key") == key:
            return f"aynı konu anahtarı: {key}"
        if difflib.SequenceMatcher(None, head, strip_marks(p.get("headline", ""))).ratio() > 0.72:
            return f"başlık çok benzer: {p.get('headline')}"
    return None


def validate_shape(item):
    assert item["category"] in CATEGORIES, "geçersiz kategori"
    assert 3 <= len(item["slides"]) <= 4, "slayt sayısı 3-4 olmalı"
    assert len(strip_marks(item["headline"]).split()) <= 11, "başlık çok uzun"
    for s in item["slides"]:
        assert len(strip_marks(s["body"]).split()) <= 45, "slayt metni çok uzun"
    assert item["caption"] and item["hashtags"], "açıklama/etiket eksik"


def generate(slot):
    history = load_history()
    recent = [f"{p['topic_key']} | {strip_marks(p['headline'])}" for p in history["posts"][-300:]]
    rejected = []
    for attempt in range(5):
        user = (
            f"Bugünkü zaman dilimi: {slot}. İçerik yönü: {SLOTS[slot]}.\n\n"
            "Daha önce paylaşılan konular (bunları ve benzerlerini, aynı ana fikri farklı cümleyle bile TEKRARLAMA):\n"
            + ("\n".join(recent) if recent else "(henüz yok)")
            + ("\n\nBu denemede reddedilen fikirler (bunları da kullanma):\n" + "\n".join(rejected) if rejected else "")
            + "\n\nŞimdi yeni, özgün ve güçlü bir carousel içeriği üret."
        )
        try:
            item = extract_json(call_claude(GEN_SYSTEM, user))
            validate_shape(item)
        except Exception as e:  # biçim hatası → yeniden dene
            print(f"[deneme {attempt+1}] biçim hatası: {e}", file=sys.stderr)
            continue
        sim = too_similar(item, history)
        if sim:
            print(f"[deneme {attempt+1}] tekrar reddedildi: {sim}", file=sys.stderr)
            rejected.append(item.get("topic_key", "") + " — " + strip_marks(item.get("headline", "")))
            continue
        ver = extract_json(call_claude(VERIFY_SYSTEM, json.dumps(item, ensure_ascii=False)))
        if ver.get("verdict") != "PASS" or not ver.get("fixed"):
            print(f"[deneme {attempt+1}] doğrulamadan geçemedi: {ver.get('problems')}", file=sys.stderr)
            rejected.append(item.get("topic_key", "") + " — doğrulama: " + "; ".join(ver.get("problems") or []))
            continue
        fixed = ver["fixed"]
        try:
            validate_shape(fixed)
        except Exception as e:
            print(f"[deneme {attempt+1}] düzeltilmiş içerik biçim hatası: {e}", file=sys.stderr)
            continue
        fixed["slot"] = slot
        fixed["verify_notes"] = ver.get("problems") or []
        return fixed
    raise RuntimeError("5 denemede geçerli içerik üretilemedi; bu slot atlanıyor.")


if __name__ == "__main__":
    slot = sys.argv[1]
    out = sys.argv[2]
    item = generate(slot)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)
    print("Üretildi:", item["topic_key"])
