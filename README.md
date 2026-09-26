# Merak Zihin — Otomatik Instagram Paylaşım Sistemi

@merakzihin hesabı için günde 5 carousel gönderiyi otomatik üretir ve paylaşır.
Bilgisayarın açık olmasına gerek yoktur; her şey GitHub Actions üzerinde çalışır.

## Nasıl çalışır?

1. **Üretim:** Claude API konuya uygun carousel metnini yazar (`src/generate.py`).
2. **Doğrulama:** İkinci bir Claude çağrısı bilimsel doğruluk ve Türkçe yazım kontrolü yapar. Şüpheli içerik atılır, yenisi üretilir.
3. **Tekrar önleme:** `data/history.json` içindeki tüm geçmiş konularla karşılaştırılır.
4. **Görsel:** 1080×1350 JPEG slaytlar oluşturulur (`src/render.py`).
5. **Paylaşım:** Instagram API ile carousel olarak yayınlanır (`src/publish.py`).

## Paylaşım saatleri (Türkiye)

| Saat | İçerik |
|---|---|
| 08:45 | Güne başlarken psikoloji |
| 12:45 | Şaşırtıcı bilim gerçeği |
| 17:45 | İnsan davranışı |
| 20:45 | Uyku, rüyalar, duygular |
| 23:15 | Evren, zaman, tarih |

GitHub zamanlanmış işleri yoğunlukta 5–30 dakika gecikebilir.

## Gerekli gizli anahtarlar (Settings → Secrets and variables → Actions)

| Ad | Ne |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Console'dan API anahtarı |
| `IG_ACCESS_TOKEN` | Instagram uzun süreli erişim anahtarı |
| `IG_USER_ID` | Instagram hesap kimliği (sayı) |
| `GH_PAT` | Anahtar yenileme için GitHub fine-grained token (bu repo, Secrets: Read and write) |

## Elle çalıştırma

Actions → "Merak Zihin - Otomatik Paylaşım" → Run workflow.
`dry_run` işaretlenirse paylaşmaz, görselleri indirilebilir önizleme olarak bırakır.

## Durdurma

Actions → iş akışı → "..." → Disable workflow.
